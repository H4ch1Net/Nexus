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
