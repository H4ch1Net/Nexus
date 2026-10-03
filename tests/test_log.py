"""Tests for the log-analysis module."""
from nexus.modules.log_analysis.service import (
    dataset_info,
    ingest,
    run_canned,
    run_query,
)


def _seed(cfg):
    log_file = cfg.data_dir / "events.jsonl"
    log_file.write_text(
        '{"method":"GET","path":"/","status":200,"level":"info"}\n'
        '{"method":"POST","path":"/login","status":500,"level":"error"}\n'
        '{"method":"GET","path":"/","status":200,"level":"info"}\n'
    )
    return ingest(cfg, log_file)


def test_ingest(cfg):
    res = _seed(cfg)
    assert res["rows"] == 3
    assert res["table"] == "events"
    assert "status" in res["columns"]


def test_canned_total_and_status(cfg):
    _seed(cfg)
    assert run_canned(cfg, "total_requests", {})["result"] == [{"total": 3}]
    codes = {r["status"]: r["count"] for r in run_canned(cfg, "status_codes", {})["result"]}
    assert codes[200] == 2


def test_canned_top_values(cfg):
    _seed(cfg)
    res = run_canned(cfg, "top_values", {"field": "path", "limit": 5})
    assert res["result"][0] == {"value": "/", "count": 2}


def test_canned_unknown(cfg):
    assert "error" in run_canned(cfg, "nope", {})


def test_query_select(cfg):
    _seed(cfg)
    res = run_query(cfg, "SELECT COUNT(*) AS n FROM events")
    assert res["result"] == [{"n": 3}]


def test_query_blocks_writes(cfg):
    _seed(cfg)
    assert "error" in run_query(cfg, "DROP TABLE events")
    assert "error" in run_query(cfg, "SELECT 1; DELETE FROM events")
    assert "error" in run_query(cfg, "UPDATE events SET status = 0")


def test_dataset_info(cfg):
    _seed(cfg)
    info = dataset_info(cfg)
    assert info["active_table"]["row_count"] == 3
    assert len(info["datasets"]) == 1
