"""CLI commands for the log-analysis module."""
from __future__ import annotations

import json as _json
import sys
from pathlib import Path

import click

from nexus.core import render
from nexus.core.audit import audit


def _print_rows(rows: list[dict]) -> str:
    if not rows:
        return render.c("  (no rows)", "gray")
    headers = list(rows[0].keys())
    return render.table(headers, [[r.get(h) for h in headers] for r in rows])


@click.group()
def log():
    """Logs: ingest JSONL and run analytics with DuckDB."""


@log.command("ingest")
@click.option("-i", "--input", "path", type=click.Path(exists=True), required=True, help="JSONL file.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
@click.pass_context
def log_ingest(ctx, path, as_json):
    """Ingest a JSONL log file into the local DuckDB-backed table."""
    from nexus.modules.log_analysis.service import ingest
    res = ingest(ctx.obj, Path(path))
    audit(ctx.obj, module="log", action="ingest", target=path, success_bool=bool(res),
          notes=f"rows={res.get('rows', 0)}")
    if not res:
        click.echo(render.c("no rows ingested (empty file?)", "yellow"), err=True)
        sys.exit(1)
    if as_json:
        click.echo(render.dumps(res))
    else:
        click.echo(render.c("ingested", "green") + " " + render.kv([
            ("dataset", res["dataset_id"]), ("table", res["table"]),
            ("rows", res["rows"]), ("columns", len(res["columns"])),
            ("malformed", res["malformed_lines"]),
        ]).lstrip())
    sys.exit(0)


@log.command("canned")
@click.argument("name", required=False)
@click.option("--params", default="{}", help="JSON parameters for the query.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
@click.pass_context
def log_canned(ctx, name, params, as_json):
    """Run a built-in analytics query. Omit NAME to list them."""
    from nexus.modules.log_analysis.service import run_canned, list_canned
    if not name:
        click.echo(render.heading("Canned queries") + "\n")
        click.echo(render.kv(list(list_canned().items())))
        return
    res = run_canned(ctx.obj, name, _json.loads(params))
    ok = "error" not in res
    audit(ctx.obj, module="log", action=f"canned:{name}", target=res.get("table", ""), success_bool=ok)
    if as_json:
        click.echo(render.dumps(res))
    elif not ok:
        click.echo(render.c(f"error: {res['error']}", "red"), err=True)
    else:
        if res.get("sql"):
            click.echo(render.c(res["sql"], "gray") + "\n")
        click.echo(_print_rows(res["result"]))
    sys.exit(0 if ok else 3)


@log.command("query")
@click.argument("sql")
@click.option("--limit", type=int, default=200, help="Max rows to return.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
@click.pass_context
def log_query(ctx, sql, limit, as_json):
    """Run a read-only SELECT/WITH query against the ingested table."""
    from nexus.modules.log_analysis.service import run_query
    res = run_query(ctx.obj, sql, limit=limit)
    ok = "error" not in res
    audit(ctx.obj, module="log", action="query", target="[sql]", success_bool=ok)
    if as_json:
        click.echo(render.dumps(res))
    elif not ok:
        click.echo(render.c(f"error: {res['error']}", "red"), err=True)
    else:
        click.echo(_print_rows(res["result"]))
        note = f"{res['row_count']} row(s)"
        if res["truncated"]:
            note += f", showing first {limit}"
        click.echo("\n" + render.c(note, "gray"))
    sys.exit(0 if ok else 3)


@log.command("info")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
@click.pass_context
def log_info(ctx, as_json):
    """Show ingested datasets and the active table schema."""
    from nexus.modules.log_analysis.service import dataset_info
    res = dataset_info(ctx.obj)
    audit(ctx.obj, module="log", action="info", target="", success_bool=True)
    if as_json:
        click.echo(render.dumps(res))
        return
    out = [render.heading("Log store"), "", render.kv([("data dir", res["data_dir"])])]
    at = res["active_table"]
    out += ["", render.c(f"active table: {at['table']} "
                         f"({at['row_count'] if at['row_count'] is not None else 'empty'})", "bold")]
    if at["columns"]:
        out.append(_print_rows(at["columns"]))
    if res["datasets"]:
        out += ["", render.c("datasets", "bold"),
                _print_rows(res["datasets"])]
    else:
        out += ["", render.c("no datasets ingested yet", "gray")]
    click.echo("\n".join(out))
