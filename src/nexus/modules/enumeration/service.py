from __future__ import annotations
import re
from pathlib import Path

EXT_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ header",
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

# Regex signatures for content-based detection. Each language has a list of
# (weight, compiled_pattern) rules; matches are summed into a raw score and
# then normalized to a 0..1 confidence.
_SIGNATURES = {
    "Python": [
        (3, r"^\s*def\s+\w+\s*\(.*\)\s*:"),
        (3, r"^\s*(from\s+[\w.]+\s+)?import\s+\w+"),
        (2, r"\bprint\s*\("),
        (2, r'^\s*(if|elif|else|for|while|with|class)\b.*:\s*$'),
        (2, r'\b__\w+__\b'),
        (1, r"\bself\b"),
        (1, r"\b(None|True|False)\b"),
    ],
    "JavaScript": [
        (3, r"\b(const|let|var)\s+\w+\s*="),
        (3, r"\bfunction\s*\*?\s*\w*\s*\("),
        (2, r"=>\s*[{(]"),
        (2, r"\bconsole\.(log|error|warn)\s*\("),
        (2, r"\brequire\s*\(|\bmodule\.exports\b"),
        (1, r"\bdocument\.|window\."),
    ],
    "TypeScript": [
        (3, r":\s*(string|number|boolean|any|void|unknown)\b"),
        (3, r"\b(interface|type)\s+\w+\s*[={]"),
        (2, r"\b(enum|namespace)\s+\w+"),
        (2, r"\b(public|private|protected|readonly)\s+\w+"),
        (2, r"\bimport\s+.*\bfrom\s+['\"]"),
    ],
    "Java": [
        (3, r"\b(public|private|protected)\s+(static\s+)?(final\s+)?(class|interface|enum)\s+\w+"),
        (3, r"\bpublic\s+static\s+void\s+main\s*\("),
        (2, r"\bSystem\.out\.print"),
        (2, r"\bimport\s+[\w.]+;"),
        (1, r"\bnew\s+\w+\s*\("),
    ],
    "C++": [
        (3, r"#include\s*<(iostream|vector|string|map)>"),
        (3, r"\bstd::\w+"),
        (2, r"\b(cout|cin)\b\s*<<|>>"),
        (2, r"\btemplate\s*<"),
        (2, r"\b(namespace|using\s+namespace)\b"),
    ],
    "C": [
        (3, r"#include\s*<\w+\.h>"),
        (3, r"\bint\s+main\s*\([^)]*\)\s*{"),
        (2, r"\bprintf\s*\(|\bscanf\s*\("),
        (2, r"\b(malloc|free|sizeof)\b"),
        (1, r"\b(struct|typedef)\b"),
    ],
    "Go": [
        (3, r"\bpackage\s+\w+"),
        (3, r"\bfunc\s+(\(\w+\s+\*?\w+\)\s+)?\w+\s*\("),
        (2, r'\bimport\s+\('),
        (2, r"\bfmt\.(Print|Sprint)"),
        (2, r":=|\bchan\b|\bgo\s+\w+\("),
    ],
    "Rust": [
        (3, r"\bfn\s+\w+\s*\("),
        (3, r"\blet\s+(mut\s+)?\w+"),
        (2, r"\b(use|mod|impl|trait)\s+\w+"),
        (2, r"\bprintln!\s*\(|\bpanic!\s*\("),
        (2, r"->\s*\w+|&(mut\s+)?self\b"),
    ],
    "Ruby": [
        (3, r"\bdef\s+\w+[?!]?"),
        (2, r"\b(puts|require|require_relative)\b"),
        (2, r"\bend\b\s*$"),
        (2, r"\b(do|module)\b|\|\w+\|"),
        (1, r"\battr_(accessor|reader|writer)\b"),
    ],
    "PHP": [
        (3, r"<\?php\b"),
        (3, r"\$\w+\s*="),
        (2, r"\b(echo|function|namespace|use)\b"),
        (2, r"->\w+\s*\(|::\w+"),
    ],
    "Shell": [
        (3, r"^#!.*/(ba)?sh\b"),
        (2, r"\b(echo|export|source)\b"),
        (2, r"\$\{?\w+\}?|\$\(.*\)"),
        (2, r"\b(if|then|fi|for|do|done|case|esac)\b"),
    ],
    "PowerShell": [
        (3, r"\$\w+\s*="),
        (3, r"\b(Write-Host|Write-Output|Get-\w+|Set-\w+)\b"),
        (2, r"\bparam\s*\(|\[CmdletBinding\("),
        (2, r"\|\s*ForEach-Object|\-eq|\-ne\b"),
    ],
    "Lua": [
        (3, r"\bfunction\s+\w*\s*\("),
        (2, r"\blocal\s+\w+"),
        (2, r"\bend\b"),
        (2, r"\b(nil|then|elseif)\b|\.\."),
    ],
    "Swift": [
        (3, r"\bfunc\s+\w+\s*\("),
        (3, r"\b(let|var)\s+\w+\s*:"),
        (2, r"\bprint\s*\(|\bguard\s+let\b"),
        (2, r"\b(struct|class|enum|protocol)\s+\w+"),
    ],
}

_COMPILED = {
    lang: [(w, re.compile(p, re.MULTILINE)) for w, p in rules]
    for lang, rules in _SIGNATURES.items()
}


def _shebang_lang(first_line: str) -> str | None:
    if first_line.startswith("#!"):
        if "python" in first_line:
            return "Python"
        if "bash" in first_line or "sh" in first_line:
            return "Shell"
        if "node" in first_line:
            return "JavaScript"
        if "ruby" in first_line:
            return "Ruby"
        if "pwsh" in first_line or "powershell" in first_line:
            return "PowerShell"
        if "lua" in first_line:
            return "Lua"
    return None


def _score_snippet(code: str) -> list[dict]:
    """Score a code snippet against every language signature set."""
    results = []
    for lang, rules in _COMPILED.items():
        raw = 0
        hits = 0
        for weight, pattern in rules:
            if pattern.search(code):
                raw += weight
                hits += 1
        if raw == 0:
            continue
        max_weight = sum(w for w, _ in rules)
        # Confidence blends how much signature weight matched with how many
        # distinct rules fired, so a single strong keyword can't dominate.
        confidence = round(min(0.98, 0.15 + 0.75 * (raw / max_weight) + 0.05 * hits), 3)
        results.append({
            "language": lang,
            "confidence": confidence,
            "evidence": "content",
            "matched_rules": hits,
        })
    results.sort(key=lambda c: c["confidence"], reverse=True)
    return results


def detect_language(source: str) -> dict:
    """
    Identify the programming language of an inline code snippet.

    ``source`` is the code text itself (not a file path). Detection is based on
    a shebang line when present and on language-specific syntax signatures.
    """
    code = source if isinstance(source, str) else str(source)
    candidates: list[dict] = []

    first_line = code.splitlines()[0].strip() if code.strip() else ""
    shebang = _shebang_lang(first_line)
    if shebang:
        candidates.append({
            "language": shebang,
            "confidence": 0.95,
            "evidence": "shebang",
            "matched_rules": 1,
        })

    candidates.extend(_score_snippet(code))

    # Keep the highest-confidence entry per language.
    best: dict[str, dict] = {}
    for c in candidates:
        lang = c["language"]
        if lang not in best or c["confidence"] > best[lang]["confidence"]:
            best[lang] = c

    ordered = sorted(best.values(), key=lambda x: x["confidence"], reverse=True)
    if not ordered:
        ordered = [{"language": "Unknown", "confidence": 0.1, "evidence": "none", "matched_rules": 0}]

    return {"input_length": len(code), "candidates": ordered}


def detect_language_file(path: str | Path) -> dict:
    """Identify a language from a file on disk using its extension, shebang, and content."""
    p = Path(path)
    candidates: list[dict] = []

    ext = p.suffix.lower()
    if ext in EXT_MAP:
        candidates.append({"language": EXT_MAP[ext], "confidence": 0.7, "evidence": "extension", "matched_rules": 1})

    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        text = ""

    if text:
        first_line = text.splitlines()[0].strip() if text.strip() else ""
        lang = _shebang_lang(first_line)
        if lang:
            candidates.append({"language": lang, "confidence": 0.9, "evidence": "shebang", "matched_rules": 1})
        candidates.extend(_score_snippet(text))

    best: dict[str, dict] = {}
    for c in candidates:
        L = c["language"]
        if L not in best or c["confidence"] > best[L]["confidence"]:
            best[L] = c

    ordered = sorted(best.values(), key=lambda x: x["confidence"], reverse=True)
    if not ordered:
        ordered = [{"language": "Unknown", "confidence": 0.1, "evidence": "none", "matched_rules": 0}]

    return {"file": str(p), "candidates": ordered}
