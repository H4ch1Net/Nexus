from __future__ import annotations
import base64
import binascii
import urllib.parse

SCHEMES = ["base64", "base64url", "base32", "hex", "url", "rot13", "rot", "binary", "base85"]


class CodecError(ValueError):
    pass


def _rot_n(text: str, n: int) -> str:
    n = n % 26
    out = []
    for c in text:
        if 'a' <= c <= 'z':
            out.append(chr((ord(c) - 97 + n) % 26 + 97))
        elif 'A' <= c <= 'Z':
            out.append(chr((ord(c) - 65 + n) % 26 + 65))
        else:
            out.append(c)
    return ''.join(out)


def _binary_encode(data: bytes) -> str:
    return ' '.join(format(b, '08b') for b in data)


def _binary_decode(text: str) -> bytes:
    bits = text.split()
    try:
        return bytes(int(b, 2) for b in bits)
    except ValueError as e:
        raise CodecError(f"invalid binary string: {e}") from e


def _pad_b64(text: str) -> str:
    return text + "=" * (-len(text) % 4)


def encode(text: str, scheme: str, shift: int = 13) -> str:
    data = text.encode("utf-8")
    scheme = scheme.lower()
    if scheme == "base64":
        return base64.b64encode(data).decode()
    if scheme == "base64url":
        return base64.urlsafe_b64encode(data).decode()
    if scheme == "base32":
        return base64.b32encode(data).decode()
    if scheme == "hex":
        return data.hex()
    if scheme == "url":
        return urllib.parse.quote(text, safe="")
    if scheme == "rot13":
        return _rot_n(text, 13)
    if scheme == "rot":
        return _rot_n(text, shift)
    if scheme == "binary":
        return _binary_encode(data)
    if scheme == "base85":
        return base64.a85encode(data).decode()
    raise CodecError(f"unknown scheme: {scheme!r}; choose from {SCHEMES}")


def decode(text: str, scheme: str, shift: int = 13) -> str:
    scheme = scheme.lower()
    try:
        if scheme == "base64":
            data = base64.b64decode(_pad_b64(text.strip()))
        elif scheme == "base64url":
            data = base64.urlsafe_b64decode(_pad_b64(text.strip()))
        elif scheme == "base32":
            data = base64.b32decode(_pad_b64(text.strip().upper()))
        elif scheme == "hex":
            data = bytes.fromhex(text.strip().replace(" ", "").replace("\n", ""))
        elif scheme == "url":
            return urllib.parse.unquote(text)
        elif scheme == "rot13":
            return _rot_n(text, -13)
        elif scheme == "rot":
            return _rot_n(text, -shift)
        elif scheme == "binary":
            data = _binary_decode(text)
        elif scheme == "base85":
            data = base64.a85decode(text.strip())
        else:
            raise CodecError(f"unknown scheme: {scheme!r}; choose from {SCHEMES}")
    except (binascii.Error, ValueError) as e:
        raise CodecError(f"failed to decode as {scheme}: {e}") from e
    return data.decode("utf-8", errors="replace")
