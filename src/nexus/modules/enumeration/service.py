from __future__ import annotations
from pathlib import Path

EXT_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C header",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".sh": "Shell",
    ".ps1": "PowerShell",
    ".php": "PHP",
    ".lua": "Lua",
    ".swift": "Swift",
}

def _shebang_lang(first_line: str) -> str | None:
    if first_line.startswith("#!"):
        if "python" in first_line: return "Python"
        if "bash" in first_line or "sh" in first_line: return "Shell"
        if "node" in first_line: return "JavaScript"
        if "ruby" in first_line: return "Ruby"
    return None

def detect_language(path: Path) -> dict:
    p = Path(path)
    candidates = []
    ext = p.suffix.lower()
    if ext in EXT_MAP:
        candidates.append({"language": EXT_MAP[ext], "confidence": 0.7, "evidence": "extension"})
    try:
        with p.open('r', encoding='utf-8', errors='ignore') as f:
            first = f.readline().strip()
        lang = _shebang_lang(first)
        if lang:
            candidates.append({"language": lang, "confidence": 0.9, "evidence": "shebang"})
    except Exception:
        pass
    if not candidates:
        candidates.append({"language": "Unknown", "confidence": 0.1, "evidence": "none"})
    best = {}
    for c in candidates:
        L = c["language"]
        if L not in best or c["confidence"] > best[L]["confidence"]:
            best[L] = c
    ordered = sorted(best.values(), key=lambda x: x["confidence"], reverse=True)
    return {"file": str(p), "candidates": ordered}
