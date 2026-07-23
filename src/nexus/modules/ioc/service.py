from __future__ import annotations
import re

_IPV4 = r'\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b'
_IPV6 = r'\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b'
_EMAIL = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
_URL = r'\bhttps?://[^\s"\'<>]+[^\s"\'<>.,;:!?)\]]'
_DOMAIN = r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'
_MD5 = r'\b[a-fA-F0-9]{32}\b'
_SHA1 = r'\b[a-fA-F0-9]{40}\b'
_SHA256 = r'\b[a-fA-F0-9]{64}\b'
_CVE = r'\bCVE-\d{4}-\d{4,7}\b'
_BTC = r'\b(?:bc1[a-z0-9]{25,39}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b'
_ETH = r'\b0x[a-fA-F0-9]{40}\b'
_MAC = r'\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b'
_WIN_PATH = r'\b[A-Za-z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]+'
_REGISTRY_KEY = r'\bHK(?:EY_)?(?:LM|CU|CR|U|CC|LOCAL_MACHINE|CURRENT_USER|CLASSES_ROOT|USERS|CURRENT_CONFIG)\\[^\s"\']+'

PATTERNS = {
    "ipv4": re.compile(_IPV4),
    "ipv6": re.compile(_IPV6),
    "email": re.compile(_EMAIL),
    "url": re.compile(_URL, re.I),
    "domain": re.compile(_DOMAIN),
    "md5": re.compile(_MD5),
    "sha1": re.compile(_SHA1),
    "sha256": re.compile(_SHA256),
    "cve": re.compile(_CVE, re.I),
    "btc_address": re.compile(_BTC),
    "eth_address": re.compile(_ETH),
    "mac_address": re.compile(_MAC),
    "windows_path": re.compile(_WIN_PATH),
    "registry_key": re.compile(_REGISTRY_KEY, re.I),
}

# Evaluation order matters: hashes are pure hex and would also match nothing
# else, but domain/email/url can overlap (an email's host also looks like a
# domain). We keep every category independent rather than suppressing
# overlaps - a domain list that also contains email hosts is still useful
# for a defender scanning a triage note.
CATEGORY_ORDER = [
    "ipv4", "ipv6", "mac_address", "email", "url", "domain",
    "cve", "btc_address", "eth_address", "sha256", "sha1", "md5",
    "windows_path", "registry_key",
]


def extract(text: str) -> dict:
    iocs: dict[str, list[str]] = {}
    for name in CATEGORY_ORDER:
        pattern = PATTERNS[name]
        matches = sorted(set(pattern.findall(text)))
        if matches:
            iocs[name] = matches

    total = sum(len(v) for v in iocs.values())
    return {"input_length": len(text), "total_matches": total, "iocs": iocs}
