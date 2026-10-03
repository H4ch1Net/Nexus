"""Shared terminal rendering helpers.

Small, dependency-free utilities for colored output, key/value blocks,
tables, and score bars. Color is disabled automatically when stdout is not a
TTY or when the NO_COLOR environment variable is set, so piped output stays
clean and script-friendly.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Callable, Iterable, Sequence

_CODES = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "gray": "\033[90m",
}


def color_enabled(stream=None) -> bool:
    """Report whether ANSI color should be emitted for the given stream."""
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("NEXUS_FORCE_COLOR") is not None:
        return True
    stream = stream or sys.stdout
    try:
        return bool(stream.isatty())
    except Exception:
        return False


def c(text: str, *styles: str, stream=None) -> str:
    """Wrap text in ANSI styles when color is enabled."""
    if not styles or not color_enabled(stream):
        return text
    prefix = "".join(_CODES.get(s, "") for s in styles)
    return f"{prefix}{text}{_CODES['reset']}"


def heading(text: str) -> str:
    """A bold, underlined section heading."""
    return c(text, "bold", "cyan")


def rule(width: int = 64, ch: str = "─") -> str:
    return c(ch * width, "gray")


def kv(pairs: Sequence[tuple[str, Any]], key_width: int | None = None) -> str:
    """Render aligned key/value lines."""
    rows = [(str(k), "" if v is None else str(v)) for k, v in pairs]
    if not rows:
        return ""
    width = key_width or max(len(k) for k, _ in rows)
    return "\n".join(f"  {c(k.ljust(width), 'gray')}  {v}" for k, v in rows)


def table(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    """Render a simple fixed-width table."""
    rows = [[("" if v is None else str(v)) for v in r] for r in rows]
    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(cell))
    header_line = "  ".join(c(h.ljust(widths[i]), "bold") for i, h in enumerate(headers))
    sep = c("  ".join("─" * w for w in widths), "gray")
    body = [
        "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(r))
        for r in rows
    ]
    return "\n".join([header_line, sep, *body])


def bar(score: float, width: int = 24) -> str:
    """A proportional block bar for a 0..1 score, color-coded by magnitude."""
    score = max(0.0, min(1.0, float(score)))
    filled = int(round(score * width))
    style = "green" if score >= 0.85 else "yellow" if score >= 0.6 else "red"
    return c("█" * filled, style) + c("░" * (width - filled), "gray")


def confidence_word(score: float) -> str:
    if score >= 0.85:
        return c("very high", "green")
    if score >= 0.70:
        return c("high", "green")
    if score >= 0.55:
        return c("medium", "yellow")
    return c("low", "red")


def dumps(obj: Any) -> str:
    """Canonical JSON for machine-readable output."""
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
