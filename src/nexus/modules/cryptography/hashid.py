from __future__ import annotations
import re

# (name, pattern, base_score). Multiple entries can match the same length
# (e.g. 32 hex chars matches MD5, NTLM, MD4) - all are returned, ranked by
# how distinctive the pattern is rather than pure length.
HASH_PATTERNS = [
    ("bcrypt", re.compile(r'^\$2[aby]?\$\d{2}\$[./A-Za-z0-9]{53}$'), 0.97),
    ("argon2", re.compile(r'^\$argon2(id|i|d)\$'), 0.97),
    ("scrypt", re.compile(r'^\$scrypt\$'), 0.95),
    ("md5crypt", re.compile(r'^\$1\$[./A-Za-z0-9]{0,8}\$[./A-Za-z0-9]{22}$'), 0.95),
    ("sha256crypt", re.compile(r'^\$5\$[./A-Za-z0-9]{0,16}\$[./A-Za-z0-9]{43}$'), 0.95),
    ("sha512crypt", re.compile(r'^\$6\$[./A-Za-z0-9]{0,16}\$[./A-Za-z0-9]{86}$'), 0.95),
    ("mysql5", re.compile(r'^\*[A-F0-9]{40}$'), 0.93),
    ("ldap_ssha", re.compile(r'^\{SSHA\}[A-Za-z0-9+/=]+$'), 0.92),
    ("jwt", re.compile(r'^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$'), 0.9),
    ("mysql_old", re.compile(r'^[a-f0-9]{16}$', re.I), 0.4),
    ("crc32", re.compile(r'^[a-f0-9]{8}$', re.I), 0.3),
    ("md5", re.compile(r'^[a-f0-9]{32}$', re.I), 0.55),
    ("ntlm", re.compile(r'^[a-f0-9]{32}$', re.I), 0.4),
    ("md4", re.compile(r'^[a-f0-9]{32}$', re.I), 0.25),
    ("sha1", re.compile(r'^[a-f0-9]{40}$', re.I), 0.6),
    ("mysql5_unsalted", re.compile(r'^[a-f0-9]{40}$', re.I), 0.2),
    ("sha224", re.compile(r'^[a-f0-9]{56}$', re.I), 0.6),
    ("sha3_256", re.compile(r'^[a-f0-9]{64}$', re.I), 0.35),
    ("sha256", re.compile(r'^[a-f0-9]{64}$', re.I), 0.6),
    ("sha384", re.compile(r'^[a-f0-9]{96}$', re.I), 0.65),
    ("sha3_512", re.compile(r'^[a-f0-9]{128}$', re.I), 0.35),
    ("sha512", re.compile(r'^[a-f0-9]{128}$', re.I), 0.65),
    ("whirlpool", re.compile(r'^[a-f0-9]{128}$', re.I), 0.2),
]


def identify_hash(text: str) -> dict:
    text = text.strip()
    candidates = []
    for name, pattern, score in HASH_PATTERNS:
        if pattern.match(text):
            candidates.append({"name": name, "score": score})
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return {"input": text, "length": len(text), "candidates": candidates}
