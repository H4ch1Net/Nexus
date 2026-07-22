from __future__ import annotations
from pathlib import Path
import atexit
import duckdb

# Cache one connection per database directory for the life of the process.
# Repeatedly opening/closing a DuckDB connection to the same file works fine
# for a one-shot CLI invocation, but a long-lived process (the web UI) that
# opens a fresh connection per request has been observed to crash the native
# extension. Reusing a single connection avoids that and is the normal
# pattern for an embedded database in a persistent process anyway.
_connections: dict[str, duckdb.DuckDBPyConnection] = {}


def duck_connect(db_dir: Path) -> duckdb.DuckDBPyConnection:
    db_dir.mkdir(parents=True, exist_ok=True)
    key = str(db_dir.resolve())
    con = _connections.get(key)
    if con is None:
        con = duckdb.connect(str(db_dir / "nexus.duckdb"))
        con.execute("PRAGMA threads=1")
        _connections[key] = con
    return con


@atexit.register
def _close_all_connections() -> None:
    for con in _connections.values():
        try:
            con.close()
        except Exception:
            pass
    _connections.clear()
