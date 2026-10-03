from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json
import re
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from nexus.core.storage import duck_connect


def _dataset_id(path: Path) -> str:
    stem = path.stem
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stem}-{ts}"


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _normalize_obj(obj):
    # Ensure parquet-friendly scalars. JSON-stringify nested types.
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                out[k] = json.dumps(v, ensure_ascii=False)
            else:
                out[k] = v
        return out
    # valid JSON but not an object (e.g., string/number/array)
    return {"value": obj}


def ingest(cfg, path: Path) -> dict:
    rows = []
    bad = 0
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                obj = {"raw_line": s}
                bad += 1
            rows.append(_normalize_obj(obj))

    if not rows:
        return {}

    df = pd.DataFrame(rows)
    dsid = _dataset_id(path)
    pq_dir = cfg.data_dir / "parquet" / dsid
    pq_dir.mkdir(parents=True, exist_ok=True)

    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_to_dataset(table, root_path=str(pq_dir), basename_template="part-{i}.parquet")

    con = duck_connect(cfg.data_dir / "duckdb")
    tbl = _quote_ident(cfg.default_table)
    pattern = str(pq_dir / "*.parquet")
    # DuckDB does not allow bind parameters inside CREATE VIEW, so the path
    # (which the tool controls, under the configured data dir) is inlined as a
    # safely-escaped string literal.
    con.execute(
        f"CREATE OR REPLACE VIEW {tbl} AS SELECT * FROM read_parquet({_quote_literal(pattern)})"
    )
    con.close()

    return {
        "dataset_id": dsid,
        "table": cfg.default_table,
        "rows": int(len(rows)),
        "columns": list(df.columns),
        "malformed_lines": bad,
    }


def _columns(con, tbl_ident: str) -> list[str]:
    try:
        return [d[0] for d in con.execute(f"SELECT * FROM {tbl_ident} LIMIT 0").description]
    except Exception:
        return []


# Canned queries: name -> (description, builder(tbl_ident, params) -> sql | None)
CANNED = {
    "total_requests": "Total row count in the current table.",
    "schema": "Column names and inferred types.",
    "top_values": "Most frequent values of a column (--params '{\"field\": \"col\", \"limit\": 10}').",
    "distinct": "Distinct value count for a column (--params '{\"field\": \"col\"}').",
    "status_codes": "Distribution of HTTP-style status codes (auto-detects the column).",
    "errors": "Rows whose level/status looks like an error (sampled).",
    "time_histogram": "Row counts bucketed by day from a timestamp column.",
}


def list_canned() -> dict:
    return CANNED


def run_canned(cfg, name: str, params: dict) -> dict:
    con = duck_connect(cfg.data_dir / "duckdb")
    tbl = _quote_ident(cfg.default_table)
    cols = _columns(con, tbl)

    def _result(sql, rows, **extra):
        return {"table": cfg.default_table, "sql": sql, "result": rows, **extra}

    try:
        if name == "total_requests":
            sql = f"SELECT COUNT(*) AS total FROM {tbl};"
            total = int(con.execute(sql).fetchone()[0])
            sample = con.execute(f"SELECT * FROM {tbl} LIMIT 5;").fetchdf().to_dict("records")
            return _result(sql, [{"total": total}], evidence=sample,
                           confidence="high" if total else "low")

        if name == "schema":
            desc = con.execute(f"DESCRIBE {tbl};").fetchdf().to_dict("records")
            return _result(f"DESCRIBE {tbl};", desc)

        if name == "top_values":
            field = params.get("field")
            limit = int(params.get("limit", 10))
            if not field or field not in cols:
                return {"error": f"field required; available columns: {cols}"}
            fi = _quote_ident(field)
            sql = (f"SELECT {fi} AS value, COUNT(*) AS count FROM {tbl} "
                   f"GROUP BY {fi} ORDER BY count DESC LIMIT {limit};")
            return _result(sql, con.execute(sql).fetchdf().to_dict("records"))

        if name == "distinct":
            field = params.get("field")
            if not field or field not in cols:
                return {"error": f"field required; available columns: {cols}"}
            fi = _quote_ident(field)
            sql = f"SELECT COUNT(DISTINCT {fi}) AS distinct_count FROM {tbl};"
            return _result(sql, con.execute(sql).fetchdf().to_dict("records"))

        if name == "status_codes":
            col = next((c for c in cols if c.lower() in ("status", "status_code", "code", "response")), None)
            if not col:
                return {"error": f"no status-like column found; columns: {cols}"}
            ci = _quote_ident(col)
            sql = (f"SELECT {ci} AS status, COUNT(*) AS count FROM {tbl} "
                   f"GROUP BY {ci} ORDER BY count DESC;")
            return _result(sql, con.execute(sql).fetchdf().to_dict("records"), column=col)

        if name == "errors":
            lvl = next((c for c in cols if c.lower() in ("level", "severity", "status", "status_code")), None)
            if not lvl:
                return {"error": f"no level/status column found; columns: {cols}"}
            li = _quote_ident(lvl)
            sql = (f"SELECT * FROM {tbl} WHERE lower(CAST({li} AS VARCHAR)) "
                   f"IN ('error','err','critical','fatal') "
                   f"OR CAST({li} AS VARCHAR) LIKE '5%' LIMIT 50;")
            rows = con.execute(sql).fetchdf().to_dict("records")
            return _result(sql, rows, matched=len(rows))

        if name == "time_histogram":
            col = params.get("field") or next(
                (c for c in cols if c.lower() in ("timestamp", "time", "ts", "date", "datetime", "@timestamp")), None)
            if not col or col not in cols:
                return {"error": f"timestamp column required; columns: {cols}"}
            ci = _quote_ident(col)
            sql = (f"SELECT CAST(TRY_CAST({ci} AS TIMESTAMP) AS DATE) AS day, COUNT(*) AS count "
                   f"FROM {tbl} WHERE TRY_CAST({ci} AS TIMESTAMP) IS NOT NULL "
                   f"GROUP BY day ORDER BY day;")
            return _result(sql, con.execute(sql).fetchdf().to_dict("records"), column=col)

        return {"error": f"unknown canned query: {name}", "available": list(CANNED)}
    except Exception as e:
        return {"error": f"query failed: {e}"}
    finally:
        con.close()


_WRITE_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|create|alter|attach|detach|copy|install|"
    r"load|export|import|pragma|call|set|begin|commit|vacuum|truncate)\b", re.I)


def run_query(cfg, sql: str, limit: int = 200) -> dict:
    """Run a single read-only SELECT/WITH statement against the ingested table."""
    stmt = sql.strip().rstrip(";").strip()
    if not stmt:
        return {"error": "empty query"}
    if ";" in stmt:
        return {"error": "only a single statement is allowed"}
    first = stmt.split(None, 1)[0].lower()
    if first not in ("select", "with", "describe", "summarize", "table"):
        return {"error": "only read-only SELECT/WITH/DESCRIBE/SUMMARIZE queries are allowed"}
    if _WRITE_KEYWORDS.search(stmt):
        return {"error": "query contains a disallowed (write) keyword"}

    con = duck_connect(cfg.data_dir / "duckdb")
    try:
        df = con.execute(stmt).fetchdf()
    except Exception as e:
        return {"error": f"query failed: {e}"}
    finally:
        con.close()

    truncated = len(df) > limit
    rows = df.head(limit).to_dict("records")
    return {
        "sql": stmt,
        "columns": list(df.columns),
        "row_count": int(len(df)),
        "result": rows,
        "truncated": truncated,
    }


def dataset_info(cfg) -> dict:
    """List ingested datasets and describe the active table."""
    pq_root = cfg.data_dir / "parquet"
    datasets = []
    if pq_root.exists():
        for d in sorted(pq_root.iterdir()):
            if d.is_dir():
                parts = list(d.glob("*.parquet"))
                size = sum(p.stat().st_size for p in parts)
                datasets.append({"dataset_id": d.name, "files": len(parts), "size_bytes": size})

    active = {}
    con = duck_connect(cfg.data_dir / "duckdb")
    tbl = _quote_ident(cfg.default_table)
    try:
        cols = con.execute(f"DESCRIBE {tbl};").fetchdf().to_dict("records")
        count = int(con.execute(f"SELECT COUNT(*) FROM {tbl};").fetchone()[0])
        active = {"table": cfg.default_table, "row_count": count, "columns": cols}
    except Exception:
        active = {"table": cfg.default_table, "row_count": None, "columns": []}
    finally:
        con.close()

    return {"data_dir": str(cfg.data_dir), "datasets": datasets, "active_table": active}
