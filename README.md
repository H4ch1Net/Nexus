# Nexus

Local-first terminal toolkit for cryptography, OSINT, log analysis, and enumeration. Offline by default.

## Requirements
- Windows or Linux
- Python 3.11+ (3.12 recommended)

## Install

### PyPI (users)
Windows (PowerShell):
```powershell
py -m pip install --user pipx
py -m pipx ensurepath
pipx install nexus-tool
nexus --help
```

Linux:
```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install nexus-tool
nexus --help
```

Without pipx:
```bash
pip install --user nexus-tool
nexus --help
```

### GitHub (users)
```bash
pipx install "git+https://github.com/H4ch1Net/Nexus.git"
nexus --help
```

## Usage

Help:
```bash
nexus --help
```

OSINT metadata:
```bash
nexus osint meta -i /path/to/file.jpg
```

Log ingest and canned query:
```bash
nexus log ingest -i ./events.jsonl
nexus log canned total_requests
```

Cryptography heuristics:
```bash
nexus crypt detect -i /path/to/blob.bin
```

Language detection:
```bash
nexus enum code-id -i /path/to/sourcefile
```

If the command is not found:
```bash
python -m nexus.cli --help
```

## Configuration

Default path:
- Windows: `C:\Users\<user>\.nexus\config.toml`
- Linux: `/home/<user>/.nexus/config.toml`

Example (`config.toml`):
```toml
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
```

## Data locations
- Parquet datasets: `<data_dir>/parquet/<dataset-id>/`
- DuckDB catalog: `<data_dir>/duckdb/nexus.duckdb`
- Audit log (NDJSON): `<data_dir>/audit.log`

## Update / Uninstall

PyPI via pipx:
```bash
pipx reinstall nexus-tool
pipx uninstall nexus-tool
```

Editable install:
```bash
git pull
pip install -e .
```

## Troubleshooting

Python version error:
```text
Requires Python >= 3.11
```

Command not found:
```bash
python -m nexus.cli --help
```

PowerShell activation blocked:
```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

## License
See `LICENSE`.
