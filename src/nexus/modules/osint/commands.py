"""CLI commands for the OSINT / metadata module."""
from __future__ import annotations

import sys

import click

from nexus.core import render
from nexus.core.audit import audit


def _format_meta(res: dict) -> str:
    out = [render.heading("File metadata"), ""]
    out.append(render.kv([
        ("file", res["file"]),
        ("size", f"{res['file_size_bytes']} bytes"),
        ("mime", res["file_mime"]),
    ]))
    out += ["", render.c("hashes", "bold"), render.kv(list(res["hashes"].items()))]
    if res["metadata"]:
        out += ["", render.c("exif", "bold"), render.kv(list(res["metadata"].items()))]
    if res.get("gps"):
        g = res["gps"]
        out += ["", render.c("gps", "bold"),
                render.kv([("lat", g["lat"]), ("lon", g["lon"]), ("alt", g.get("alt"))])]
        if res.get("map_link"):
            out.append(render.c(f"  map: {res['map_link']}", "blue"))
    else:
        out += ["", render.c("no EXIF/GPS metadata found", "gray")]
    return "\n".join(out)


@click.group()
def osint():
    """OSINT: metadata, IOC extraction, and defanging."""


@osint.command("meta")
@click.option("-i", "--input", "path", type=click.Path(exists=True), required=True, help="Image/file path.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
@click.pass_context
def osint_meta(ctx, path, as_json):
    """Extract EXIF, GPS, hashes, and file metadata."""
    from nexus.modules.osint.service import extract_meta
    res = extract_meta(path)
    audit(ctx.obj, module="osint", action="meta", target=path, success_bool=bool(res))
    if not res:
        click.echo(render.c("file not found or unreadable", "red"), err=True)
        sys.exit(3)
    click.echo(render.dumps(res) if as_json else _format_meta(res))


@osint.command("strings")
@click.option("-i", "--input", "path", type=click.Path(exists=True), required=True, help="File to scan.")
@click.option("--min-len", type=int, default=4, help="Minimum string length.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
@click.pass_context
def osint_strings(ctx, path, min_len, as_json):
    """Extract printable strings and classify indicators (URLs, IPs, emails, hashes)."""
    from nexus.modules.osint.iocs import analyze_file
    res = analyze_file(path, min_len=min_len)
    audit(ctx.obj, module="osint", action="strings", target=path,
          success_bool=True, notes=f"iocs={res['ioc_total']}")
    if as_json:
        click.echo(render.dumps(res))
    else:
        out = [render.heading("IOC extraction"), ""]
        out.append(render.kv([("file", res["file"]),
                              ("strings", res["string_count"]),
                              ("indicators", res["ioc_total"])]))
        if res["iocs"]:
            out.append("")
            for kind, values in res["iocs"].items():
                out.append(render.c(f"  {kind} ({len(values)})", "bold"))
                for v in values[:20]:
                    out.append(f"    {v}")
                if len(values) > 20:
                    out.append(render.c(f"    ... {len(values) - 20} more", "gray"))
        else:
            out.append(render.c("  no indicators found", "gray"))
        click.echo("\n".join(out))
    sys.exit(0 if res["ioc_total"] else 3)


@osint.command("defang")
@click.option("-i", "--input", "text", required=True, help="Text to defang.")
@click.pass_context
def osint_defang(ctx, text):
    """Neutralize URLs/IPs/emails so they are safe to share (http -> hxxp, . -> [.])."""
    from nexus.modules.osint.iocs import defang
    audit(ctx.obj, module="osint", action="defang", target="[inline]", success_bool=True)
    click.echo(defang(text))


@osint.command("refang")
@click.option("-i", "--input", "text", required=True, help="Defanged text to restore.")
@click.pass_context
def osint_refang(ctx, text):
    """Reverse defanging back to live indicators."""
    from nexus.modules.osint.iocs import refang
    audit(ctx.obj, module="osint", action="refang", target="[inline]", success_bool=True)
    click.echo(refang(text))
