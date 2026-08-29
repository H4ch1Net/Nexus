from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
import tomllib

DEFAULT_TOML = {
    "data": {
        "data_dir": str(Path.home()/".nexus"),
        "log_dir": str(Path.home()/".nexus"),
        "audit_log": str(Path.home()/".nexus"/"audit.log"),
    },
    "log": {
        "default_table_name": "events",
    },
}

@dataclass
class Config:
    raw: dict
    data_dir: Path
    log_dir: Path
    audit_log: Path
    default_table: str

def _expand(p: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(p)))

def load_config(path: str) -> Config:
    cfg_path = _expand(path)
    if cfg_path.exists():
        with open(cfg_path, "rb") as f:
            user = tomllib.load(f)
    else:
        user = {}
    merged = DEFAULT_TOML | user

    data = merged.get("data", {})
    data_dir = _expand(data.get("data_dir", DEFAULT_TOML["data"]["data_dir"]))
    log_dir = _expand(data.get("log_dir", DEFAULT_TOML["data"]["log_dir"]))
    audit_log = _expand(data.get("audit_log", DEFAULT_TOML["data"]["audit_log"]))

    for p in [data_dir, log_dir, audit_log.parent]:
        p.mkdir(parents=True, exist_ok=True)

    return Config(
        raw=merged,
        data_dir=data_dir,
        log_dir=log_dir,
        audit_log=audit_log,
        default_table=merged.get("log", {}).get("default_table_name", "events"),
    )
