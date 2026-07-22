from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from typing import Callable
import duckdb

VALID_BUCKETS = {"second", "minute", "hour", "day", "week", "month", "year"}
MAX_LIMIT = 1000
DEFAULT_LIMIT = 20


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _json_safe(value):
    # DuckDB infers native temporal/decimal types (e.g. via read_json_auto's
    # type detection), which the stdlib json module can't serialize directly.
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _fetch_rows(con: duckdb.DuckDBPyConnection, sql: str) -> list[dict]:
    """Execute a query and return rows as plain dicts via the DB-API cursor
    (fetchall + description), never .fetchdf(). The pandas/pyarrow conversion
    path has been observed to crash the process on a second call when run
    from inside a long-lived server (e.g. the web UI); fetchall() does not."""
    cur = con.execute(sql)
    columns = [d[0] for d in cur.description]
    return [{col: _json_safe(v) for col, v in zip(columns, row)} for row in cur.fetchall()]


def _table_columns(con: duckdb.DuckDBPyConnection, tbl_ident: str) -> list[str]:
    rows = con.execute(f"DESCRIBE {tbl_ident};").fetchall()
    return [r[0] for r in rows]


def _validate_field(con: duckdb.DuckDBPyConnection, tbl_ident: str, field_name: str) -> str:
    """Validate a user-supplied field name against real columns before it is
    interpolated into SQL as an identifier. Raises ValueError on mismatch."""
    columns = _table_columns(con, tbl_ident)
    if field_name not in columns:
        raise ValueError(f"unknown field {field_name!r}; available: {', '.join(columns)}")
    return _quote_ident(field_name)


def _clamp_limit(limit) -> int:
    try:
        n = int(limit)
    except (TypeError, ValueError):
        n = DEFAULT_LIMIT
    return max(1, min(n, MAX_LIMIT))


@dataclass
class CannedQuery:
    name: str
    description: str
    params_schema: dict = field(default_factory=dict)
    handler: Callable[[duckdb.DuckDBPyConnection, str, dict], dict] = None


REGISTRY: dict[str, CannedQuery] = {}


def _register(name: str, description: str, params_schema: dict):
    def deco(fn):
        REGISTRY[name] = CannedQuery(name=name, description=description,
                                      params_schema=params_schema, handler=fn)
        return fn
    return deco


def list_canned_queries() -> list[dict]:
    return [
        {"name": q.name, "description": q.description, "params": q.params_schema}
        for q in REGISTRY.values()
    ]


@_register("total_requests", "Total row count in the table, with a sample of rows as evidence.", {})
def _total_requests(con, tbl_ident, params):
    sql = f"SELECT COUNT(*) AS total FROM {tbl_ident};"
    total = _fetch_rows(con, sql)[0]["total"]
    sample = _fetch_rows(con, f"SELECT * FROM {tbl_ident} LIMIT 5;")
    return {
        "sql": sql,
        "result": [{"total": int(total)}],
        "evidence": sample,
        "confidence": "high" if total > 0 else "low",
    }


@_register("columns", "List the columns available in the ingested table.", {})
def _columns(con, tbl_ident, params):
    sql = f"DESCRIBE {tbl_ident};"
    result = _fetch_rows(con, sql)
    return {
        "sql": sql,
        "result": result,
        "evidence": result[:5],
        "confidence": "high",
    }


@_register(
    "count_by_field",
    "Group rows by a field and count occurrences, most common first.",
    {"field": "string (required)", "limit": f"int, default {DEFAULT_LIMIT}, max {MAX_LIMIT}"},
)
def _count_by_field(con, tbl_ident, params):
    field_name = params.get("field")
    if not field_name:
        raise ValueError("param 'field' is required")
    field_ident = _validate_field(con, tbl_ident, field_name)
    limit = _clamp_limit(params.get("limit", DEFAULT_LIMIT))

    sql = (f"SELECT {field_ident} AS value, COUNT(*) AS count FROM {tbl_ident} "
           f"GROUP BY {field_ident} ORDER BY count DESC LIMIT {limit};")
    result = _fetch_rows(con, sql)
    return {
        "sql": sql,
        "result": result,
        "evidence": result[:5],
        "confidence": "high" if result else "low",
    }


@_register(
    "time_bucketed_counts",
    "Bucket rows by a timestamp field and count per bucket.",
    {
        "time_field": "string (required)",
        "bucket": f"one of {sorted(VALID_BUCKETS)}, default 'day'",
        "limit": f"int, default {DEFAULT_LIMIT}, max {MAX_LIMIT}",
    },
)
def _time_bucketed_counts(con, tbl_ident, params):
    field_name = params.get("time_field")
    if not field_name:
        raise ValueError("param 'time_field' is required")
    field_ident = _validate_field(con, tbl_ident, field_name)

    bucket = params.get("bucket", "day")
    if bucket not in VALID_BUCKETS:
        raise ValueError(f"invalid bucket {bucket!r}; must be one of {sorted(VALID_BUCKETS)}")

    limit = _clamp_limit(params.get("limit", DEFAULT_LIMIT))

    sql = (f"SELECT CAST(date_trunc('{bucket}', TRY_CAST({field_ident} AS TIMESTAMP)) AS VARCHAR) AS bucket, "
           f"COUNT(*) AS count FROM {tbl_ident} "
           f"WHERE TRY_CAST({field_ident} AS TIMESTAMP) IS NOT NULL "
           f"GROUP BY bucket ORDER BY bucket LIMIT {limit};")
    result = _fetch_rows(con, sql)
    return {
        "sql": sql,
        "result": result,
        "evidence": result[:5],
        "confidence": "high" if result else "low",
    }


@_register(
    "distinct_values",
    "List distinct values seen for a field, for exploratory sniffing.",
    {"field": "string (required)", "limit": f"int, default {DEFAULT_LIMIT}, max {MAX_LIMIT}"},
)
def _distinct_values(con, tbl_ident, params):
    field_name = params.get("field")
    if not field_name:
        raise ValueError("param 'field' is required")
    field_ident = _validate_field(con, tbl_ident, field_name)
    limit = _clamp_limit(params.get("limit", DEFAULT_LIMIT))

    sql = f"SELECT DISTINCT {field_ident} AS value FROM {tbl_ident} LIMIT {limit};"
    result = _fetch_rows(con, sql)
    return {
        "sql": sql,
        "result": result,
        "evidence": result[:5],
        "confidence": "high" if result else "low",
    }
