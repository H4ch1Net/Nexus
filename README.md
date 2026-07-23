# Nexus

A local-first terminal toolkit for cryptography analysis, OSINT, IOC/secrets triage, log analytics, and code enumeration. Runs entirely offline. No accounts, no telemetry. Every action is written to a local, tamper-evident audit log.

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

To also use the local web UI, install the `web` extra: `pipx install "nexus-tool[web]"` (or `pip install "nexus-tool[web]"`).

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

Encode/decode text (base64, base64url, base32, base85, hex, url, rot13/rot-N, binary):

```bash
nexus crypt encode -i "Hello World!" -t base64
nexus crypt decode -i "SGVsbG8gV29ybGQh" -t base64
nexus crypt encode -i "attack at dawn" -t rot --shift 7
```

Identify a hash's likely algorithm(s) by pattern/length:

```bash
nexus crypt hash-id -i "5f4dcc3b5aa765d61d8327deb882cf99"
```

XOR encode/decode, or brute-force a single-byte key (classic CTF technique):

```bash
nexus crypt xor -i "48656c6c6f" -k "X" --input-format hex --key-format text
nexus crypt xor -i "0b1a1a1a1e" --bruteforce --top 5
```

### IOC Extraction

Pull indicators of compromise (IPs, domains, URLs, emails, MD5/SHA1/SHA256, CVEs, BTC/ETH addresses, MAC addresses, Windows paths, registry keys) out of arbitrary text.

```bash
nexus ioc extract -i "$(cat incident_notes.txt)"
```

### Secrets Scanning

Scan text or code for exposed credentials (AWS/GitHub/GitLab/Slack/Google/Stripe/npm keys, private key headers, JWTs, generic API keys, basic-auth URLs) plus an entropy-based fallback for unrecognized high-entropy tokens. Matches are redacted in the output.

```bash
nexus secrets scan -i "$(cat .env)"
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

# List available canned queries and their parameters
nexus log queries

# Run a built-in query
nexus log canned total_requests
nexus log canned count_by_field --params '{"field": "status"}'
nexus log canned time_bucketed_counts --params '{"time_field": "ts", "bucket": "day"}'
nexus log canned distinct_values --params '{"field": "user"}'
```

### Enumeration

Identify the programming language of a code snippet (extension hint + content heuristics).

```bash
nexus enum code-id -i "def hello(): print('hi')"
nexus enum code-id -i "fn main() {}" -n main.rs
```

## Web UI

A local-only (127.0.0.1) web UI exposes every module above through the same service layer and audit trail as the CLI. Requires the `web` extra (`pip install nexus-tool[web]`).

```bash
nexus web serve
# -> Serving Nexus web UI on http://127.0.0.1:8765
```

The web UI has no authentication - only bind it beyond localhost if you understand the exposure (`nexus web serve --host --port`). It also includes an **audit trail viewer** (`/audit`) showing everything analyzed through either interface.

## Plugins

Nexus can load third-party plugins that register new CLI subcommands. Plugins live under `~/.nexus/plugins/` and must be explicitly trusted before they run.

```bash
nexus plugin list                    # discover plugins and their trust status
nexus plugin trust <path/to/plugin.py>   # pin a plugin's SHA256 hash as trusted
```

A plugin is a `.py` file exposing `NEXUS_PLUGIN = {"name", "version", "api_version": 1}` and a `register_cli(ctx)` function that can attach commands to any module group (`ctx.crypt_group`, `ctx.osint_group`, `ctx.log_group`, `ctx.enum_group`, `ctx.ioc_group`, `ctx.secrets_group`) or the root CLI (`ctx.cli`).

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
