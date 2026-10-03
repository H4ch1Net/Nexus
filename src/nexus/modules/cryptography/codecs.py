"""Reversible decoders and a recursive auto-decode ("magic") engine.

Every decoder maps a string to a decoded string and raises ``DecodeError`` when
the input does not fit that codec. ``magic`` chains decoders breadth-first and
scores each result for readability, which is the fast path for CTF-style
"what is this and how do I read it" questions.
"""
from __future__ import annotations

import base64
import binascii
import codecs as _codecs
import html
import math
import quopri
import re
import string
import urllib.parse
from collections import Counter
from typing import Callable, Dict, List, NamedTuple

PRINTABLE = set(bytes(string.printable, "ascii"))

MORSE_MAP = {
    ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E", "..-.": "F",
    "--.": "G", "....": "H", "..": "I", ".---": "J", "-.-": "K", ".-..": "L",
    "--": "M", "-.": "N", "---": "O", ".--.": "P", "--.-": "Q", ".-.": "R",
    "...": "S", "-": "T", "..-": "U", "...-": "V", ".--": "W", "-..-": "X",
    "-.--": "Y", "--..": "Z", "-----": "0", ".----": "1", "..---": "2",
    "...--": "3", "....-": "4", ".....": "5", "-....": "6", "--...": "7",
    "---..": "8", "----.": "9", ".-.-.-": ".", "--..--": ",", "..--..": "?",
    "-..-.": "/", "-....-": "-", "-.--.": "(", "-.--.-": ")",
}

_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


class DecodeError(ValueError):
    """Raised when an input cannot be decoded by a given codec."""


def _bytes_to_text(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


# ----------------------------------------------------------------------------
# Individual decoders
# ----------------------------------------------------------------------------
def from_base64(s: str) -> str:
    t = re.sub(r"\s+", "", s)
    t = t.replace("-", "+").replace("_", "/")
    if len(t) < 4 or len(t) % 4 != 0:
        raise DecodeError("base64: length must be a multiple of 4")
    try:
        return _bytes_to_text(base64.b64decode(t, validate=True))
    except (binascii.Error, ValueError) as e:
        raise DecodeError(f"base64: {e}") from e


def from_base32(s: str) -> str:
    t = re.sub(r"\s+", "", s).upper()
    if len(t) < 8 or len(t) % 8 != 0:
        raise DecodeError("base32: length must be a multiple of 8")
    try:
        return _bytes_to_text(base64.b32decode(t))
    except (binascii.Error, ValueError) as e:
        raise DecodeError(f"base32: {e}") from e


def from_hex(s: str) -> str:
    t = re.sub(r"(?i)\s+|0x|\\x|:", "", s)
    if len(t) < 2 or len(t) % 2 != 0 or not all(ch in string.hexdigits for ch in t):
        raise DecodeError("hex: expected an even number of hex digits")
    return _bytes_to_text(binascii.unhexlify(t))


def from_base58(s: str) -> str:
    t = s.strip()
    if not t or any(ch not in _B58_ALPHABET for ch in t):
        raise DecodeError("base58: invalid character")
    num = 0
    for ch in t:
        num = num * 58 + _B58_ALPHABET.index(ch)
    raw = num.to_bytes((num.bit_length() + 7) // 8, "big") if num else b""
    pad = len(t) - len(t.lstrip("1"))
    return _bytes_to_text(b"\x00" * pad + raw)


def from_ascii85(s: str) -> str:
    t = re.sub(r"\s+", "", s)
    try:
        return _bytes_to_text(base64.a85decode(t))
    except (ValueError, binascii.Error) as e:
        raise DecodeError(f"ascii85: {e}") from e


def from_base85(s: str) -> str:
    t = re.sub(r"\s+", "", s)
    try:
        return _bytes_to_text(base64.b85decode(t))
    except (ValueError, binascii.Error) as e:
        raise DecodeError(f"base85: {e}") from e


def from_url(s: str) -> str:
    if "%" not in s and "+" not in s:
        raise DecodeError("url: no percent-encoded sequences")
    return urllib.parse.unquote_plus(s)


def from_html(s: str) -> str:
    if "&" not in s or ";" not in s:
        raise DecodeError("html: no entities present")
    out = html.unescape(s)
    if out == s:
        raise DecodeError("html: nothing to unescape")
    return out


def from_quoted_printable(s: str) -> str:
    if not re.search(r"=[0-9A-Fa-f]{2}", s):
        raise DecodeError("quoted-printable: no =XX sequences")
    return _bytes_to_text(quopri.decodestring(s.encode("utf-8", "ignore")))


def rot13(s: str) -> str:
    return _codecs.encode(s, "rot_13")


def rot47(s: str) -> str:
    out = []
    for ch in s:
        o = ord(ch)
        if 33 <= o <= 126:
            out.append(chr(33 + (o - 33 + 47) % 94))
        else:
            out.append(ch)
    return "".join(out)


def atbash(s: str) -> str:
    out = []
    for ch in s:
        if ch.isupper():
            out.append(chr(ord("Z") - (ord(ch) - ord("A"))))
        elif ch.islower():
            out.append(chr(ord("z") - (ord(ch) - ord("a"))))
        else:
            out.append(ch)
    return "".join(out)


def reverse(s: str) -> str:
    return s[::-1]


def caesar(s: str, shift: int) -> str:
    out = []
    for ch in s:
        if ch.isupper():
            out.append(chr((ord(ch) - ord("A") + shift) % 26 + ord("A")))
        elif ch.islower():
            out.append(chr((ord(ch) - ord("a") + shift) % 26 + ord("a")))
        else:
            out.append(ch)
    return "".join(out)


def from_binary(s: str) -> str:
    bits = re.sub(r"[^01]", "", s)
    if len(bits) < 8 or len(bits) % 8 != 0:
        raise DecodeError("binary: expected groups of 8 bits")
    raw = bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))
    return _bytes_to_text(raw)


def from_decimal(s: str) -> str:
    parts = re.split(r"[\s,]+", s.strip())
    if not parts or not all(p.isdigit() for p in parts if p):
        raise DecodeError("decimal: expected space/comma separated byte values")
    vals = [int(p) for p in parts if p]
    if any(v > 255 for v in vals):
        raise DecodeError("decimal: value out of byte range")
    return _bytes_to_text(bytes(vals))


def from_morse(s: str) -> str:
    cleaned = s.strip().replace("|", "/")
    if not re.fullmatch(r"[.\-/ \n]+", cleaned):
        raise DecodeError("morse: unexpected characters")
    words = re.split(r"\s*/\s*|\n", cleaned)
    out_words = []
    for word in words:
        letters = [MORSE_MAP.get(tok, "?") for tok in word.split() if tok]
        if letters:
            out_words.append("".join(letters))
    text = " ".join(out_words)
    if not text or "?" * 3 in text:
        raise DecodeError("morse: no recognizable letters")
    return text


# Codecs safe to try automatically (no parameters, deterministic).
_AUTO: Dict[str, Callable[[str], str]] = {
    "base64": from_base64,
    "base32": from_base32,
    "hex": from_hex,
    "base58": from_base58,
    "ascii85": from_ascii85,
    "base85": from_base85,
    "url": from_url,
    "html": from_html,
    "quoted_printable": from_quoted_printable,
    "rot13": rot13,
    "rot47": rot47,
    "atbash": atbash,
    "binary": from_binary,
    "decimal": from_decimal,
    "morse": from_morse,
    "reverse": reverse,
}

# Everything callable from the `decode` command, including parameterized codecs.
CODECS = dict(_AUTO)


def list_codecs() -> List[str]:
    return sorted(CODECS) + ["caesar", "xor"]


def decode(text: str, codec: str, *, shift: int = 3, key: str = "") -> str:
    """Decode ``text`` with a single named codec."""
    codec = codec.lower()
    if codec == "caesar":
        return caesar(text, -shift if shift >= 0 else shift)
    if codec == "xor":
        return xor(text, key)
    if codec not in CODECS:
        raise DecodeError(f"unknown codec: {codec}")
    return CODECS[codec](text)


def xor(text: str, key: str) -> str:
    """XOR a (possibly hex) payload against a repeating key."""
    if not key:
        raise DecodeError("xor: a key is required")
    try:
        data = binascii.unhexlify(re.sub(r"\s+", "", text)) if re.fullmatch(
            r"(?i)[0-9a-f\s]+", text
        ) and len(re.sub(r"\s+", "", text)) % 2 == 0 else text.encode("utf-8", "ignore")
    except binascii.Error:
        data = text.encode("utf-8", "ignore")
    kb = key.encode("utf-8")
    return _bytes_to_text(bytes(b ^ kb[i % len(kb)] for i, b in enumerate(data)))


# ----------------------------------------------------------------------------
# Readability scoring + recursive magic
# ----------------------------------------------------------------------------
_COMMON_WORDS = {
    "the", "and", "for", "that", "this", "with", "you", "flag", "key", "secret",
    "password", "http", "https", "www", "true", "false", "hello", "world",
}


def text_score(s: str) -> float:
    """Heuristic 0..1 readability score for decoded text."""
    if not s:
        return 0.0
    raw = s.encode("utf-8", "ignore")
    printable = sum(1 for b in raw if b in PRINTABLE) / len(raw)
    score = printable * 0.6
    letters = sum(ch.isalpha() or ch.isspace() for ch in s) / len(s)
    score += letters * 0.25
    lowered = s.lower()
    if any(w in lowered for w in _COMMON_WORDS):
        score += 0.2
    if re.search(r"(?i)(flag|ctf|key)\{", lowered):
        score = max(score, 0.98)
    # Penalize replacement/control noise.
    control = sum(1 for b in raw if b < 9 or (13 < b < 32)) / len(raw)
    score -= control * 0.8
    return max(0.0, min(1.0, score))


class MagicResult(NamedTuple):
    recipe: List[str]
    output: str
    score: float


def magic(text: str, *, depth: int = 3, limit: int = 6) -> List[MagicResult]:
    """Breadth-first search over auto codecs, ranked by output readability."""
    seen = {text}
    results: List[MagicResult] = []
    frontier = [([], text)]

    for _ in range(max(1, depth)):
        next_frontier = []
        for recipe, current in frontier:
            for name, fn in _AUTO.items():
                # Avoid trivially self-inverse loops.
                if recipe and recipe[-1] == name and name in {"rot13", "atbash", "reverse"}:
                    continue
                try:
                    out = fn(current)
                except DecodeError:
                    continue
                except Exception:
                    continue
                if not out or out in seen:
                    continue
                seen.add(out)
                new_recipe = recipe + [name]
                results.append(MagicResult(new_recipe, out, text_score(out)))
                next_frontier.append((new_recipe, out))
        frontier = sorted(
            next_frontier, key=lambda rc: text_score(rc[1]), reverse=True
        )[:8]
        if not frontier:
            break

    results.sort(key=lambda r: (r.score, -len(r.recipe)), reverse=True)
    # De-duplicate by output, keeping the best/shortest recipe.
    unique: List[MagicResult] = []
    taken = set()
    for r in results:
        if r.output in taken:
            continue
        taken.add(r.output)
        unique.append(r)
    return unique[:limit]
