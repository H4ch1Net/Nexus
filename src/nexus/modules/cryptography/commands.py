"""CLI commands for the cryptography module."""
from __future__ import annotations

import sys

import click

from nexus.core import render
from nexus.core.audit import audit


# ----------------------------------------------------------------------------
# Human-readable formatters for `crypt detect`
# ----------------------------------------------------------------------------
_CATEGORY = {
    "encoder": "encoder",
    "armor": "armor",
    "classical_cipher": "classical cipher",
    "modern_cipher": "modern cipher",
    "container": "container",
}


def format_simple(result: dict) -> str:
    candidates = result["candidates"]
    if not candidates:
        return render.c("No matches found", "yellow")
    top = candidates[0]
    name = top["name"].replace("_", " ").title()
    score = top["score"]
    verb = "Detected" if score >= 0.85 else "Likely" if score >= 0.7 else "Possibly"
    line = f"{render.c(verb, 'green' if score >= 0.7 else 'yellow')}: {render.c(name, 'bold')} ({score:.0%} confidence)"
    alts = [c["name"].replace("_", " ").title() for c in candidates[1:4] if c["score"] > 0.65]
    if alts:
        line += "\n" + render.c(f"  also consider: {', '.join(alts)}", "gray")
    return line


def format_compact(result: dict) -> str:
    m = result["metrics"]
    header = render.c(
        f"input {result['input_length']} chars  "
        f"entropy {m['entropy']:.2f}  IC {m['index_of_coincidence']:.4f}", "gray")
    rows = [
        (i, c["name"].replace("_", " ").title(), f"{c['score']:.0%}",
         _CATEGORY.get(c.get("category", ""), c.get("category", "")))
        for i, c in enumerate(result["candidates"], 1)
    ]
    return header + "\n\n" + render.table(["#", "name", "score", "category"], rows)


def format_detailed(result: dict) -> str:
    m = result["metrics"]
    out = [render.heading("Cryptographic detection"), ""]
    out.append(render.kv([
        ("input length", f"{result['input_length']} chars"),
        ("entropy", f"{m['entropy']:.4f} bits/byte"),
        ("printable", f"{m['printable_ratio']:.1%}"),
        ("index of coincidence", f"{m['index_of_coincidence']:.4f}"),
    ]))

    ent, ic = m["entropy"], m["index_of_coincidence"]
    hint = ("high entropy: modern encryption or compression" if ent > 7.5
            else "medium entropy: encoding or classical cipher" if ent > 6.0
            else "low entropy: plaintext or simple substitution")
    out += ["", render.c("  interpretation: " + hint, "gray")]
    if ic > 0.06:
        out.append(render.c("  high IC: monoalphabetic or transposition (letters preserved)", "gray"))
    elif ic > 0.045:
        out.append(render.c("  medium IC: polyalphabetic cipher", "gray"))
    elif ic > 0:
        out.append(render.c("  low IC: random data or strong encryption", "gray"))

    if not result["candidates"]:
        out += ["", render.c("No strong matches found.", "yellow")]
        return "\n".join(out)

    out += ["", render.heading(f"Candidates ({len(result['candidates'])})"), ""]
    for i, cand in enumerate(result["candidates"], 1):
        name = cand["name"].replace("_", " ").title()
        score = cand["score"]
        out.append(f"  {i}. {render.c(name, 'bold')}  {render.bar(score)} {score:.0%} "
                   f"({render.confidence_word(score)})")
        cat = _CATEGORY.get(cand.get("category", ""), cand.get("category", ""))
        out.append(render.c(f"     {cat}", "gray"))
        params = cand.get("params")
        if params:
            for k, v in params.items():
                if isinstance(v, list):
                    v = ", ".join(str(x) for x in v[:6]) + (" ..." if len(v) > 6 else "")
                out.append(render.c(f"     {k}: {v}", "gray"))
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
        click.echo(render.c(f"error: {e}", "red"), err=True)
        audit(ctx.obj, module="crypt", action="detect", target="[inline]",
              success_bool=False, notes=f"error: {e}")
        sys.exit(1)


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
            click.echo(render.c("No readable decoding found.", "yellow"))
            sys.exit(3)
        else:
            lines = [render.heading("Auto-decode candidates"), ""]
            for r in results:
                recipe = render.c(" -> ".join(r.recipe), "cyan")
                lines.append(f"  {render.bar(r.score, 12)} {r.score:.0%}  {recipe}")
                preview = r.output if len(r.output) <= 200 else r.output[:200] + " ..."
                lines.append(render.c(f"     {preview!r}", "gray"))
            click.echo("\n".join(lines))
        sys.exit(0 if results else 3)

    try:
        out = codecs.decode(inline, codec, shift=shift, key=key)
    except codecs.DecodeError as e:
        click.echo(render.c(f"error: {e}", "red"), err=True)
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
        click.echo(render.kv(list(digests.items())))


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
        click.echo(render.c("No match. Not a recognized hash format.", "yellow"))
    else:
        rows = [(c["name"], f"{c['confidence']:.0%}", c["basis"]) for c in cands]
        click.echo(render.table(["algorithm", "confidence", "basis"], rows))
    sys.exit(0 if cands else 3)


@crypt.command("codecs")
def crypt_codecs():
    """List the codecs available to 'crypt decode'."""
    from nexus.modules.cryptography import codecs
    click.echo(render.heading("Available codecs") + "\n")
    click.echo("  " + "  ".join(codecs.list_codecs()))
