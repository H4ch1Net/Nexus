import sys, json
import click
from pathlib import Path
from nexus.core.config import load_config
from nexus.core.audit import audit
from nexus.modules.cryptography.formatting import (
    format_simple_output, format_detailed_output, format_compact_output,
)


@click.group()
@click.option("--config", default="~/.nexus/config.toml", help="Path to config TOML")
@click.option("--no-plugins", is_flag=True, default=False, help="Skip loading plugins for this invocation.")
@click.pass_context
def cli(ctx, config, no_plugins):
    ctx.obj = load_config(config)
    if not no_plugins:
        from nexus.core.plugin_loader import load_plugins, PluginContext
        plugin_ctx = PluginContext(cfg=ctx.obj, cli=cli, crypt_group=crypt,
                                    osint_group=osint, log_group=log, enum_group=enum)
        for info in load_plugins(ctx.obj, plugin_ctx):
            if info.error:
                click.echo(f"⚠️  Plugin {info.path.name}: {info.error}", err=True)


# -------- CRYPT --------
@cli.group()
def crypt():
    """Cryptography helpers"""
    pass


@crypt.command("detect")
@click.option("-i", "--input", "inline", type=str, required=True,
              help="Inline payload only (no files).")
@click.option("-f", "--format", type=click.Choice(['simple', 'detailed', 'compact', 'json'], case_sensitive=False),
              default='simple', help="Output format (default: simple)")
@click.option("--top", type=int, default=10, help="Number of top candidates to show")
@click.pass_context
def crypt_detect(ctx, inline, format, top):
    """
    Detect cryptographic encodings, ciphers, and formats.
    
    Examples:
    
        # Simple one-line answer (default)
        nexus crypt detect -i "SGVsbG8gV29ybGQh"
        
        # Detailed analysis with full metrics
        nexus crypt detect -i "SGVsbG8gV29ybGQh" --format detailed
        
        # Compact table format
        nexus crypt detect -i "c2NyaWJibGU=" --format compact
        
        # Raw JSON for scripting
        nexus crypt detect -i "URYYB JBEYQ" --format json --top 5
    """
    from nexus.modules.cryptography.service import detect
    
    try:
        res = detect(inline)
        
        # Limit candidates to requested top N
        if res and 'candidates' in res and len(res['candidates']) > top:
            res['candidates'] = res['candidates'][:top]
        
        audit(ctx.obj, module="crypt", action="detect", target="[inline]",
              success_bool=bool(res), 
              notes=f"candidates={len(res.get('candidates', [])) if res else 0}")
        
        # Format output based on user preference
        if format == 'json':
            output = json.dumps(res, ensure_ascii=False, indent=2)
        elif format == 'compact':
            output = format_compact_output(res)
        elif format == 'detailed':
            output = format_detailed_output(res)
        else:  # simple
            output = format_simple_output(res)
        
        click.echo(output)
        sys.exit(0 if res else 3)
        
    except Exception as e:
        click.echo(f"❌ Error during detection: {str(e)}", err=True)
        audit(ctx.obj, module="crypt", action="detect", target="[inline]",
              success_bool=False, notes=f"error: {str(e)}")
        sys.exit(1)


# -------- OSINT --------
@cli.group()
def osint():
    """OSINT metadata"""
    pass


@osint.command("meta")
@click.option("-i", "--input", type=click.Path(exists=True), required=True)
@click.pass_context
def osint_meta(ctx, input):
    from nexus.modules.osint.service import extract_meta
    res = extract_meta(input)
    audit(ctx.obj, module="osint", action="meta", target=input, success_bool=bool(res))
    click.echo(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res else 3)


# -------- LOG --------
@cli.group()
def log():
    """Log ingestion and analytics"""
    pass


@log.command("ingest")
@click.option("-i", "--input", type=click.Path(exists=True), required=True)
@click.pass_context
def log_ingest(ctx, input):
    from nexus.modules.log_analysis.service import ingest
    res = ingest(ctx.obj, Path(input))
    audit(ctx.obj, module="log", action="ingest", target=input, success_bool=bool(res),
          notes=f"table={res.get('table')} rows={res.get('rows', 0)}")
    click.echo(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res.get("table") else 1)


@log.command("queries")
def log_queries():
    """List available canned queries and their parameters."""
    from nexus.modules.log_analysis.canned_queries import list_canned_queries
    click.echo(json.dumps(list_canned_queries(), ensure_ascii=False, indent=2))


@log.command("canned")
@click.argument("name")
@click.option("--params", default="{}")
@click.pass_context
def log_canned(ctx, name, params):
    from nexus.modules.log_analysis.service import run_canned
    res = run_canned(ctx.obj, name, json.loads(params))
    audit(ctx.obj, module="log", action=f"canned:{name}",
          target=res.get('table', ''), success_bool=bool(res.get('result')))
    click.echo(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res.get("result") is not None else 3)


# -------- ENUM --------
@cli.group()
def enum():
    """Enumeration helpers"""
    pass


@enum.command("code-id")
@click.option("-i", "--input", "inline", required=True, type=str,
              help="Inline code snippet only.")
@click.option("-n", "--filename", default=None, type=str,
              help="Optional filename hint (e.g. foo.py) - used only for its extension, never read from disk.")
@click.pass_context
def code_id(ctx, inline, filename):
    from nexus.modules.enumeration.service import detect_language
    res = detect_language(inline, filename=filename)
    audit(ctx.obj, module="enum", action="code-id", target="[inline]", success_bool=bool(res))
    click.echo(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res.get("candidates") else 3)


# -------- PLUGIN --------
@cli.group()
def plugin():
    """Plugin discovery and trust management"""
    pass


@plugin.command("list")
@click.pass_context
def plugin_list(ctx):
    from nexus.core.plugin_loader import discover_plugin_files, verify_trust
    cfg = ctx.obj
    out = []
    for path in discover_plugin_files(cfg):
        trusted, digest = verify_trust(path, cfg)
        out.append({"path": str(path), "sha256": digest, "trusted": trusted})
    click.echo(json.dumps(out, ensure_ascii=False, indent=2))


@plugin.command("trust")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def plugin_trust(ctx, path):
    from nexus.core.plugin_loader import sha256_file
    from nexus.core.config import save_config
    cfg = ctx.obj
    digest = sha256_file(Path(path))

    hashes = set(cfg.raw.get("security", {}).get("trusted_plugin_hashes", []))
    if digest in hashes:
        click.echo(f"Already trusted: {digest}")
        return

    hashes.add(digest)
    cfg.raw.setdefault("security", {})["trusted_plugin_hashes"] = sorted(hashes)
    cfg.trusted_plugin_hashes = sorted(hashes)
    save_config(cfg.config_path, cfg.raw)
    audit(cfg, module="plugin", action="trust", target=path, success_bool=True, notes=f"sha256={digest}")
    click.echo(f"Trusted {path} (sha256={digest})")


# -------- WEB --------
@cli.group()
def web():
    """Local web UI"""
    pass


@web.command("serve")
@click.option("--host", default=None, help="Bind host (default from config, normally 127.0.0.1).")
@click.option("--port", default=None, type=int, help="Bind port (default from config, normally 8765).")
@click.pass_context
def web_serve(ctx, host, port):
    """Serve the local web UI. Binds to 127.0.0.1 by default - this tool is
    local-first and the web UI has no authentication, so only bind it to a
    non-loopback address if you understand the exposure."""
    cfg = ctx.obj
    bind_host = host or cfg.web_bind_host
    bind_port = port or cfg.web_port

    if bind_host not in ("127.0.0.1", "localhost", "::1"):
        click.echo(f"⚠️  Binding to {bind_host} exposes the Nexus web UI beyond localhost. "
                   f"It has no authentication - anyone who can reach this host can use it.", err=True)

    try:
        from nexus.web.app import create_app
    except ImportError:
        click.echo("❌ The web UI requires Flask. Install it with: pip install nexus-tool[web]", err=True)
        sys.exit(1)

    app = create_app(cfg)
    click.echo(f"Serving Nexus web UI on http://{bind_host}:{bind_port}")
    app.run(host=bind_host, port=bind_port, debug=False, threaded=True)