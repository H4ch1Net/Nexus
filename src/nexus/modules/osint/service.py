from __future__ import annotations
from pathlib import Path
import hashlib, mimetypes

def _hashes(path: Path) -> dict:
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            md5.update(chunk); sha1.update(chunk); sha256.update(chunk)
    return {"md5": md5.hexdigest(), "sha1": sha1.hexdigest(), "sha256": sha256.hexdigest()}

def extract_meta(input_path: str) -> dict:
    p = Path(input_path)
    if not p.exists():
        return {}
    size = p.stat().st_size
    mime, _ = mimetypes.guess_type(p.name)
    return {
        "file": str(p),
        "file_size_bytes": size,
        "file_mime": mime or "application/octet-stream",
        "hashes": _hashes(p),
        "metadata": {},
        "gps": None,
        "map_link": None,
        "warnings": [],
    }