from __future__ import annotations
from nexus.modules.cryptography.service import _entropy, _printable_ratio


class XorError(ValueError):
    pass


def _parse_bytes(text: str, fmt: str) -> bytes:
    fmt = fmt.lower()
    if fmt == "hex":
        try:
            return bytes.fromhex(text.strip().replace(" ", "").replace("\n", ""))
        except ValueError as e:
            raise XorError(f"invalid hex input: {e}") from e
    if fmt == "text":
        return text.encode("utf-8")
    raise XorError(f"unknown format: {fmt!r}; choose 'hex' or 'text'")


def xor_bytes(data: bytes, key: bytes) -> bytes:
    if not key:
        raise XorError("key must not be empty")
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def apply(input_text: str, key_text: str, input_format: str = "hex", key_format: str = "text") -> dict:
    """XOR is its own inverse, so this serves as both encode and decode."""
    data = _parse_bytes(input_text, input_format)
    key = _parse_bytes(key_text, key_format)
    out = xor_bytes(data, key)
    return {
        "output_hex": out.hex(),
        "output_text": out.decode("utf-8", errors="replace"),
        "length": len(out),
    }


def bruteforce(input_text: str, input_format: str = "hex", top: int = 5) -> dict:
    """Single-byte XOR key brute force, ranked by printable ratio then entropy
    (classic CTF technique for short XOR'd ciphertext)."""
    data = _parse_bytes(input_text, input_format)
    if not data:
        raise XorError("input is empty")

    results = []
    for k in range(256):
        out = xor_bytes(data, bytes([k]))
        pr = _printable_ratio(out)
        ent = _entropy(out)
        results.append({
            "key": k,
            "key_hex": f"{k:02x}",
            "key_char": chr(k) if 32 <= k < 127 else None,
            "printable_ratio": round(pr, 4),
            "entropy": round(ent, 4),
            "preview": out[:120].decode("utf-8", errors="replace"),
        })

    results.sort(key=lambda r: (r["printable_ratio"], -r["entropy"]), reverse=True)
    top = max(1, min(top, 256))
    return {"input_length": len(data), "candidates": results[:top]}
