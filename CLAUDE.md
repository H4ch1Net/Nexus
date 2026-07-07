# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Nexus (`nexus-tool` on PyPI) is a local-first, offline terminal toolkit exposing four security-analysis domains through a single `nexus` CLI: cryptography detection, OSINT/metadata extraction, log analytics, and code enumeration. It runs entirely offline — no network calls, no accounts, no telemetry.

## Commands

```bash
# Install for local development (editable)
pip install -e .

# Run the CLI (entry point is nexus.cli:cli, defined in pyproject.toml)
nexus --help
python -m nexus.cli --help          # equivalent when not installed

# The four command groups
nexus crypt detect -i "SGVsbG8gV29ybGQh" [--format simple|detailed|compact|json] [--top N]
nexus osint meta   -i /path/to/image.jpg
nexus log ingest   -i ./events.jsonl
nexus log canned   total_requests [--params '{}']
nexus enum code-id -i "def hello(): print('hi')"

# Override the config file location (default ~/.nexus/config.toml)
nexus --config ./my.toml crypt detect -i "..."
```

There is **no test suite, linter config, or CI** in the repo. When adding functionality, exercise it by running the CLI directly.

## Architecture

The design is a thin CLI shell over independent, pure-function service modules, with a shared core for cross-cutting concerns.

```
src/nexus/
  cli.py                 # Click command tree + all output formatting for crypt
  core/                  # cross-cutting: config, storage, audit, plugins
  modules/<domain>/service.py   # the actual logic for each domain
```

**Command flow.** Every command follows the same pattern in `cli.py`:
1. The root `cli` group loads `Config` into `ctx.obj` (via `load_config`).
2. The subcommand lazily imports its `service` module *inside the function body* (keeps startup fast and dependencies isolated per command).
3. It calls the service, writes an audit record, `click.echo`s JSON (or formatted text for `crypt`), and `sys.exit`s with a status code.

**Exit-code convention** (meaningful for scripting): `0` = success with results, `3` = ran successfully but found nothing, `1` = error. Preserve this when adding commands.

**Services are pure and stdlib-shaped.** Module services (`modules/*/service.py`) take plain inputs and return plain `dict`s / lists of dicts. They do no printing, no `sys.exit`, and — except `log_analysis` — take no `Config`. Keep new logic here, not in `cli.py`.

**`core/` responsibilities:**
- `config.py` — `Config` dataclass built by merging `DEFAULT_TOML` with a user TOML (shallow `dict | dict` merge, so a user-provided `[section]` replaces the whole default section — not a deep merge). Ensures `~/.nexus` dirs exist. Note `DEFAULT_TOML` declares `crypto`, `security`, and geoip settings that are **not yet consumed** by any code.
- `audit.py` — `audit()` appends one JSON line per invocation to `cfg.audit_log` (`~/.nexus/audit.log`). Every CLI command calls this; keep doing so for new commands.
- `storage.py` — `duck_connect(db_dir)` opens `nexus.duckdb`. The only shared persistence primitive.
- `plugin_loader.py` — placeholder only; plugin loading and the `security.*` allowlist/signature settings in config are not implemented.

**Domain notes:**
- `cryptography/service.py` — the largest module. `detect()` runs a suite of heuristic detectors (`detect_encoders`, `detect_classical_*`, `detect_containers`, `detect_high_entropy_ciphertext`), each returning scored candidates `{name, score, category, params?}`. Results are deduped by `(name, category)`, sorted by score, capped at 15. Detection is heuristic/statistical — entropy, index of coincidence, chi-squared, charset ratios, and magic bytes — it does **not** decode anything. Categories (`encoder`, `armor`, `classical_cipher`, `modern_cipher`, `container`) drive the emoji/labels in the detailed formatter.
- `log_analysis/service.py` — `ingest()` reads JSONL, normalizes each object (nested values are JSON-stringified for parquet), writes a partitioned parquet dataset under `data_dir/parquet/<dataset_id>`, then registers it as a DuckDB **view** named by `default_table` (`events`). Each ingest replaces the view (`CREATE OR REPLACE VIEW`), so only the most recent dataset is queryable. `run_canned()` currently implements only `total_requests`.
- `osint/service.py` — `extract_meta()` returns file hashes (md5/sha1/sha256) + MIME + size for any file; EXIF/GPS parsing runs only for JPEG/TIFF. GPS is converted DMS→decimal and a Google Maps link is built. Pillow is imported defensively (degrades to no-EXIF if missing).
- `enumeration/service.py` — `detect_language()` identifies a file by extension (`EXT_MAP`) and shebang. **Caveat:** it expects a filesystem path, but the `enum code-id` CLI command passes the raw `-i` string straight through (`Path(snippet)`), so the README's inline-snippet example does not actually inspect snippet contents — it treats the string as a path.

## Conventions

- Python 3.11+; modules use `from __future__ import annotations` and modern typing.
- Runtime deps live in `pyproject.toml` (`click`, `duckdb`, `pyarrow`, `pandas`, `pillow`); the build backend is `hatchling` and only `src/nexus` is packaged.
- When adding a domain: create `modules/<domain>/service.py` with pure functions, then add a Click group/command in `cli.py` that lazy-imports it, calls `audit()`, and follows the exit-code convention.
- SQL identifiers are quoted via `_quote_ident` before interpolation, and query values are passed as DuckDB parameters — keep that split (identifiers interpolated, values parameterized) for any new queries.
