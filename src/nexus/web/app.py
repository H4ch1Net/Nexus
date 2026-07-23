from __future__ import annotations
import json
import tempfile
from pathlib import Path

from flask import Flask, render_template, request, jsonify

from nexus.core.audit import audit
from nexus.modules.cryptography.formatting import (
    format_simple_output, format_detailed_output, format_compact_output,
)

MAX_UPLOAD_BYTES = 32 * 1024 * 1024  # 32 MiB, generous for a local single-user tool


def _json_or_none(result):
    # Pre-serialize in Python rather than via Jinja2's `tojson` filter.
    return json.dumps(result, ensure_ascii=False, indent=2) if result is not None else None


def create_app(cfg) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
    # Local-only tool, no accounts/sessions - a fixed key just satisfies Flask's
    # flash-message machinery, it protects nothing sensitive here.
    app.secret_key = "nexus-local-web-ui"

    @app.route("/")
    def index():
        return render_template("index.html")

    # -------- CRYPT --------
    @app.route("/crypt/detect", methods=["GET", "POST"])
    def crypt_detect():
        from nexus.modules.cryptography.service import detect

        result = None
        formatted = None
        error = None
        inline = ""
        fmt = "simple"

        if request.method == "POST":
            inline = request.form.get("inline", "")
            fmt = request.form.get("format", "simple")
            top = int(request.form.get("top", 10) or 10)

            if not inline:
                error = "Input is required."
            else:
                try:
                    result = detect(inline)
                    if result and "candidates" in result and len(result["candidates"]) > top:
                        result["candidates"] = result["candidates"][:top]
                    audit(cfg, module="crypt", action="detect", target="[inline]",
                          success_bool=bool(result),
                          notes=f"candidates={len(result.get('candidates', [])) if result else 0}",
                          interface="web")
                    if fmt == "json":
                        formatted = json.dumps(result, ensure_ascii=False, indent=2)
                    elif fmt == "compact":
                        formatted = format_compact_output(result)
                    elif fmt == "detailed":
                        formatted = format_detailed_output(result)
                    else:
                        formatted = format_simple_output(result)
                except Exception as e:
                    error = str(e)
                    audit(cfg, module="crypt", action="detect", target="[inline]",
                          success_bool=False, notes=f"error: {e}", interface="web")

        return render_template("crypt.html", formatted=formatted, error=error,
                                inline=inline, fmt=fmt)

    # -------- OSINT --------
    @app.route("/osint/meta", methods=["GET", "POST"])
    def osint_meta():
        from nexus.modules.osint.service import extract_meta

        result = None
        error = None

        if request.method == "POST":
            uploaded = request.files.get("file")
            if not uploaded or not uploaded.filename:
                error = "A file is required."
            else:
                # Ephemeral: process in a temp file, never persist the original upload.
                suffix = Path(uploaded.filename).suffix
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    uploaded.save(tmp.name)
                    tmp_path = Path(tmp.name)
                try:
                    result = extract_meta(str(tmp_path))
                    result["file"] = uploaded.filename  # don't leak the tempfile path
                    audit(cfg, module="osint", action="meta", target=uploaded.filename,
                          success_bool=bool(result), interface="web")
                except Exception as e:
                    error = str(e)
                    audit(cfg, module="osint", action="meta", target=uploaded.filename,
                          success_bool=False, notes=f"error: {e}", interface="web")
                finally:
                    tmp_path.unlink(missing_ok=True)

        return render_template("osint.html", result_json=_json_or_none(result), error=error)

    # -------- LOG --------
    @app.route("/log/ingest", methods=["GET", "POST"])
    def log_ingest():
        from nexus.modules.log_analysis.service import ingest

        result = None
        error = None

        if request.method == "POST":
            uploaded = request.files.get("file")
            if not uploaded or not uploaded.filename:
                error = "A JSONL file is required."
            else:
                with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
                    uploaded.save(tmp.name)
                    tmp_path = Path(tmp.name)
                try:
                    result = ingest(cfg, tmp_path)
                    audit(cfg, module="log", action="ingest", target=uploaded.filename,
                          success_bool=bool(result), notes=f"table={result.get('table')} rows={result.get('rows', 0)}",
                          interface="web")
                except Exception as e:
                    error = str(e)
                    audit(cfg, module="log", action="ingest", target=uploaded.filename,
                          success_bool=False, notes=f"error: {e}", interface="web")
                finally:
                    tmp_path.unlink(missing_ok=True)

        return render_template("log_ingest.html", result_json=_json_or_none(result), error=error)

    @app.route("/log/canned", methods=["GET", "POST"])
    def log_canned():
        from nexus.modules.log_analysis.service import run_canned
        from nexus.modules.log_analysis.canned_queries import list_canned_queries

        queries = list_canned_queries()
        result = None
        error = None
        selected = request.values.get("name", queries[0]["name"] if queries else "")
        params_raw = request.values.get("params", "{}")

        if request.method == "POST":
            try:
                params = json.loads(params_raw or "{}")
                result = run_canned(cfg, selected, params)
                audit(cfg, module="log", action=f"canned:{selected}",
                      target=result.get("table", ""), success_bool=bool(result.get("result")),
                      interface="web")
                if result.get("error"):
                    error = result["error"]
            except json.JSONDecodeError as e:
                error = f"Invalid params JSON: {e}"

        return render_template("log_canned.html", queries=queries, selected=selected,
                                params_raw=params_raw, result_json=_json_or_none(result), error=error)

    # -------- ENUM --------
    @app.route("/enum/code-id", methods=["GET", "POST"])
    def enum_code_id():
        from nexus.modules.enumeration.service import detect_language

        result = None
        error = None
        inline = ""
        filename = ""

        if request.method == "POST":
            inline = request.form.get("inline", "")
            filename = request.form.get("filename", "") or None
            if not inline:
                error = "Code snippet is required."
            else:
                result = detect_language(inline, filename=filename)
                audit(cfg, module="enum", action="code-id", target="[inline]",
                      success_bool=bool(result), interface="web")

        return render_template("enum.html", result_json=_json_or_none(result), error=error,
                                inline=inline, filename=filename or "")

    # -------- CRYPT: codec / hash-id / xor --------
    @app.route("/crypt/codec", methods=["GET", "POST"])
    def crypt_codec():
        from nexus.modules.cryptography.codec import encode, decode, CodecError, SCHEMES

        output = None
        error = None
        inline = ""
        scheme = "base64"
        direction = "encode"
        shift = 13

        if request.method == "POST":
            inline = request.form.get("inline", "")
            scheme = request.form.get("scheme", "base64")
            direction = request.form.get("direction", "encode")
            shift = int(request.form.get("shift", 13) or 13)
            if not inline:
                error = "Input is required."
            else:
                try:
                    fn = encode if direction == "encode" else decode
                    output = fn(inline, scheme, shift=shift)
                    audit(cfg, module="crypt", action=f"{direction}:{scheme}", target="[inline]",
                          success_bool=True, interface="web")
                except CodecError as e:
                    error = str(e)
                    audit(cfg, module="crypt", action=f"{direction}:{scheme}", target="[inline]",
                          success_bool=False, notes=f"error: {e}", interface="web")

        return render_template("crypt_codec.html", output=output, error=error, inline=inline,
                                scheme=scheme, direction=direction, shift=shift, schemes=SCHEMES)

    @app.route("/crypt/hash-id", methods=["GET", "POST"])
    def crypt_hash_id():
        from nexus.modules.cryptography.hashid import identify_hash

        result = None
        error = None
        inline = ""

        if request.method == "POST":
            inline = request.form.get("inline", "")
            if not inline:
                error = "Input is required."
            else:
                result = identify_hash(inline)
                audit(cfg, module="crypt", action="hash-id", target="[inline]",
                      success_bool=bool(result["candidates"]),
                      notes=f"candidates={len(result['candidates'])}", interface="web")

        return render_template("crypt_hashid.html", result_json=_json_or_none(result),
                                error=error, inline=inline)

    @app.route("/crypt/xor", methods=["GET", "POST"])
    def crypt_xor():
        from nexus.modules.cryptography.xor import apply, bruteforce, XorError

        result = None
        error = None
        inline = ""
        key = ""
        input_format = "hex"
        key_format = "text"
        mode = "apply"

        if request.method == "POST":
            inline = request.form.get("inline", "")
            key = request.form.get("key", "")
            input_format = request.form.get("input_format", "hex")
            key_format = request.form.get("key_format", "text")
            mode = request.form.get("mode", "apply")
            if not inline:
                error = "Input is required."
            else:
                try:
                    if mode == "bruteforce":
                        result = bruteforce(inline, input_format=input_format, top=10)
                        audit(cfg, module="crypt", action="xor:bruteforce", target="[inline]",
                              success_bool=True, interface="web")
                    elif not key:
                        error = "Key is required unless using bruteforce."
                    else:
                        result = apply(inline, key, input_format=input_format, key_format=key_format)
                        audit(cfg, module="crypt", action="xor:apply", target="[inline]",
                              success_bool=True, interface="web")
                except XorError as e:
                    error = str(e)
                    audit(cfg, module="crypt", action="xor", target="[inline]",
                          success_bool=False, notes=f"error: {e}", interface="web")

        return render_template("crypt_xor.html", result_json=_json_or_none(result), error=error,
                                inline=inline, key=key, input_format=input_format,
                                key_format=key_format, mode=mode)

    # -------- IOC --------
    @app.route("/ioc/extract", methods=["GET", "POST"])
    def ioc_extract():
        from nexus.modules.ioc.service import extract

        result = None
        error = None
        inline = ""

        if request.method == "POST":
            inline = request.form.get("inline", "")
            if not inline:
                error = "Input is required."
            else:
                result = extract(inline)
                audit(cfg, module="ioc", action="extract", target="[inline]",
                      success_bool=result["total_matches"] > 0,
                      notes=f"matches={result['total_matches']}", interface="web")

        return render_template("ioc.html", result=result, result_json=_json_or_none(result),
                                error=error, inline=inline)

    # -------- SECRETS --------
    @app.route("/secrets/scan", methods=["GET", "POST"])
    def secrets_scan():
        from nexus.modules.secrets.service import scan

        result = None
        error = None
        inline = ""

        if request.method == "POST":
            inline = request.form.get("inline", "")
            if not inline:
                error = "Input is required."
            else:
                result = scan(inline)
                audit(cfg, module="secrets", action="scan", target="[inline]",
                      success_bool=result["findings_count"] > 0,
                      notes=f"findings={result['findings_count']}", interface="web")

        return render_template("secrets.html", result=result, result_json=_json_or_none(result),
                                error=error, inline=inline)

    # -------- AUDIT LOG --------
    @app.route("/audit")
    def audit_log_view():
        limit = request.args.get("limit", 100, type=int) or 100
        limit = max(1, min(limit, 1000))
        entries = []
        if cfg.audit_log.exists():
            with cfg.audit_log.open("r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in reversed(lines[-limit:]):
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return render_template("audit.html", entries=entries, limit=limit)

    return app
