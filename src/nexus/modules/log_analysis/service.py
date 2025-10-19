from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from nexus.core.storage import duck_connect


def _dataset_id(path: Path) -> str:
    stem = path.stem
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{stem}-{ts}"


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


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

    df = pd.DataFrame(rows)
    dsid = _dataset_id(path)
    pq_dir = cfg.data_dir / "parquet" / dsid
    pq_dir.mkdir(parents=True, exist_ok=True)

    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_to_dataset(table, root_path=str(pq_dir), basename_template="part-{i}.parquet")

    con = duck_connect(cfg.data_dir / "duckdb")
    tbl = _quote_ident(cfg.default_table)
    pattern = str(pq_dir / "*.parquet")
    con.execute(f"CREATE OR REPLACE VIEW {tbl} AS SELECT * FROM read_parquet(?)", [pattern])

    return {"dataset_id": dsid, "table": cfg.default_table, "rows": int(len(rows))}


def run_canned(cfg, name: str, params: dict) -> dict:
    con = duck_connect(cfg.data_dir / "duckdb")
    tbl_ident = _quote_ident(cfg.default_table)

    if name == "total_requests":
        try:
            sql = f"SELECT COUNT(*) AS total FROM {tbl_ident};"
            res = con.execute(sql, []).fetchdf()
        except Exception as e:
            return {"error": f"query failed: {e}"}

        try:
            sample = con.execute(f"SELECT * FROM {tbl_ident} LIMIT 5;", []).fetchdf()
            evidence = sample.to_dict(orient="records")
        except Exception:
            evidence = []

        total = int(res.loc[0, "total"]) if not res.empty else 0
        confidence = "high" if total > 0 else "low"
        return {
            "table": cfg.default_table,
            "sql": sql,
            "result": [{"total": total}],
            "evidence": evidence,
            "confidence": confidence,
        }

    return {"error": f"unknown canned query: {name}"}