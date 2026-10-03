"""Shared pytest fixtures."""
import textwrap
from pathlib import Path

import pytest

from nexus.core.config import load_config


@pytest.fixture()
def cfg(tmp_path: Path):
    """A Config whose data/audit paths live under a temp directory."""
    data = tmp_path / "data"
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(textwrap.dedent(f"""
        [data]
        data_dir = "{data.as_posix()}"
        log_dir = "{data.as_posix()}"
        audit_log = "{(data / 'audit.log').as_posix()}"
    """))
    return load_config(str(cfg_file))
