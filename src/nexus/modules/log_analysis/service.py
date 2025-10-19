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

def ingest(cfg, path: Path) -> dict:
    rows = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                obj = {"raw_line": line}
            rows.append(obj)
    if not rows:
        return {}

    df = pd.DataFrame(rows)
    dsid = _dataset_id(path)
    pq_dir = cfg.data_dir / "parquet" / dsid
    pq_dir.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df)
    pq.write_to_dataset(table, root_path=str(pq_dir))

    con = duck_connect(cfg.data_dir / "duckdb")
    tbl = cfg.default_table
    con.execute(f"CREATE OR REPLACE VIEW {tbl} AS SELECT * FROM parquet_scan(?)", [str(pq_dir)])

    return {"dataset_id": dsid, "table": tbl, "rows": len(rows)}

def run_canned(cfg, name: str, params: dict) -> dict:
    con = duck_connect(cfg.data_dir / "duckdb")
    tbl = cfg.default_table
    if name == "total_requests":
        sql = f"SELECT COUNT(*) AS total FROM {tbl};"
        res = con.execute(sql).fetchdf()
        try:
            sample = con.execute(f"SELECT * FROM {tbl} LIMIT 5;").fetchdf()
            evidence = sample.to_dict(orient="records")
        except Exception:
            evidence = []
        confidence = "high" if res.loc[0, "total"] > 0 else "low"
        return {
            "table": tbl,
            "sql": sql,
            "result": res.to_dict(orient="records"),
            "evidence": evidence,
            "confidence": confidence,
        }
    return {"error": f"unknown canned query: {name}"}