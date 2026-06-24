# Nexus

A local-first terminal toolkit for cryptography analysis, OSINT, log analytics, and code enumeration. Runs entirely offline. No accounts, no telemetry.

## Requirements

- Python 3.11+
- Windows or Linux

## Install

**Arch**
```bash
sudo pacman -S --needed python-pipx
pipx ensurepath
pipx install nexus-tool
```

**Debian / Ubuntu / Kali**
```bash
sudo apt update && sudo apt install -y pipx
pipx ensurepath
pipx install nexus-tool
```

**Windows**
```powershell
py -m pip install --user -U nexus-tool
```

Open a new shell after `pipx ensurepath` to pick up the PATH change.

## Commands

### Cryptography

Detect encodings, classical ciphers, and modern encryption from an input string. Reports entropy, index of coincidence, and ranked candidates.

```bash
# Quick one-line answer (default)
nexus crypt detect -i "SGVsbG8gV29ybGQh"

# Full statistical breakdown
nexus crypt detect -i "SGVsbG8gV29ybGQh" --format detailed

# Compact table
nexus crypt detect -i "c2NyaWJibGU=" --format compact

# JSON output for scripting
nexus crypt detect -i "URYYB JBEYQ" --format json --top 5
```

### OSINT / Metadata

Extract EXIF and file metadata from images.

```bash
nexus osint meta -i /path/to/image.jpg
```

### Log Analysis

Ingest structured JSONL logs into a local DuckDB database and run analytics queries against them.

```bash
# Ingest a log file
nexus log ingest -i ./events.jsonl

# Run a built-in query
nexus log canned total_requests
```

### Enumeration

Identify the programming language of a code snippet.

```bash
nexus enum code-id -i "def hello(): print('hi')"
```

## Output Formats (crypt detect)

| Format | Description |
|--------|-------------|
| `simple` | Top match with confidence rating (default) |
| `detailed` | Full entropy, IC analysis, and ranked candidates |
| `compact` | Table view for quick scanning |
| `json` | Raw JSON for scripting and piping |

## Update / Uninstall

**Linux (pipx)**
```bash
pipx upgrade nexus-tool
pipx uninstall nexus-tool
```

**Windows**
```powershell
py -m pip install --user -U nexus-tool
py -m pip uninstall nexus-tool
```

## License

MIT
