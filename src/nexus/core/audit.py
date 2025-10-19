from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, uuid

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def audit(cfg, *, module: str, action: str, target: str = "", payload: bytes | None = None,
          bytes_sent: int = 0, provider: str = "", result_id: str = "", success_bool: bool = True,
          notes: str = "") -> None:
    sha = hashlib.sha256(payload).hexdigest() if payload else ""
    rec = {
        "timestamp_utc": _now_iso(),
        "module": module,
        "action": action,
        "target": target,
        "payload_sha256": f"sha256:{sha}" if sha else "",
        "bytes_sent": bytes_sent,
        "provider": provider,
        "result_id": result_id or str(uuid.uuid4()),
        "success_bool": success_bool,
        "notes": notes,
    }
    path: Path = cfg.audit_log
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
