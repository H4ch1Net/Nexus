# Nexus

Local-first terminal toolkit for cryptography, OSINT, log analysis, and enumeration.

## Requirements
- Windows or Linux
- Python 3.11 or newer (3.12 recommended)

## Install

### Users (pipx)
Windows (PowerShell):
```powershell
py -m pip install --user pipx
py -m pipx ensurepath
pipx install "git+https://github.com/H4ch1Net/Nexus.git"
nexus --help
```

Linux:
```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install "git+https://github.com/H4ch1Net/Nexus.git"
nexus --help
```

### Contributors (source)
Windows (PowerShell):
```powershell
git clone https://github.com/H4ch1Net/Nexus.git
cd Nexus
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
nexus --help
```

Linux:
```bash
git clone https://github.com/H4ch1Net/Nexus.git
cd Nexus
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
nexus --help
```

## Quickstart

Show help:
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

Default config path:
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

## Data

- Parquet datasets: `<data_dir>/parquet/<dataset-id>/`
- DuckDB catalog: `<data_dir>/duckdb/nexus.duckdb`
- Audit log (NDJSON): `<data_dir>/audit.log`

## Update / Uninstall

pipx:
```bash
# update
pipx reinstall "git+https://github.com/H4ch1Net/Nexus.git"
# uninstall
pipx uninstall nexus
```

Editable install:
```bash
# update after pulling changes
pip install -e .
# remove venv when done
# Windows (PowerShell)
Remove-Item -Recurse -Force .venv
# Linux
rm -rf .venv
```

## Troubleshooting

Python version error:
```text
ERROR: Package 'nexus' requires a different Python: 3.10.x not in '>=3.11'
```
Create the venv with Python 3.11+.

Command not found:
```bash
python -m nexus.cli --help
```

PowerShell activation blocked:
```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

pipx not on PATH:
```powershell
# Windows
py -m pipx ensurepath
```
```bash
# Linux
python3 -m pipx ensurepath
```

## License

See `LICENSE`.
