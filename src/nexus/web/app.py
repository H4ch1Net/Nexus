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

    return app
