Nexus
=====

Local-first terminal toolkit for cryptography, OSINT, log analysis, and enumeration.
Offline by default. Cross-platform: Windows and Linux.

----------------------------------------
REQUIREMENTS
----------------------------------------
- Python 3.11 or newer (3.12 recommended) for source installs
- Or a released binary (no Python required)
- Disk space for Parquet and DuckDB files

----------------------------------------
INSTALL FOR USERS (EASIEST FIRST)
----------------------------------------

A) GitHub + pipx (one command, no virtualenv juggling)
  Windows:
    py -m pip install --user pipx
    py -m pipx ensurepath
    pipx install "git+https://github.com/H4ch1Net/Nexus.git"
    nexus --help

  Linux:
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    pipx install "git+https://github.com/H4ch1Net/Nexus.git"
    nexus --help

  Update:
    pipx reinstall "git+https://github.com/H4ch1Net/Nexus.git"

  Uninstall:
    pipx uninstall nexus

B) Download a binary from GitHub Releases (if provided)
  Windows:
    1) Download nexus.exe from the latest Release
    2) Run: .\nexus.exe --help

  Linux:
    1) Download nexus from the latest Release
    2) chmod +x nexus && ./nexus --help

C) Docker (no Python on host; build locally)
  Build image:
    docker build -t nexus:local .
  Run help:
    docker run --rm nexus:local --help
  Process a local file (mount folder):
    docker run --rm -v "$PWD:/data" nexus:local osint meta -i /data/file.jpg

----------------------------------------
DEVELOPER INSTALL (CLONE + EDITABLE)
----------------------------------------

Windows (PowerShell):
  git clone https://github.com/H4ch1Net/Nexus.git
  cd Nexus
  py -3.12 -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  pip install -e .
  nexus --help

Linux:
  git clone https://github.com/H4ch1Net/Nexus.git
  cd Nexus
  python3.12 -m venv .venv
  source .venv/bin/activate
  python -m pip install --upgrade pip
  pip install -e .
  nexus --help

Optional convenience runners (repo root):
  Windows: create run.ps1
    $ErrorActionPreference="Stop"
    Set-Location $PSScriptRoot
    $py = (Get-Command py -ErrorAction SilentlyContinue) ? "py -3.12" : "python"
    if (!(Test-Path .\.venv\Scripts\python.exe)) { iex "$py -m venv .venv" }
    . .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip >$null
    pip install -e . >$null
    nexus $args

  Linux: create run.sh
    #!/usr/bin/env bash
    set -euo pipefail
    cd "$(dirname "$0")"
    python=${PYTHON:-python3.12}
    [ -f .venv/bin/python ] || $python -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip >/dev/null
    pip install -e . >/dev/null
    exec nexus "$@"

----------------------------------------
USAGE
----------------------------------------

General:
  nexus --help
  nexus --config <path/to/config.toml> <subcommand> ...

OSINT metadata:
  nexus osint meta -i <path/to/file>

Logs:
  # JSON Lines input
  nexus log ingest -i <events.jsonl>
  nexus log canned total_requests

Cryptography heuristics:
  nexus crypt detect -i <path/to/blob>

Language detection:
  nexus enum code-id -i <path/to/sourcefile>

If the command is not found:
  python -m nexus.cli --help

----------------------------------------
CONFIGURATION
----------------------------------------

Default path:
  Windows:  C:\Users\<user>\.nexus\config.toml
  Linux:    /home/<user>/.nexus/config.toml

Minimal example:
  [data]
  data_dir = "~/.nexus"
  plugins_dir = "~/.nexus/plugins"
  log_dir = "~/.nexus"
  audit_log = "~/.nexus/audit.log"

  [log]
  default_table_name = "events"

  [crypto]
  auto_decode_top = 3
  max_auto_decode_input_bytes = 32768

----------------------------------------
DATA LOCATIONS
----------------------------------------

- Parquet datasets: <data_dir>/parquet/<dataset-id>/
- DuckDB catalog:  <data_dir>/duckdb/nexus.duckdb
- Audit log (NDJSON): <data_dir>/audit.log

----------------------------------------
TROUBLESHOOTING
----------------------------------------

Python version error (needs >= 3.11):
  Install Python 3.12 and recreate the venv:
    Windows: py -3.12 -m venv .venv
    Linux:   python3.12 -m venv .venv

Permission denied recreating venv (Windows):
  deactivate
  Remove-Item -Recurse -Force .venv
  py -3.12 -m venv .venv

Command not found:
  Ensure install completed.
  Ensure venv is activated (dev install).
  Try: python -m nexus.cli --help

PowerShell execution policy blocks activation:
  Set-ExecutionPolicy -Scope Process Bypass

pipx not on PATH:
  Windows: py -m pipx ensurepath
  Linux:   python3 -m pipx ensurepath
  Restart the shell.

----------------------------------------
UPDATE / UNINSTALL
----------------------------------------

pipx install:
  Update:    pipx reinstall "git+https://github.com/H4ch1Net/Nexus.git"
  Uninstall: pipx uninstall nexus

Editable install:
  Update:    git pull && pip install -e .
  Uninstall: deactivate (if active) then remove .venv

----------------------------------------
LICENSE
----------------------------------------

See LICENSE in the repository.
