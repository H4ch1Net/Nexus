from __future__ import annotations
from pathlib import Path
import math, string

BASE58_ALPHABET = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")

def _read_bytes(p: Path) -> bytes:
    with p.open('rb') as f:
        return f.read()

def _entropy(data: bytes) -> float:
    if not data:
        return 0.0
    freqs = [0]*256
    for b in data:
        freqs[b]+=1
    ent = 0.0
    n = len(data)
    for c in freqs:
        if c:
            p = c/n
            ent -= p*math.log2(p)
    return ent

def _printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    printable = set(bytes(string.printable, 'ascii'))
    return sum(1 for b in data if b in printable)/len(data)

def _starts_with(data: bytes, sig: bytes) -> bool:
    return data.startswith(sig)

def _is_base64ish(s: bytes) -> float:
    allowed = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
    if not s:
        return 0.0
    ok = sum(1 for b in s if b in allowed)
    return ok/len(s)

def _is_base32ish(s: bytes) -> float:
    allowed = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567=")
    if not s:
        return 0.0
    ok = sum(1 for b in s if b in allowed)
    return ok/len(s)

def _is_base58ish(s: bytes) -> float:
    if not s:
        return 0.0
    ok = sum(1 for b in s if chr(b) in BASE58_ALPHABET)
    return ok/len(s)

def detect(input_path: str) -> dict:
    p = Path(input_path)
    data = _read_bytes(p)
    ent = _entropy(data)
    pr = _printable_ratio(data)

    candidates = []

    if _starts_with(data, b"%PDF"):
        candidates.append({"name": "pdf", "score": 1.0, "params": {}})
    if _starts_with(data, b"PK\x03\x04"):
        candidates.append({"name": "zip", "score": 0.95, "params": {}})
    if _starts_with(data, b"\x1f\x8b\x08"):
        candidates.append({"name": "gzip", "score": 0.9, "params": {}})

    b64 = _is_base64ish(data)
    if b64 > 0.9:
        candidates.append({"name": "base64", "score": 0.8 + 0.2*b64, "params": {}})
    b32 = _is_base32ish(data)
    if b32 > 0.9:
        candidates.append({"name": "base32", "score": 0.75 + 0.25*b32, "params": {}})
    b58 = _is_base58ish(data)
    if b58 > 0.9:
        candidates.append({"name": "base58", "score": 0.7 + 0.3*b58, "params": {}})

    txt = {"name": "text", "score": max(0.0, pr - (ent/8.0)*0.2), "params": {"printable_ratio": pr}}
    binhint = {"name": "binary", "score": max(0.0, (ent/8.0) - pr*0.2), "params": {"entropy": ent}}
    candidates.extend([txt, binhint])

    candidates.sort(key=lambda c: c["score"], reverse=True)

    return {
        "file": str(p),
        "size_bytes": len(data),
        "metrics": {"entropy": ent, "printable_ratio": pr},
        "candidates": candidates[:10],
    }
