from __future__ import annotations
import re
from nexus.modules.cryptography.service import _entropy

# (name, pattern, severity)
SECRET_PATTERNS = [
    ("private_key_header", re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----'), "critical"),
    ("aws_access_key_id", re.compile(r'\b(?:AKIA|ASIA)[0-9A-Z]{16}\b'), "high"),
    ("aws_secret_access_key", re.compile(r'(?i)\baws_secret_access_key\s*[:=]\s*[\'"]?([A-Za-z0-9/+=]{40})[\'"]?'), "high"),
    ("github_token", re.compile(r'\bgh[pousr]_[A-Za-z0-9]{36,255}\b'), "high"),
    ("gitlab_token", re.compile(r'\bglpat-[A-Za-z0-9_-]{20}\b'), "high"),
    ("slack_token", re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{10,72}\b'), "high"),
    ("slack_webhook", re.compile(r'https://hooks\.slack\.com/services/[A-Za-z0-9/]+'), "high"),
    ("google_api_key", re.compile(r'\bAIza[0-9A-Za-z_-]{35}\b'), "high"),
    ("stripe_key", re.compile(r'\b[sp]k_(?:live|test)_[A-Za-z0-9]{16,247}\b'), "high"),
    ("npm_token", re.compile(r'\bnpm_[A-Za-z0-9]{36}\b'), "high"),
    ("twilio_key", re.compile(r'\bSK[a-z0-9]{32}\b', re.I), "high"),
    ("heroku_api_key", re.compile(r'(?i)\bheroku[a-z0-9_ ]{0,20}[:=]\s*[\'"]?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}[\'"]?'), "medium"),
    ("basic_auth_url", re.compile(r'\b[a-zA-Z][a-zA-Z0-9+.-]*://[^\s:@/]+:[^\s:@/]+@'), "high"),
    ("jwt", re.compile(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b'), "medium"),
    ("generic_api_key", re.compile(r'(?i)\b(?:api[_-]?key|apikey|access[_-]?token|auth[_-]?token)\s*[:=]\s*[\'"]?([A-Za-z0-9_\-]{16,64})[\'"]?'), "medium"),
    ("generic_password", re.compile(r'(?i)\bpassword\s*[:=]\s*[\'"]?(\S{6,})[\'"]?'), "low"),
]

_ENTROPY_TOKEN = re.compile(r'[A-Za-z0-9_\-+/=]{20,}')
_ENTROPY_THRESHOLD = 4.3
_MAX_FINDINGS = 200


def _redact(s: str) -> str:
    if len(s) <= 8:
        return "*" * len(s)
    return s[:4] + "*" * (len(s) - 8) + s[-4:]


def scan(text: str) -> dict:
    findings = []
    matched_spans: list[tuple[int, int]] = []

    for name, pattern, severity in SECRET_PATTERNS:
        for m in pattern.finditer(text):
            matched_spans.append((m.start(), m.end()))
            # Redact just the captured secret value when the pattern has a
            # group (e.g. "aws_secret_access_key = ****"), not the whole
            # match, so the field-name context stays readable.
            whole = m.group(0)
            secret_part = m.group(1) if m.groups() else whole
            display = whole.replace(secret_part, _redact(secret_part), 1)
            findings.append({
                "type": name,
                "match": display,
                "severity": severity,
                "offset": m.start(),
            })
            if len(findings) >= _MAX_FINDINGS:
                break
        if len(findings) >= _MAX_FINDINGS:
            break

    # Entropy-based fallback for tokens not caught by a known pattern.
    if len(findings) < _MAX_FINDINGS:
        for m in _ENTROPY_TOKEN.finditer(text):
            if len(findings) >= _MAX_FINDINGS:
                break
            start, end = m.start(), m.end()
            if any(s <= start < e or s < end <= e for s, e in matched_spans):
                continue
            tok = m.group(0)
            ent = _entropy(tok.encode())
            if ent >= _ENTROPY_THRESHOLD:
                findings.append({
                    "type": "high_entropy_string",
                    "match": _redact(tok),
                    "severity": "low",
                    "offset": start,
                    "entropy": round(ent, 3),
                })

    findings.sort(key=lambda f: f["offset"])
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings.sort(key=lambda f: severity_rank.get(f["severity"], 9))

    return {
        "input_length": len(text),
        "findings_count": len(findings),
        "findings": findings,
    }
