"""End-to-end CLI tests via Click's runner."""
import json

from click.testing import CliRunner

from nexus.cli import cli


def _run(args):
    return CliRunner().invoke(cli, args, catch_exceptions=False)


def test_version():
    out = _run(["--version"])
    assert out.exit_code == 0
    assert "0.2.0" in out.output


def test_crypt_detect_json():
    out = _run(["crypt", "detect", "-i", "SGVsbG8=", "-f", "json"])
    assert out.exit_code == 0
    assert "base64" in [c["name"] for c in json.loads(out.output)["candidates"]]


def test_crypt_decode_auto():
    out = _run(["crypt", "decode", "-i", "Uryyb Jbeyq", "-c", "auto", "--json"])
    data = json.loads(out.output)
    assert data["candidates"][0]["recipe"] == ["rot13"]


def test_crypt_hash_id():
    out = _run(["crypt", "hash-id", "-i", "5d41402abc4b2a76b9719d911017c592", "--json"])
    assert json.loads(out.output)["candidates"][0]["name"] == "MD5"


def test_enum_ports():
    out = _run(["enum", "ports", "443", "--json"])
    assert json.loads(out.output)["matches"][0]["service"] == "https"


def test_osint_defang():
    out = _run(["osint", "defang", "-i", "http://x.com"])
    assert out.output.strip() == "hxxp[://]x[.]com"


def test_log_ingest_and_query(cfg):
    log_file = cfg.data_dir / "e.jsonl"
    log_file.write_text('{"a":1}\n{"a":2}\n')
    cfg_path = str((cfg.data_dir.parent / "config.toml"))
    res = _run(["--config", cfg_path, "log", "ingest", "-i", str(log_file), "--json"])
    assert json.loads(res.output)["rows"] == 2
    q = _run(["--config", cfg_path, "log", "query", "SELECT COUNT(*) n FROM events", "--json"])
    assert json.loads(q.output)["result"] == [{"n": 2}]
