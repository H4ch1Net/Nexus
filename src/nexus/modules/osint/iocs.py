"""Indicator-of-compromise extraction and defanging.

Pulls printable strings out of arbitrary files and classifies the common
network indicators an analyst cares about (URLs, domains, IPv4/IPv6, emails,
and hashes), plus reversible defang/refang helpers for safe sharing.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

_PATTERNS = {
    "url": re.compile(r"\b(?:https?|ftp)://[^\s<>\"'\\)]+", re.I),
    "email": re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    "ipv4": re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"),
    "ipv6": re.compile(r"\b(?:[A-Fa-f0-9]{1,4}:){2,7}[A-Fa-f0-9]{1,4}\b"),
    "domain": re.compile(r"\b(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b", re.I),
    "md5": re.compile(r"\b[a-f0-9]{32}\b", re.I),
    "sha1": re.compile(r"\b[a-f0-9]{40}\b", re.I),
    "sha256": re.compile(r"\b[a-f0-9]{64}\b", re.I),
    "btc": re.compile(r"\b(?:bc1[a-z0-9]{25,90}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b"),
}

# Domains that are almost always noise when harvested from binaries.
_DOMAIN_NOISE = re.compile(r"\.(png|jpg|jpeg|gif|css|js|dll|exe|so|dylib)$", re.I)


def extract_strings(data: bytes, min_len: int = 4) -> List[str]:
    """Extract printable ASCII runs of at least ``min_len`` characters."""
    return re.findall(rb"[\x20-\x7e]{%d,}" % min_len, data)  # type: ignore[return-value]


def _decoded_strings(data: bytes, min_len: int) -> List[str]:
    return [m.decode("ascii", "ignore") for m in extract_strings(data, min_len)]


def find_iocs(text: str) -> Dict[str, List[str]]:
    """Classify indicators found in a block of text, de-duplicated and ordered."""
    found: Dict[str, List[str]] = {}
    for name, pattern in _PATTERNS.items():
        seen: List[str] = []
        for match in pattern.findall(text):
            value = match if isinstance(match, str) else match[0]
            if name in ("url", "domain", "email"):
                # Trim trailing sentence punctuation the greedy match absorbed.
                value = value.rstrip(".,;:!?)]}'\"")
            if name == "domain" and _DOMAIN_NOISE.search(value):
                continue
            if value not in seen:
                seen.append(value)
        if seen:
            found[name] = seen
    # A URL's host also matches the domain pattern; keep domains that are not
    # merely substrings of captured URLs to reduce duplication noise.
    if "url" in found and "domain" in found:
        url_blob = " ".join(found["url"])
        found["domain"] = [d for d in found["domain"] if d not in url_blob] or found["domain"]
    return found


def analyze_file(path: str | Path, min_len: int = 4) -> Dict:
    """Extract strings and IOCs from a file on disk."""
    p = Path(path)
    data = p.read_bytes()
    strings = _decoded_strings(data, min_len)
    iocs = find_iocs("\n".join(strings))
    return {
        "file": str(p),
        "file_size_bytes": len(data),
        "string_count": len(strings),
        "iocs": iocs,
        "ioc_total": sum(len(v) for v in iocs.values()),
    }


# ----------------------------------------------------------------------------
# Defang / refang
# ----------------------------------------------------------------------------
def defang(text: str) -> str:
    """Neutralize indicators so they are safe to paste in reports/chats."""
    out = text
    out = re.sub(r"(?i)\bhttps\b", "hxxps", out)
    out = re.sub(r"(?i)\bhttp\b", "hxxp", out)
    out = re.sub(r"(?i)\bftp\b", "fxp", out)
    out = out.replace("://", "[://]")
    out = re.sub(r"\.", "[.]", out)
    out = out.replace("@", "[@]")
    return out


def refang(text: str) -> str:
    """Reverse :func:`defang`."""
    out = text
    out = out.replace("[.]", ".").replace("[:]", ":").replace("[://]", "://")
    out = out.replace("(.)", ".").replace("{.}", ".")
    out = out.replace("[@]", "@").replace("(@)", "@")
    out = re.sub(r"(?i)\bhxxps\b", "https", out)
    out = re.sub(r"(?i)\bhxxp\b", "http", out)
    out = re.sub(r"(?i)\bfxp\b", "ftp", out)
    return out
