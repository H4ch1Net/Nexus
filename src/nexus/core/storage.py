from __future__ import annotations
from pathlib import Path
import duckdb

def duck_connect(db_dir: Path) -> duckdb.DuckDBPyConnection:
    db_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_dir / "nexus.duckdb"))
    return con
