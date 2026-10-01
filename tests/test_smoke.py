"""Smoke tests covering the core detection paths of each module."""
from pathlib import Path

from nexus.modules.cryptography.service import detect
from nexus.modules.enumeration.service import detect_language, detect_language_file
from nexus.modules.log_analysis.service import ingest, run_canned
from nexus.core.config import load_config


def test_crypt_detect_base64():
    res = detect("SGVsbG8gV29ybGQh")
    names = [c["name"] for c in res["candidates"]]
    assert "base64" in names
    assert res["metrics"]["entropy"] > 0


def test_enum_code_id_python_snippet():
    res = detect_language("def hello():\n    print('hi')\nimport os")
    assert res["candidates"][0]["language"] == "Python"
    assert res["candidates"][0]["confidence"] > 0.5


def test_enum_code_id_javascript_snippet():
    res = detect_language("const x = () => { console.log('hi'); }")
    assert res["candidates"][0]["language"] == "JavaScript"


def test_enum_code_id_unknown():
    res = detect_language("!!!???")
    assert res["candidates"][0]["language"] == "Unknown"


def test_enum_detect_language_file(tmp_path: Path):
    f = tmp_path / "snippet.py"
    f.write_text("import sys\n\ndef main():\n    print(sys.argv)\n")
    res = detect_language_file(f)
    assert res["candidates"][0]["language"] == "Python"


def test_log_ingest_and_canned(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(str(tmp_path / "config.toml"))

    log_file = tmp_path / "events.jsonl"
    log_file.write_text('{"a": 1}\n{"a": 2}\n{"a": 3}\n')

    res = ingest(cfg, log_file)
    assert res["rows"] == 3
    assert res["table"] == "events"

    out = run_canned(cfg, "total_requests", {})
    assert out["result"] == [{"total": 3}]


def test_log_canned_unknown(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config(str(tmp_path / "config.toml"))
    out = run_canned(cfg, "does_not_exist", {})
    assert "error" in out
