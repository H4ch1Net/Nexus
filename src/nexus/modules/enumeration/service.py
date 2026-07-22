from __future__ import annotations
import re

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

# Content-based signatures: language -> list of (compiled pattern, weight).
# Weights are heuristic, not calibrated against a corpus.
LANG_SIGNATURES: dict[str, list[tuple[re.Pattern, float]]] = {
    "Python": [
        (re.compile(r"^\s*def\s+\w+\s*\("), 0.3),
        (re.compile(r"^\s*import\s+\w+"), 0.2),
        (re.compile(r"^\s*from\s+\w+\s+import\s+"), 0.25),
        (re.compile(r"^\s*class\s+\w+.*:\s*$"), 0.2),
        (re.compile(r"\bself\b"), 0.15),
        (re.compile(r"^\s*elif\b"), 0.2),
    ],
    "JavaScript": [
        (re.compile(r"\bfunction\s*\w*\s*\("), 0.25),
        (re.compile(r"\b(const|let|var)\s+\w+\s*="), 0.2),
        (re.compile(r"=>"), 0.2),
        (re.compile(r"\bconsole\.log\("), 0.25),
        (re.compile(r"\brequire\(['\"]"), 0.2),
    ],
    "TypeScript": [
        (re.compile(r"\binterface\s+\w+"), 0.3),
        (re.compile(r":\s*(string|number|boolean|void|any)\b"), 0.25),
        (re.compile(r"\bexport\s+(type|interface|class)\b"), 0.25),
    ],
    "C++": [
        (re.compile(r"#include\s*<iostream>"), 0.35),
        (re.compile(r"\bstd::"), 0.3),
        (re.compile(r"\bcout\s*<<"), 0.3),
        (re.compile(r"\bnamespace\s+\w+"), 0.2),
    ],
    "C": [
        (re.compile(r"#include\s*<\w+\.h>"), 0.3),
        (re.compile(r"\bprintf\s*\("), 0.25),
        (re.compile(r"\bint\s+main\s*\(\s*(void|int argc)"), 0.3),
    ],
    "Java": [
        (re.compile(r"\bpublic\s+static\s+void\s+main\s*\("), 0.4),
        (re.compile(r"\bSystem\.out\.println\("), 0.3),
        (re.compile(r"\bpublic\s+class\s+\w+"), 0.25),
    ],
    "Go": [
        (re.compile(r"^\s*package\s+main"), 0.3),
        (re.compile(r"\bfunc\s+\w+\s*\("), 0.25),
        (re.compile(r":="), 0.2),
        (re.compile(r"\bfmt\.Print"), 0.25),
    ],
    "Rust": [
        (re.compile(r"\bfn\s+\w+\s*\("), 0.3),
        (re.compile(r"\blet\s+mut\b"), 0.25),
        (re.compile(r"\bprintln!\("), 0.3),
        (re.compile(r"::<"), 0.15),
    ],
    "Ruby": [
        (re.compile(r"^\s*def\s+\w+.*\n(.|\n)*^\s*end\s*$", re.MULTILINE), 0.2),
        (re.compile(r"\bputs\s+"), 0.25),
        (re.compile(r"\battr_accessor\b"), 0.25),
        (re.compile(r"\bend\s*$", re.MULTILINE), 0.15),
    ],
    "Shell": [
        (re.compile(r"^#!.*\b(sh|bash)\b"), 0.3),
        (re.compile(r"\becho\s+"), 0.2),
        (re.compile(r"^\s*if\s*\["), 0.25),
        (re.compile(r"\bfi\s*$", re.MULTILINE), 0.2),
    ],
    "PHP": [
        (re.compile(r"<\?php"), 0.4),
        (re.compile(r"\$\w+\s*="), 0.2),
        (re.compile(r"\becho\s+"), 0.15),
    ],
}


def _shebang_lang(first_line: str) -> str | None:
    if first_line.startswith("#!"):
        if "python" in first_line: return "Python"
        if "bash" in first_line or "sh" in first_line: return "Shell"
        if "node" in first_line: return "JavaScript"
        if "ruby" in first_line: return "Ruby"
    return None


def _extension_lang(filename: str | None) -> str | None:
    if not filename:
        return None
    for ext, lang in EXT_MAP.items():
        if filename.lower().endswith(ext):
            return lang
    return None


def _content_candidates(source: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    for lang, signatures in LANG_SIGNATURES.items():
        score = 0.0
        for pattern, weight in signatures:
            if pattern.search(source):
                score += weight
        if score > 0:
            scores[lang] = min(score, 0.95)
    return scores


def detect_language(source: str, filename: str | None = None) -> dict:
    """Detect the language of an inline code snippet.

    `source` is the raw snippet text (not a file path). `filename` is an
    optional hint (e.g. "foo.py") used only for its extension - it is never
    opened or read from disk.
    """
    candidates: dict[str, dict] = {}

    ext_lang = _extension_lang(filename)
    if ext_lang:
        candidates[ext_lang] = {"language": ext_lang, "confidence": 0.7, "evidence": "extension"}

    first_line = source.splitlines()[0].strip() if source.splitlines() else ""
    shebang_lang = _shebang_lang(first_line)
    if shebang_lang:
        existing = candidates.get(shebang_lang)
        if not existing or 0.9 > existing["confidence"]:
            candidates[shebang_lang] = {"language": shebang_lang, "confidence": 0.9, "evidence": "shebang"}

    for lang, score in _content_candidates(source).items():
        existing = candidates.get(lang)
        if existing:
            # Corroborating signal: nudge confidence up, capped at 0.97.
            existing["confidence"] = min(0.97, existing["confidence"] + score * 0.3)
            existing["evidence"] = f"{existing['evidence']}+content"
        else:
            candidates[lang] = {"language": lang, "confidence": score, "evidence": "content"}

    if not candidates:
        candidates["Unknown"] = {"language": "Unknown", "confidence": 0.1, "evidence": "none"}

    for c in candidates.values():
        c["confidence"] = round(c["confidence"], 4)

    ordered = sorted(candidates.values(), key=lambda x: x["confidence"], reverse=True)
    return {"filename": filename, "candidates": ordered}
