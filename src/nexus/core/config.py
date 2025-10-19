from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
import tomllib

DEFAULT_TOML = {
    "data": {
        "data_dir": str(Path.home()/".nexus"),
        "plugins_dir": str(Path.home()/".nexus"/"plugins"),
        "log_dir": str(Path.home()/".nexus"),
        "audit_log": str(Path.home()/".nexus"/"audit.log"),
    },
    "crypto": {
        "cyberchef_bind": "127.0.0.1",
        "cyberchef_port": 8777,
        "auto_decode_top": 3,
        "max_auto_decode_input_bytes": 32768,
    },
    "log": {
        "default_table_name": "events",
        "geoip_db_path": "",
        "ingest_chunk_size_rows": 200000,
    },
    "security": {
        "plugin_whitelist_paths": [str(Path.home()/".nexus"/"plugins")],
        "require_plugin_signature": True,
        "fips_mode": False,
    },
}

@dataclass
class Config:
    raw: dict
    data_dir: Path
    plugins_dir: Path
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
    plugins_dir = _expand(data.get("plugins_dir", DEFAULT_TOML["data"]["plugins_dir"]))
    log_dir = _expand(data.get("log_dir", DEFAULT_TOML["data"]["log_dir"]))
    audit_log = _expand(data.get("audit_log", DEFAULT_TOML["data"]["audit_log"]))

    for p in [data_dir, plugins_dir, log_dir, audit_log.parent]:
        p.mkdir(parents=True, exist_ok=True)

    return Config(
        raw=merged,
        data_dir=data_dir,
        plugins_dir=plugins_dir,
        log_dir=log_dir,
        audit_log=audit_log,
        default_table=merged.get("log", {}).get("default_table_name", "events"),
    )
