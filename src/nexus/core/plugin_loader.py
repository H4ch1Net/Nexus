from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import importlib.util
import sys

from nexus.core.audit import audit

PLUGIN_API_VERSION = 1


@dataclass
class PluginContext:
    """Passed to a plugin's register_cli(ctx) so it can attach new
    subcommands to the root CLI or to any of the existing module groups."""
    cfg: object
    cli: object
    crypt_group: object
    osint_group: object
    log_group: object
    enum_group: object
    ioc_group: object
    secrets_group: object


@dataclass
class PluginInfo:
    path: Path
    name: str = ""
    version: str = ""
    trusted: bool = False
    loaded: bool = False
    error: str = ""


def _allowlist_dirs(cfg) -> list[Path]:
    dirs = {cfg.plugins_dir.resolve()}
    for p in cfg.plugin_whitelist_paths:
        try:
            dirs.add(Path(p).resolve())
        except OSError:
            continue
    return list(dirs)


def _is_within_allowlist(p: Path, allowlist: list[Path]) -> bool:
    try:
        rp = p.resolve()
    except OSError:
        return False
    for d in allowlist:
        try:
            rp.relative_to(d)
            return True
        except ValueError:
            continue
    return False


def discover_plugin_files(cfg) -> list[Path]:
    """Non-recursive scan of allowlisted directories for plugin candidates:
    a top-level .py file, or a package dir with an __init__.py."""
    found: list[Path] = []
    for d in _allowlist_dirs(cfg):
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.is_file() and p.suffix == ".py" and not p.name.startswith("_"):
                found.append(p)
            elif p.is_dir() and (p / "__init__.py").is_file():
                found.append(p / "__init__.py")
    return found


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_trust(path: Path, cfg) -> tuple[bool, str]:
    digest = sha256_file(path)
    return digest in set(cfg.trusted_plugin_hashes), digest


def load_plugins(cfg, ctx: PluginContext) -> list[PluginInfo]:
    results: list[PluginInfo] = []
    allowlist = _allowlist_dirs(cfg)

    for path in discover_plugin_files(cfg):
        info = PluginInfo(path=path)

        if not _is_within_allowlist(path, allowlist):
            # Defends against a plugin file reached via a symlink that
            # escapes the allowlisted directory.
            info.error = "not within an allowlisted plugin directory"
            audit(cfg, module="plugin", action="load", target=str(path),
                  success_bool=False, notes=info.error)
            results.append(info)
            continue

        trusted, digest = verify_trust(path, cfg)
        info.trusted = trusted

        if cfg.require_plugin_signature and not trusted:
            info.error = f"untrusted (sha256={digest}); run `nexus plugin trust {path}` to allow"
            audit(cfg, module="plugin", action="load", target=str(path),
                  success_bool=False, notes=info.error)
            results.append(info)
            continue

        try:
            module_name = f"nexus_plugin_{digest[:16]}"
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                raise ImportError("could not create module spec")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            try:
                spec.loader.exec_module(module)
            except BaseException:
                sys.modules.pop(module_name, None)
                raise

            meta = getattr(module, "NEXUS_PLUGIN", None)
            if not isinstance(meta, dict):
                raise ValueError("plugin missing NEXUS_PLUGIN metadata dict")
            if meta.get("api_version") != PLUGIN_API_VERSION:
                raise ValueError(
                    f"unsupported api_version {meta.get('api_version')!r} "
                    f"(nexus supports {PLUGIN_API_VERSION})"
                )

            register_cli = getattr(module, "register_cli", None)
            if not callable(register_cli):
                raise ValueError("plugin missing register_cli(ctx) function")

            register_cli(ctx)

            info.name = str(meta.get("name", path.stem))
            info.version = str(meta.get("version", ""))
            info.loaded = True
            audit(cfg, module="plugin", action="load", target=str(path), success_bool=True,
                  notes=f"name={info.name} version={info.version} trusted={trusted}")
        except Exception as e:
            # One bad plugin must not take down the rest of the CLI.
            info.error = f"{type(e).__name__}: {e}"
            audit(cfg, module="plugin", action="load", target=str(path),
                  success_bool=False, notes=info.error)

        results.append(info)

    return results
