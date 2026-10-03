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


def test_render_meter_and_table(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert render.meter(1.0, 10) == "━" * 10 + " 100%"
    assert render.meter(0.5, 10, pct=False) == "━" * 5 + "─" * 5
    out = render.table(["a", "b"], [[1, 2], [3, 4]])
    assert "A" in out and "3" in out
    assert render.dumps({"x": 1}) == '{\n  "x": 1\n}'


def test_table_aligns_colored_cells(monkeypatch):
    monkeypatch.setenv("NEXUS_FORCE_COLOR", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    out = render.table(["name", "x"], [[render.c("ab", "signal"), "1"], ["abcd", "2"]])
    lines = [render._ANSI.sub("", l) for l in out.splitlines()]
    assert lines[2].index("1") == lines[3].index("2")


def test_scale_marks_value_and_refs(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    axis, refs = render.scale(0.5, 0, 1, width=11, refs={"mid": 0.8})
    assert axis.startswith("0 ") and axis.endswith(" 1")
    assert "●" in axis and "┊" in axis
    assert "mid" in refs


def test_lockup_has_three_lines(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    lines = render.lockup(["a", "b", "c"]).splitlines()
    assert len(lines) == 3 and lines[0].startswith("█▄")
