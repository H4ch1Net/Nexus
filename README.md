````markdown
# Nexus

Local-first terminal toolkit for cryptography, OSINT, log analysis, and enumeration. CLI and TUI planned. Offline by default.

---

## Requirements

- Python 3.11 or newer (3.12 recommended)
- Windows or Linux
- Disk space for Parquet and DuckDB files

---

## Install (users)

### Option A: pipx (recommended)

Windows:
```powershell
py -m pip install --user pipx
py -m pipx ensurepath
pipx install "git+https://github.com/H4ch1Net/Nexus.git"
nexus --help
````

Linux:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install "git+https://github.com/H4ch1Net/Nexus.git"
nexus --help
```

Update:

```bash
pipx reinstall "git+https://github.com/H4ch1Net/Nexus.git"
```

Uninstall:

```bash
pipx uninstall nexus
```

---

## Install (contributors)

### Windows (PowerShell)

```powershell
git clone https://github.com/H4ch1Net/Nexus.git
cd Nexus
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
nexus --help
```

### Linux

```bash
git clone https://github.com/H4ch1Net/Nexus.git
cd Nexus
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
nexus --help
```

---

## Quick use

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
# create a tiny JSONL file (Linux)
printf '{"a":1}\n{"a":2}\n' > events.jsonl

nexus log ingest -i ./events.jsonl
nexus log canned total_requests
```

Crypto detect:

```bash
nexus crypt detect -i /path/to/blob.bin
```

Language detect:

```bash
nexus enum code-id -i /path/to/file.py
```

If `nexus` is not found:

```bash
python -m nexus.cli --help
```

---

## Self-bootstrapping runners (optional)

Add `run.ps1` (Windows) at repo root:

```powershell
# run.ps1
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$py = (Get-Command py -ErrorAction SilentlyContinue) ? "py -3.12" : "python"
if (!(Test-Path .\.venv\Scripts\python.exe)) { iex "$py -m venv .venv" }
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip >$null
pip install -e . >$null
nexus $args
```

Add `run.sh` (Linux) at repo root:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python=${PYTHON:-python3.12}
[ -f .venv/bin/python ] || $python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
pip install -e . >/dev/null
exec nexus "$@"
```

Use:

```powershell
# Windows
.\run.ps1 osint meta -i C:\path\file.jpg
```

```bash
# Linux
chmod +x run.sh
./run.sh osint meta -i /path/file.jpg
```

---

## Commands

General:

* `nexus --help`
* `nexus --config <path/to/config.toml> <subcommand> ...`

OSINT:

* `nexus osint meta -i <path>`
  Output: file size, MIME, MD5/SHA1/SHA256, placeholders for metadata and GPS.

Logs:

* `nexus log ingest -i <events.jsonl>`
  Reads JSON Lines. Writes Parquet dataset. Registers a DuckDB view.
* `nexus log canned total_requests`
  Returns `{result, sql, evidence, confidence}`.

Cryptography:

* `nexus crypt detect -i <blob>`
  Heuristics: entropy, printable ratio, magic headers (PDF/ZIP/GZIP), base encodings hints.

Enumeration:

* `nexus enum code-id -i <file>`
  Detects language using extension and shebang.

Exit codes:

* `0` success
* `1` general error
* `2` bad input or missing file
* `3` no result
* `10` external provider not configured

---

## Configuration

Default path:

* Windows: `C:\Users\<you>\.nexus\config.toml`
* Linux: `/home/<you>/.nexus/config.toml`

Sample:

```toml
[data]
data_dir = "~/.nexus"
plugins_dir = "~/.nexus/plugins"
log_dir = "~/.nexus"
audit_log = "~/.nexus/audit.log"

[log]
default_table_name = "events"
ingest_chunk_size_rows = 200000

[crypto]
auto_decode_top = 3
max_auto_decode_input_bytes = 32768
```

Override config path with `--config`.

---

## Data locations

* Parquet datasets: `<data_dir>/parquet/<dataset-id>/`
* DuckDB catalog: `<data_dir>/duckdb/nexus.duckdb`
* Audit log (NDJSON lines): `<data_dir>/audit.log`

---

## Security

* Offline by default.
* Providers disabled unless configured.
* Plugins loaded from allowlisted paths only (policy to follow).
* Audit log records module, action, time, and notes.

---

## Troubleshooting

Python version error:

```
ERROR: Package 'nexus' requires a different Python: 3.10.x not in '>=3.11'
```

Fix: install Python 3.11+ and create the venv with that version.

* Windows: `py -3.12 -m venv .venv`
* Linux: `python3.12 -m venv .venv`

Permission denied recreating venv (Windows):

```
Permission denied: '.venv\Scripts\python.exe'
```

Fix: deactivate first, then remove and recreate.

```powershell
deactivate
Remove-Item -Recurse -Force .venv
py -3.12 -m venv .venv
```

`nexus` not recognized:

* Use `python -m nexus.cli --help`.
* Ensure venv is activated.
* Ensure install succeeded.

PowerShell script blocked:

```
. .\Scripts\Activate.ps1 is not digitally signed
```

Fix:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

pipx not found:

* Windows: `py -m pip install --user pipx` then `py -m pipx ensurepath`
* Linux: `python3 -m pip install --user pipx` then `python3 -m pipx ensurepath`
* Restart the shell.

---

## Updating

pipx:

```bash
pipx reinstall "git+https://github.com/H4ch1Net/Nexus.git"
```

Editable install:

```bash
git pull
pip install -e .
```

---

## Uninstall

pipx:

```bash
pipx uninstall nexus
```

Editable install:

```bash
deactivate  # if active
rm -rf .venv  # or Remove-Item -Recurse -Force .venv on Windows
```

---

## License

See `LICENSE`.

```
```
