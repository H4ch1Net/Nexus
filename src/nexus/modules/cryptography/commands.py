"""CLI commands for the cryptography module."""
from __future__ import annotations

import sys

import click

from nexus.core import render
from nexus.core.audit import audit

_CATEGORY = {
    "encoder": "encoder",
    "armor": "armor",
    "classical_cipher": "classical cipher",
    "modern_cipher": "modern cipher",
    "container": "container",
}


def _name(c: dict) -> str:
    return c["name"].replace("_", " ")


def _cat(c: dict) -> str:
    return _CATEGORY.get(c.get("category", ""), c.get("category", ""))


# ----------------------------------------------------------------------------
# `crypt detect` formatters
# ----------------------------------------------------------------------------
def format_simple(result: dict) -> str:
    candidates = result["candidates"]
    if not candidates:
        return render.note("No known pattern matched this input.")
    top = candidates[0]
    line = (f"{render.c('■', 'signal')} {render.c(_name(top), 'bold')}  "
            f"{render.meter(top['score'], 12)}  {render.label(render.confidence_word(top['score']))}"
            f"  {render.note(_cat(top))}")
    alts = [_name(c) for c in candidates[1:4] if c["score"] > 0.65]
    if alts:
        line += "\n  " + render.label("also") + "  " + render.note(" · ".join(alts))
    return line


def _metric_line(result: dict) -> str:
    m = result["metrics"]
    return render.note(f"{result['input_length']} chars · entropy {m['entropy']:.2f} · "
                       f"IC {m['index_of_coincidence']:.4f}")


def _candidate_table(candidates: list[dict]) -> str:
    rows = [
        (render.c(f"{i:02d}", "signal" if i == 1 else "muted"), _name(c), render.note(_cat(c)),
         f"{render.meter(c['score'])}  {render.label(render.confidence_word(c['score']))}")
        for i, c in enumerate(candidates, 1)
    ]
    return render.table(["#", "candidate", "category", "confidence"], rows)


def format_compact(result: dict) -> str:
    if not result["candidates"]:
        return _metric_line(result) + "\n\n" + render.note("No known pattern matched this input.")
    return "  " + _metric_line(result) + "\n\n" + _candidate_table(result["candidates"])


def format_detailed(result: dict) -> str:
    m = result["metrics"]
    ent, ic = m["entropy"], m["index_of_coincidence"]
    ent_axis, ent_refs = render.scale(ent, 0, 8, refs={"text": 4.2, "base64": 6.0})
    ic_axis, ic_refs = render.scale(ic, 0, 0.1, refs={"random": 0.038, "english": 0.067})

    hint = ("high entropy: modern encryption or compression" if ent > 7.5
            else "medium entropy: encoding or classical cipher" if ent > 6.0
            else "low entropy: plaintext or simple substitution")
    if ic > 0.06:
        hint += "; high IC: letters preserved (monoalphabetic or transposition)"
    elif ic > 0.045:
        hint += "; medium IC: polyalphabetic cipher"
    elif ic > 0:
        hint += "; low IC: random data or strong encryption"

    out = [render.header("Detect", "01.1", "cryptography"), ""]
    out.append(render.kv([
        ("length", f"{result['input_length']} chars · printable {m['printable_ratio']:.0%}"),
        ("entropy", f"{ent:.4f} bits/byte\n{ent_axis}\n{ent_refs}"),
        ("index of coincidence", f"{ic:.4f}\n{ic_axis}\n{ic_refs}"),
    ]))
    out += ["", "  " + render.note(hint), ""]
    if not result["candidates"]:
        out.append("  " + render.note("No known pattern matched this input."))
    else:
        out.append(_candidate_table(result["candidates"]))
    return "\n".join(out)


@click.group()
def crypt():
    """Cryptography: detect, decode, and hash."""


@crypt.command("detect")
@click.option("-i", "--input", "inline", required=True, help="Inline payload to analyze.")
@click.option("-f", "--format", "fmt",
              type=click.Choice(["simple", "detailed", "compact", "json"], case_sensitive=False),
              default="simple", help="Output format.")
@click.option("--top", type=int, default=10, help="Max candidates to show.")
@click.pass_context
def crypt_detect(ctx, inline, fmt, top):
    """Detect encodings, classical ciphers, and modern crypto from a string."""
    from nexus.modules.cryptography.service import detect
    try:
        res = detect(inline)
        res["candidates"] = res["candidates"][:top]
        audit(ctx.obj, module="crypt", action="detect", target="[inline]",
              success_bool=bool(res["candidates"]), notes=f"candidates={len(res['candidates'])}")
        if fmt == "json":
            click.echo(render.dumps(res))
        elif fmt == "compact":
            click.echo(format_compact(res))
        elif fmt == "detailed":
            click.echo(format_detailed(res))
        else:
            click.echo(format_simple(res))
        sys.exit(0 if res["candidates"] else 3)
    except Exception as e:  # pragma: no cover - defensive
        click.echo(render.fault(str(e)), err=True)
        audit(ctx.obj, module="crypt", action="detect", target="[inline]",
              success_bool=False, notes=f"error: {e}")
        sys.exit(1)


def _chain(recipe: list[str]) -> str:
    return render.note(" → ").join(recipe)


@crypt.command("decode")
@click.option("-i", "--input", "inline", required=True, help="Payload to decode.")
@click.option("-c", "--codec", default="auto",
              help="Codec name, or 'auto' for recursive magic decoding. See 'crypt codecs'.")
@click.option("--shift", type=int, default=3, help="Shift for the caesar codec.")
@click.option("--key", default="", help="Key for the xor codec.")
@click.option("--depth", type=int, default=3, help="Max recipe depth for auto mode.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
@click.pass_context
def crypt_decode(ctx, inline, codec, shift, key, depth, as_json):
    """Decode a payload with a named codec, or auto-detect the recipe."""
    from nexus.modules.cryptography import codecs
    if codec.lower() == "auto":
        results = codecs.magic(inline, depth=depth)
        payload = {
            "mode": "auto",
            "candidates": [
                {"recipe": r.recipe, "output": r.output, "score": round(r.score, 3)}
                for r in results
            ],
        }
        audit(ctx.obj, module="crypt", action="decode", target="[inline]",
              success_bool=bool(results), notes=f"auto candidates={len(results)}")
        if as_json:
            click.echo(render.dumps(payload))
        elif not results:
            click.echo(render.note("No readable decoding found. Try a specific codec with -c."))
        else:
            best, rest = results[0], results[1:]
            gutter = render.c("│", "signal")
            lines = [render.header("Decode", "01.2", "cryptography"), ""]
            lines.append(f"  {render.c('01', 'signal')}  {_chain(best.recipe)}  "
                         f"{render.meter(best.score, 12)}  {render.c('BEST', 'signal', 'bold')}")
            for out_line in best.output.splitlines() or [""]:
                lines.append(f"  {gutter} {render.c(out_line, 'bold')}")
            if rest:
                rows = []
                for i, r in enumerate(rest, 2):
                    preview = r.output.replace("\n", " ")
                    preview = preview if len(preview) <= 40 else preview[:39] + "…"
                    rows.append((render.c(f"{i:02d}", "muted"), render.meter(r.score, 8),
                                 _chain(r.recipe), render.note(preview)))
                lines += ["", render.table(["#", "score", "other recipes", "output"], rows)]
            click.echo("\n".join(lines))
        sys.exit(0 if results else 3)

    try:
        out = codecs.decode(inline, codec, shift=shift, key=key)
    except codecs.DecodeError as e:
        click.echo(render.fault(str(e)), err=True)
        audit(ctx.obj, module="crypt", action="decode", target="[inline]",
              success_bool=False, notes=f"codec={codec} error: {e}")
        sys.exit(1)
    audit(ctx.obj, module="crypt", action="decode", target="[inline]",
          success_bool=True, notes=f"codec={codec}")
    if as_json:
        click.echo(render.dumps({"mode": codec, "output": out}))
    else:
        click.echo(out)


@crypt.command("hash")
@click.option("-i", "--input", "inline", help="String to hash.")
@click.option("-f", "--file", "file", type=click.Path(exists=True), help="File to hash.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
@click.pass_context
def crypt_hash(ctx, inline, file, as_json):
    """Compute common digests (md5, sha family, blake2, crc32) of a string or file."""
    from nexus.modules.cryptography import hashing
    if not inline and not file:
        raise click.UsageError("provide --input or --file")
    if file:
        digests = hashing.hash_file(file)
        target = file
    else:
        digests = hashing.compute_hashes(inline.encode("utf-8"))
        target = "[inline]"
    audit(ctx.obj, module="crypt", action="hash", target=target, success_bool=True)
    if as_json:
        click.echo(render.dumps({"target": target, "hashes": digests}))
    else:
        click.echo(render.header("Hash", "01.3", "cryptography") + "\n")
        click.echo(render.kv([(k.replace("_", "-"), v) for k, v in digests.items()]))


@crypt.command("hash-id")
@click.option("-i", "--input", "inline", required=True, help="Hash string to identify.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
@click.pass_context
def crypt_hash_id(ctx, inline, as_json):
    """Identify the likely algorithm of a hash by format, length, and charset."""
    from nexus.modules.cryptography import hashing
    cands = hashing.identify_hash(inline)
    audit(ctx.obj, module="crypt", action="hash-id", target="[inline]", success_bool=bool(cands))
    if as_json:
        click.echo(render.dumps({"input": inline.strip(), "candidates": cands}))
    elif not cands:
        click.echo(render.note("Not a recognized hash format."))
    else:
        rows = [(render.c(f"{i:02d}", "signal" if i == 1 else "muted"), c["name"],
                 render.meter(c["confidence"]), render.note(c["basis"]))
                for i, c in enumerate(cands, 1)]
        click.echo(render.header("Hash ID", "01.4", "cryptography") + "\n")
        click.echo(render.table(["#", "algorithm", "confidence", "basis"], rows))
    sys.exit(0 if cands else 3)


@crypt.command("codecs")
def crypt_codecs():
    """List the codecs available to 'crypt decode'."""
    from nexus.modules.cryptography import codecs
    names = codecs.list_codecs()
    click.echo(render.header("Codecs", "01.2", "cryptography") + "\n")
    per_row = 6
    for i in range(0, len(names), per_row):
        click.echo("  " + "".join(n.ljust(18) for n in names[i:i + per_row]).rstrip())
    click.echo("\n  " + render.note("auto mode chains the parameter-free codecs; caesar takes --shift, xor takes --key"))
