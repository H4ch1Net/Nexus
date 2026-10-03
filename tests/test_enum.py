"""Tests for the enumeration module."""
from nexus.modules.enumeration.ports import resolve
from nexus.modules.enumeration.service import detect_language, detect_language_file


def test_code_id_python():
    res = detect_language("def hello():\n    print('hi')\nimport os")
    assert res["candidates"][0]["language"] == "Python"
    assert res["candidates"][0]["confidence"] > 0.5


def test_code_id_prefers_python_over_ruby_on_colon_def():
    # Regression: the old max-weight normalization favored Ruby here.
    res = detect_language("def x(): pass")
    assert res["candidates"][0]["language"] == "Python"


def test_code_id_javascript():
    res = detect_language("const x = () => { console.log('hi'); }")
    assert res["candidates"][0]["language"] == "JavaScript"


def test_code_id_unknown():
    assert detect_language("!!!???")["candidates"][0]["language"] == "Unknown"


def test_file_id(tmp_path):
    f = tmp_path / "snippet.py"
    f.write_text("import sys\n\ndef main():\n    print(sys.argv)\n")
    assert detect_language_file(f)["candidates"][0]["language"] == "Python"


def test_ports_by_number():
    res = resolve("443")
    assert res["kind"] == "port"
    assert res["matches"][0]["service"] == "https"


def test_ports_by_service():
    res = resolve("smb")
    assert res["kind"] == "service"
    assert any(m["port"] == 445 for m in res["matches"])


def test_ports_unknown():
    assert resolve("65000")["matches"] == []
