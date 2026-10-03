"""Tests for the OSINT module."""
from nexus.modules.osint.iocs import analyze_file, defang, find_iocs, refang


def test_find_iocs():
    text = "visit https://bad.example.com, ip 10.0.0.5, mail a@b.com, md5 5d41402abc4b2a76b9719d911017c592"
    iocs = find_iocs(text)
    assert "https://bad.example.com" in iocs["url"]
    assert "10.0.0.5" in iocs["ipv4"]
    assert "a@b.com" in iocs["email"]
    assert "5d41402abc4b2a76b9719d911017c592" in iocs["md5"]


def test_defang_refang_roundtrip():
    original = "http://evil.example.com/path and 8.8.8.8 and user@test.org"
    fanged = defang(original)
    assert "hxxp" in fanged and "[.]" in fanged and "[@]" in fanged
    assert refang(fanged) == original


def test_analyze_file(tmp_path):
    f = tmp_path / "blob.bin"
    f.write_bytes(b"\x00\x01junk https://x.example.org more\x00 1.2.3.4 ")
    res = analyze_file(f)
    assert res["ioc_total"] >= 2
    assert "url" in res["iocs"]


def test_extract_meta_hashes(tmp_path):
    from PIL import Image
    from nexus.modules.osint.service import extract_meta
    img = tmp_path / "pic.jpg"
    Image.new("RGB", (8, 8), (10, 20, 30)).save(img, "JPEG")
    res = extract_meta(str(img))
    assert res["file_mime"] == "image/jpeg"
    assert len(res["hashes"]["sha256"]) == 64
    assert res["gps"] is None  # no EXIF GPS in a freshly created image


def test_extract_meta_missing_file():
    from nexus.modules.osint.service import extract_meta
    assert extract_meta("/nope/does/not/exist.jpg") == {}
