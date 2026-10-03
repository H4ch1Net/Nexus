"""CLI commands for the enumeration module."""
from __future__ import annotations

import sys

import click

from nexus.core import render
from nexus.core.audit import audit


def _format_langs(result: dict) -> str:
    cands = result["candidates"]
    rows = [(c["language"], f"{c['confidence']:.0%}", c["evidence"], c.get("matched_rules", 0))
            for c in cands]
    top = cands[0]
    head = (f"{render.c(top['language'], 'bold')} "
            f"({top['confidence']:.0%}, via {top['evidence']})")
    return head + "\n\n" + render.table(["language", "confidence", "evidence", "rules"], rows)


@click.group()
def enum():
    """Enumeration: language identification and service lookup."""


@enum.command("code-id")
@click.option("-i", "--input", "inline", required=True, help="Inline code snippet.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
@click.pass_context
def code_id(ctx, inline, as_json):
    """Identify the programming language of a code snippet."""
    from nexus.modules.enumeration.service import detect_language
    res = detect_language(inline)
    audit(ctx.obj, module="enum", action="code-id", target="[inline]",
          success_bool=res["candidates"][0]["language"] != "Unknown")
    click.echo(render.dumps(res) if as_json else _format_langs(res))
    sys.exit(0 if res["candidates"][0]["language"] != "Unknown" else 3)


@enum.command("file-id")
@click.option("-i", "--input", "path", type=click.Path(exists=True), required=True, help="File to inspect.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
@click.pass_context
def file_id(ctx, path, as_json):
    """Identify a file's language from its extension, shebang, and content."""
    from nexus.modules.enumeration.service import detect_language_file
    res = detect_language_file(path)
    audit(ctx.obj, module="enum", action="file-id", target=path,
          success_bool=res["candidates"][0]["language"] != "Unknown")
    click.echo(render.dumps(res) if as_json else _format_langs(res))
    sys.exit(0 if res["candidates"][0]["language"] != "Unknown" else 3)


@enum.command("ports")
@click.argument("query")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
@click.pass_context
def ports(ctx, query, as_json):
    """Look up a well-known port by number, or search services by name.

    Examples: 'nexus enum ports 443', 'nexus enum ports smb'
    """
    from nexus.modules.enumeration.ports import resolve
    res = resolve(query)
    audit(ctx.obj, module="enum", action="ports", target=query, success_bool=bool(res["matches"]))
    if as_json:
        click.echo(render.dumps(res))
    elif not res["matches"]:
        click.echo(render.c(f"No match for {query!r}.", "yellow"))
    else:
        rows = [(m["port"], m["service"], m["protocol"], m["description"]) for m in res["matches"]]
        click.echo(render.table(["port", "service", "proto", "description"], rows))
    sys.exit(0 if res["matches"] else 3)
