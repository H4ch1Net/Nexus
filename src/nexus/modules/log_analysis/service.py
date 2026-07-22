from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json
import tempfile
from nexus.core.storage import duck_connect
from nexus.modules.log_analysis.canned_queries import REGISTRY


def _dataset_id(path: Path) -> str:
    stem = path.stem
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{stem}-{ts}"


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _sql_literal(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


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
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                obj = {"raw_line": s}
            rows.append(_normalize_obj(obj))

    if not rows:
        return {}

    dsid = _dataset_id(path)
    pq_dir = cfg.data_dir / "parquet" / dsid
    pq_dir.mkdir(parents=True, exist_ok=True)

    con = duck_connect(cfg.data_dir / "duckdb")

    # Write the normalized rows to a temp NDJSON file and let DuckDB itself
    # read JSON -> write Parquet, rather than building the table via pyarrow.
    # DuckDB and pyarrow each bundle their own copy of the Arrow C++ library;
    # handing a pyarrow-built Table to DuckDB inside a long-lived process
    # (the web UI) has been observed to crash the native extension on a
    # second call. Staying inside DuckDB alone for the whole write path
    # avoids that cross-library handoff entirely.
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as tmp:
        for row in rows:
            tmp.write(json.dumps(row, ensure_ascii=False) + "\n")
        tmp_ndjson = Path(tmp.name)

    try:
        out_file = pq_dir / "part-0.parquet"
        con.execute(
            f"COPY (SELECT * FROM read_json_auto({_sql_literal(str(tmp_ndjson))})) "
            f"TO {_sql_literal(str(out_file))} (FORMAT PARQUET)"
        )
    finally:
        tmp_ndjson.unlink(missing_ok=True)

    tbl = _quote_ident(cfg.default_table)
    pattern = str(pq_dir / "*.parquet")
    con.execute(f"CREATE OR REPLACE VIEW {tbl} AS SELECT * FROM read_parquet({_sql_literal(pattern)})")

    return {"dataset_id": dsid, "table": cfg.default_table, "rows": int(len(rows))}


def run_canned(cfg, name: str, params: dict) -> dict:
    query = REGISTRY.get(name)
    if not query:
        return {"error": f"unknown canned query: {name}"}

    con = duck_connect(cfg.data_dir / "duckdb")
    tbl_ident = _quote_ident(cfg.default_table)

    try:
        out = query.handler(con, tbl_ident, params or {})
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"query failed: {e}"}

    out["table"] = cfg.default_table
    return out
