NEXUS
=====

Local-first terminal toolkit for cryptography, OSINT, log analysis, and enumeration.

REQUIREMENTS
------------
- Windows or Linux
- Python 3.11 or newer (3.12 recommended)
- Disk space for Parquet and DuckDB files

INSTALL
-------
Using pipx (recommended for users with Python):
  Windows (PowerShell):
    py -m pip install --user pipx
    py -m pipx ensurepath
    pipx install "git+https://github.com/H4ch1Net/Nexus.git"
    nexus --help

  Linux:
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    pipx install "git+https://github.com/H4ch1Net/Nexus.git"
    nexus --help

From source (contributors):
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

USAGE
-----
Show help:
  nexus --help

OSINT metadata:
  nexus osint meta -i <path/to/file>

Log ingest and canned query:
  nexus log ingest -i <events.jsonl>
  nexus log canned total_requests

Cryptography heuristics:
  nexus crypt detect -i <path/to/blob>

Language detection:
  nexus enum code-id -i <path/to/sourcefile>

If the command is not found:
  python -m nexus.cli --help

CONFIGURATION
-------------
Default config path:
  Windows:  C:\Users\<user>\.nexus\config.toml
  Linux:    /home/<user>/.nexus/config.toml

Example (config.toml):
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

DATA
----
- Parquet datasets: <data_dir>/parquet/<dataset-id>/
- DuckDB catalog:  <data_dir>/duckdb/nexus.duckdb
- Audit log (NDJSON): <data_dir>/audit.log

UPDATE / UNINSTALL
------------------
pipx:
  Update:    pipx reinstall "git+https://github.com/H4ch1Net/Nexus.git"
  Uninstall: pipx uninstall nexus

Editable install:
  Update:    git pull && pip install -e .
  Uninstall: remove the virtual environment

TROUBLESHOOTING
---------------
Python version error:
  Install Python 3.11+ and recreate the virtual environment.

Command not found:
  Ensure installation completed and your environment (pipx or venv) is active.

LICENSE
-------
See LICENSE in the repository.
