"""Tests for the cryptography module: detection, codecs, magic, hashing."""
import base64

import pytest

from nexus.modules.cryptography import codecs, hashing
from nexus.modules.cryptography.service import detect


def test_detect_base64():
    res = detect("SGVsbG8gV29ybGQh")
    names = [c["name"] for c in res["candidates"]]
    assert "base64" in names
    assert res["metrics"]["entropy"] > 0


def test_detect_base64url_not_triggered_by_plain_word():
    # Regression: an operator-precedence bug meant ANY text containing '_'
    # was flagged base64url regardless of its other characters. This string
    # has a space and '!' (outside the base64url charset), so it must not match.
    res = detect("hello world_!")
    assert "base64url" not in [c["name"] for c in res["candidates"]]


def test_detect_pem_armor():
    res = detect("-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----")
    assert any(c["category"] == "armor" for c in res["candidates"])


@pytest.mark.parametrize("codec,encoded,plain", [
    ("base64", base64.b64encode(b"Hello World!").decode(), "Hello World!"),
    ("base32", base64.b32encode(b"Hello").decode(), "Hello"),
    ("hex", b"Hello".hex(), "Hello"),
    ("rot13", "Uryyb", "Hello"),
    ("reverse", "olleH", "Hello"),
    ("binary", "01001000 01101001", "Hi"),
    ("decimal", "72 105", "Hi"),
    ("url", "a%20b%2Fc", "a b/c"),
])
def test_decode_roundtrip(codec, encoded, plain):
    assert codecs.decode(encoded, codec) == plain


def test_decode_base58():
    assert codecs.decode("StV1DL6CwTryKyV", "base58") == "hello world"


def test_decode_morse():
    assert codecs.decode(".... .. / - .... . .-. .", "morse") == "HI THERE"


def test_decode_caesar_and_xor():
    assert codecs.decode("Khoor", "caesar", shift=3) == "Hello"
    assert codecs.decode(codecs.xor("secret", "k"), "xor", key="k") == "secret"


def test_decode_invalid_raises():
    with pytest.raises(codecs.DecodeError):
        codecs.decode("not valid base64 !!!", "base64")
    with pytest.raises(codecs.DecodeError):
        codecs.decode("abc", "unknown_codec")


def test_magic_finds_single_step():
    results = codecs.magic("Uryyb Jbeyq")
    assert results, "expected at least one candidate"
    assert results[0].recipe == ["rot13"]
    assert "Hello" in results[0].output


def test_magic_finds_chain():
    payload = base64.b64encode("Uryyb".encode()).decode()  # base64(rot13("Hello"))
    results = codecs.magic(payload)
    recipes = ["->".join(r.recipe) for r in results]
    assert any(r.startswith("base64") for r in recipes)
    best = results[0]
    assert "Hello" in best.output or best.recipe[0] == "base64"


def test_hashes():
    h = hashing.compute_hashes(b"hello")
    assert h["md5"] == "5d41402abc4b2a76b9719d911017c592"
    assert h["sha256"].startswith("2cf24dba")
    assert len(h["crc32"]) == 8


def test_hash_file(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"hello")
    assert hashing.hash_file(f)["md5"] == "5d41402abc4b2a76b9719d911017c592"


def test_hash_id():
    assert hashing.identify_hash("5d41402abc4b2a76b9719d911017c592")[0]["name"] == "MD5"
    assert hashing.identify_hash("aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d")[0]["name"] == "SHA-1"
    assert hashing.identify_hash("$2b$12$" + "a" * 53)[0]["name"] == "bcrypt"
    assert hashing.identify_hash("not-a-hash") == []
