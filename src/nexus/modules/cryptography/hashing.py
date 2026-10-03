"""Hashing utilities: digest computation and hash-type identification."""
from __future__ import annotations

import hashlib
import re
import zlib
from pathlib import Path
from typing import Dict, List

# Algorithms computed by `crypt hash` (name -> hashlib constructor key / special).
_ALGOS = [
    "md5", "sha1", "sha224", "sha256", "sha384", "sha512",
    "sha3_256", "sha3_512", "blake2b", "blake2s",
]


def compute_hashes(data: bytes) -> Dict[str, str]:
    """Return a mapping of algorithm -> hex digest for the given bytes."""
    out: Dict[str, str] = {}
    for algo in _ALGOS:
        out[algo] = hashlib.new(algo, data).hexdigest()
    out["crc32"] = format(zlib.crc32(data) & 0xFFFFFFFF, "08x")
    return out


def hash_file(path: str | Path) -> Dict[str, str]:
    p = Path(path)
    hashers = {a: hashlib.new(a) for a in _ALGOS}
    crc = 0
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            for h in hashers.values():
                h.update(chunk)
            crc = zlib.crc32(chunk, crc)
    out = {a: h.hexdigest() for a, h in hashers.items()}
    out["crc32"] = format(crc & 0xFFFFFFFF, "08x")
    return out


# Length (hex chars) -> candidate algorithms, ranked most-likely first.
_BY_LENGTH = {
    8: ["CRC-32", "Adler-32", "FNV-1a (32-bit)"],
    16: ["MySQL323", "CRC-64"],
    32: ["MD5", "NTLM", "MD4", "LM", "MD2", "RIPEMD-128"],
    40: ["SHA-1", "RIPEMD-160", "HAS-160"],
    56: ["SHA-224", "SHA3-224"],
    64: ["SHA-256", "SHA3-256", "BLAKE2s-256", "Keccak-256", "RIPEMD-256"],
    96: ["SHA-384", "SHA3-384"],
    128: ["SHA-512", "SHA3-512", "BLAKE2b-512", "Whirlpool", "Keccak-512"],
}

# Prefix-based identification for modular crypt / structured formats.
_PREFIX = [
    (re.compile(r"^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$"), "bcrypt"),
    (re.compile(r"^\$1\$"), "md5crypt"),
    (re.compile(r"^\$5\$"), "sha256crypt"),
    (re.compile(r"^\$6\$"), "sha512crypt"),
    (re.compile(r"^\$y\$"), "yescrypt"),
    (re.compile(r"^\$argon2(id|i|d)\$"), "Argon2"),
    (re.compile(r"^\$pbkdf2(-sha\d+)?\$"), "PBKDF2"),
    (re.compile(r"^\$scrypt\$|^SCRYPT:"), "scrypt"),
    (re.compile(r"^{SSHA}"), "SSHA (LDAP)"),
    (re.compile(r"^{SHA}"), "SHA-1 (LDAP)"),
    (re.compile(r"^\$P\$|^\$H\$"), "phpass"),
    (re.compile(r"^[0-9a-f]{32}:[0-9a-f]{32}$", re.I), "MD5(salted) or NTLM:hash"),
    (re.compile(r"^[0-9a-f]{32}:.+$", re.I), "MD5 with salt"),
    (re.compile(r"^sha1\$"), "Django SHA-1"),
    (re.compile(r"^pbkdf2_sha256\$"), "Django PBKDF2-SHA256"),
]


def identify_hash(value: str) -> List[Dict]:
    """Identify likely hash algorithms for a string by prefix, length and charset."""
    s = value.strip()
    if not s:
        return []

    candidates: List[Dict] = []
    for pattern, name in _PREFIX:
        if pattern.search(s):
            candidates.append({"name": name, "confidence": 0.95, "basis": "format"})
    if candidates:
        return candidates

    is_hex = bool(re.fullmatch(r"[0-9a-fA-F]+", s))
    length = len(s)
    if is_hex and length in _BY_LENGTH:
        names = _BY_LENGTH[length]
        for i, name in enumerate(names):
            # First candidate is most common; taper confidence for the rest.
            conf = round(max(0.3, 0.8 - i * 0.12), 2)
            candidates.append({"name": name, "confidence": conf, "basis": f"hex, {length} chars"})
        return candidates

    if re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", s) and length in (24, 28, 44, 88):
        guess = {24: "MD5 (base64)", 28: "SHA-1 (base64)", 44: "SHA-256 (base64)", 88: "SHA-512 (base64)"}
        candidates.append({"name": guess[length], "confidence": 0.5, "basis": f"base64, {length} chars"})
        return candidates

    if is_hex:
        candidates.append({"name": "Unknown hex digest", "confidence": 0.2, "basis": f"hex, {length} chars"})
    return candidates
