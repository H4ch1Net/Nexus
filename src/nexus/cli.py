import sys, json
import click
from pathlib import Path

from nexus.core.config import load_config
from nexus.core.audit import audit

@click.group()
@click.option("--config", default="~/.nexus/config.toml", help="Path to config TOML")
@click.pass_context
def cli(ctx, config):
    ctx.obj = load_config(config)

# -------- CRYPT --------
@cli.group()
def crypt():
    """Cryptography helpers"""
    pass

@crypt.command("detect")
@click.option("-i","--input", type=click.Path(exists=True), required=True)
@click.pass_context
def crypt_detect(ctx, input):
    from nexus.modules.cryptography.service import detect
    res = detect(input_path=input)
    audit(ctx.obj, module="crypt", action="detect", target=input, success_bool=True,
          notes=f"candidates={len(res.get('candidates', []))}")
    click.echo(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res else 3)

# -------- OSINT --------
@cli.group()
def osint():
    """OSINT metadata"""
    pass

@osint.command("meta")
@click.option("-i","--input", type=click.Path(exists=True), required=True)
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
@click.option("-i","--input", type=click.Path(exists=True), required=True)
@click.pass_context
def log_ingest(ctx, input):
    from nexus.modules.log_analysis.service import ingest
    res = ingest(ctx.obj, Path(input))
    audit(ctx.obj, module="log", action="ingest", target=input, success_bool=bool(res),
          notes=f"table={res.get('table')} rows={res.get('rows',0)}")
    click.echo(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res.get("table") else 1)

@log.command("canned")
@click.argument("name")
@click.option("--params", default="{}")
@click.pass_context
def log_canned(ctx, name, params):
    from nexus.modules.log_analysis.service import run_canned
    res = run_canned(ctx.obj, name, json.loads(params))
    audit(ctx.obj, module="log", action=f"canned:{name}", target=res.get('table',''), success_bool=bool(res.get('result')))
    click.echo(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res.get("result") is not None else 3)

# -------- ENUM --------
@cli.group()
def enum():
    """Enumeration helpers"""
    pass

@enum.command("code-id")
@click.option("-i","--input", type=click.Path(exists=True), required=True)
@click.pass_context
def code_id(ctx, input):
    from nexus.modules.enumeration.service import detect_language
    res = detect_language(Path(input))
    audit(ctx.obj, module="enum", action="code-id", target=input, success_bool=True)
    click.echo(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res.get("candidates") else 3)
