"""Shared terminal rendering: the CLI side of the Field Instrument design.

Same rules as the web console: neutral ink, one signal color (orange), hairline
rules, condensed uppercase labels, and instrument-style meters and scales. Color
is disabled automatically when stdout is not a TTY or NO_COLOR is set, so piped
output stays clean and script-friendly.
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Iterable, Mapping, Sequence

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _truecolor() -> bool:
    return os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit")


def _styles() -> dict[str, str]:
    signal = "38;2;242;90;26" if _truecolor() else "38;5;202"
    return {
        "reset": "0",
        "bold": "1",
        "dim": "2",
        "signal": signal,
        "muted": "38;5;245",
        "faint": "38;5;240",
        "critical": "38;5;203",
        # Legacy names kept so older call sites keep working.
        "red": "38;5;203",
        "yellow": signal,
        "green": signal,
        "cyan": signal,
        "blue": "4",
        "gray": "38;5;245",
        "white": "37",
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


def c(text: Any, *styles: str, stream=None) -> str:
    """Wrap text in ANSI styles when color is enabled."""
    text = str(text)
    if not styles or not color_enabled(stream):
        return text
    table = _styles()
    codes = ";".join(table[s] for s in styles if s in table)
    return f"\x1b[{codes}m{text}\x1b[0m" if codes else text


def visible_len(text: str) -> int:
    """Printable width of a string that may contain ANSI escapes."""
    return len(_ANSI.sub("", text))


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - visible_len(text))


# ----------------------------------------------------------------------------
# Brand
# ----------------------------------------------------------------------------
# The Polybius-square "N" (5x5 cipher grid) rendered with half blocks so each
# cell is roughly square. Diagonal cells carry the signal color.
_MARK = [
    [("█", 0), ("▄", 1), (" ", 0), (" ", 0), ("█", 0)],
    [("█", 0), (" ", 0), ("▀", 1), ("▄", 1), ("█", 0)],
    [("▀", 0), (" ", 0), (" ", 0), (" ", 0), ("▀", 0)],
]


def mark() -> list[str]:
    """Three terminal lines drawing the Nexus mark."""
    return ["".join(c(ch, "signal") if sig else ch for ch, sig in row) for row in _MARK]


def lockup(lines: Sequence[str]) -> str:
    """The mark beside up to three lines of text."""
    rows = mark()
    lines = list(lines) + [""] * (3 - len(lines))
    return "\n".join(f"{m}  {t}".rstrip() for m, t in zip(rows, lines))


# ----------------------------------------------------------------------------
# Typographic primitives
# ----------------------------------------------------------------------------
def label(text: str) -> str:
    """Datasheet label: uppercase, muted."""
    return c(str(text).upper(), "muted")


def rule(width: int = 64, ch: str = "─") -> str:
    return c(ch * width, "faint")


def header(title: str, code: str = "", module: str = "", width: int = 64) -> str:
    """Section header: signal square, title, right-aligned index code, hairline."""
    left = f"{c('■', 'signal')} {c(title, 'bold')}"
    right = " · ".join(p for p in (c(code, 'signal') if code else "", label(module) if module else "") if p)
    gap = max(2, width - visible_len(left) - visible_len(right))
    return f"{left}{' ' * gap}{right}\n{rule(width)}"


def heading(text: str) -> str:
    """Backwards-compatible bare heading."""
    return f"{c('■', 'signal')} {c(text, 'bold')}"


def kv(pairs: Sequence[tuple[str, Any]], key_width: int | None = None) -> str:
    """Aligned key/value lines with datasheet labels."""
    rows = [(str(k), "" if v is None else str(v)) for k, v in pairs]
    if not rows:
        return ""
    width = key_width or max(len(k) for k, _ in rows)
    out = []
    for k, v in rows:
        lines = v.split("\n")
        out.append(f"  {_pad(label(k), width)}  {lines[0]}")
        out.extend(f"  {' ' * width}  {extra}" for extra in lines[1:])
    return "\n".join(out)


def table(headers: Sequence[str], rows: Iterable[Sequence[Any]], *, align: Mapping[int, str] | None = None) -> str:
    """Fixed-width table; cells may contain ANSI color and still align."""
    align = align or {}
    rows = [[("" if v is None else str(v)) for v in r] for r in rows]
    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], visible_len(cell))

    def fmt(cell: str, i: int) -> str:
        if align.get(i) == "right":
            return " " * (widths[i] - visible_len(cell)) + cell
        return _pad(cell, widths[i])

    head = "  ".join(_pad(label(h), widths[i]) for i, h in enumerate(headers))
    sep = c("  ".join("─" * w for w in widths), "faint")
    body = ["  ".join(fmt(cell, i) for i, cell in enumerate(r)).rstrip() for r in rows]
    return "\n".join(["  " + head.rstrip(), "  " + sep, *("  " + b for b in body)])


# ----------------------------------------------------------------------------
# Instruments
# ----------------------------------------------------------------------------
def meter(score: float, width: int = 20, pct: bool = True) -> str:
    """Instrument meter: signal fill on a muted track, mirrors the web console."""
    score = max(0.0, min(1.0, float(score)))
    filled = int(round(score * width))
    bar_ = c("━" * filled, "signal") + c("─" * (width - filled), "faint")
    return f"{bar_} {score:>4.0%}" if pct else bar_


def bar(score: float, width: int = 24) -> str:
    """Backwards-compatible alias for :func:`meter` without the percentage."""
    return meter(score, width, pct=False)


def scale(value: float, lo: float, hi: float, width: int = 32,
          refs: Mapping[str, float] | None = None) -> tuple[str, str]:
    """A labelled linear scale: returns (axis line, reference label line).

    The filled run and the value marker are signal-colored; reference positions
    are drawn as ┊ on the track with their names aligned underneath.
    """
    refs = refs or {}

    def col(v: float) -> int:
        frac = 0.0 if hi == lo else (v - lo) / (hi - lo)
        return max(0, min(width - 1, int(round(frac * (width - 1)))))

    pos = col(value)
    ref_cols = {col(v): name for name, v in refs.items()}
    cells = []
    for i in range(width):
        if i == pos:
            cells.append(c("●", "signal"))
        elif i < pos:
            cells.append(c("━", "signal"))
        elif i in ref_cols:
            cells.append(c("┊", "muted"))
        else:
            cells.append(c("─", "faint"))
    lo_s, hi_s = f"{lo:g}", f"{hi:g}"
    axis = f"{c(lo_s, 'muted')} {''.join(cells)} {c(hi_s, 'muted')}"

    under = [" "] * (width + len(lo_s) + 1 + 12)
    for i, name in sorted(ref_cols.items()):
        start = len(lo_s) + 1 + i - len(name) // 2
        start = max(len(lo_s) + 1, start)
        if all(ch == " " for ch in under[max(0, start - 1):start + len(name) + 1]):
            under[start:start + len(name)] = list(name)
    return axis, c("".join(under).rstrip(), "muted")


def confidence_word(score: float) -> str:
    if score >= 0.85:
        return "very high"
    if score >= 0.70:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def note(text: str) -> str:
    """A quiet, muted line (empty states, hints)."""
    return c(text, "muted")


def fault(text: str) -> str:
    """Error line: critical marker + label, never color alone."""
    return f"{c('■', 'critical')} {c('ERROR', 'critical', 'bold')}  {text}"


def dumps(obj: Any) -> str:
    """Canonical JSON for machine-readable output."""
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
