# Nexus

Local-first terminal toolkit for cryptography, OSINT, log analysis, and enumeration.

## Requirements
- Windows or Linux
- Python 3.11+

## Install

### Arch (pipx)
```bash
sudo pacman -S --needed python-pipx
pipx ensurepath   # open a new shell after this
pipx install nexus-tool
nexus --help
```

### Kali (pipx)
```bash
sudo apt update && sudo apt install -y pipx
pipx ensurepath   # open a new shell after this
pipx install nexus-tool
nexus --help
```

### Windows (per-user pip)
```powershell
py -m pip install --user -U nexus-tool
nexus --help
```

## Usage

```bash
nexus --help
nexus osint meta -i /path/to/image.jpg
nexus log ingest -i ./events.jsonl
nexus log canned total_requests
nexus crypt detect -i /path/to/blob.bin
nexus enum code-id -i /path/to/sourcefile
```

## Update / Uninstall

Arch/Kali:
```bash
pipx upgrade nexus-tool
pipx uninstall nexus-tool
```

Windows:
```powershell
py -m pip install --user -U nexus-tool
py -m pip uninstall nexus-tool
```

## License
MIT
