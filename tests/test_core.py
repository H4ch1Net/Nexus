"""Tests for core config, audit, and render helpers."""
import json

from nexus.core import render
from nexus.core.audit import audit


def test_config_creates_dirs(cfg):
    assert cfg.data_dir.exists()
    assert cfg.default_table == "events"


def test_audit_appends_line(cfg):
    audit(cfg, module="t", action="a", target="x", success_bool=True, notes="n")
    audit(cfg, module="t", action="b", target="y", success_bool=False)
    lines = cfg.audit_log.read_text().strip().splitlines()
    assert len(lines) == 2
    rec = json.loads(lines[0])
    assert rec["module"] == "t" and rec["action"] == "a"
    assert "timestamp_utc" in rec and "result_id" in rec


def test_render_bar_and_table(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert "█" in render.bar(1.0)
    out = render.table(["a", "b"], [[1, 2], [3, 4]])
    assert "a" in out and "3" in out
    assert render.dumps({"x": 1}) == '{\n  "x": 1\n}'
