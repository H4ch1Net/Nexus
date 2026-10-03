"""Local, offline web UI for Nexus.

A dependency-free server (stdlib ``http.server``) that exposes the module
services over a small JSON API and serves a single-page front end. It binds to
loopback by default and never makes outbound requests.
"""
from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict

from nexus import __version__

STATIC_DIR = Path(__file__).parent / "static"
MAX_BODY = 2 * 1024 * 1024  # 2 MiB request cap


# ----------------------------------------------------------------------------
# API handlers (pure: dict in, dict out)
# ----------------------------------------------------------------------------
def _api_detect(body: Dict[str, Any]) -> Dict[str, Any]:
    from nexus.modules.cryptography.service import detect
    return detect(str(body.get("input", "")))


def _api_decode(body: Dict[str, Any]) -> Dict[str, Any]:
    from nexus.modules.cryptography import codecs
    text = str(body.get("input", ""))
    codec = str(body.get("codec", "auto")).lower()
    if codec == "auto":
        results = codecs.magic(text, depth=int(body.get("depth", 3)))
        return {"mode": "auto", "candidates": [
            {"recipe": r.recipe, "output": r.output, "score": round(r.score, 3)} for r in results]}
    out = codecs.decode(text, codec, shift=int(body.get("shift", 3)), key=str(body.get("key", "")))
    return {"mode": codec, "output": out}


def _api_hash(body: Dict[str, Any]) -> Dict[str, Any]:
    from nexus.modules.cryptography import hashing
    return {"hashes": hashing.compute_hashes(str(body.get("input", "")).encode("utf-8"))}


def _api_hash_id(body: Dict[str, Any]) -> Dict[str, Any]:
    from nexus.modules.cryptography import hashing
    return {"candidates": hashing.identify_hash(str(body.get("input", "")))}


def _api_code_id(body: Dict[str, Any]) -> Dict[str, Any]:
    from nexus.modules.enumeration.service import detect_language
    return detect_language(str(body.get("input", "")))


def _api_ports(body: Dict[str, Any]) -> Dict[str, Any]:
    from nexus.modules.enumeration.ports import resolve
    return resolve(str(body.get("input", "")))


def _api_iocs(body: Dict[str, Any]) -> Dict[str, Any]:
    from nexus.modules.osint.iocs import find_iocs
    iocs = find_iocs(str(body.get("input", "")))
    return {"iocs": iocs, "ioc_total": sum(len(v) for v in iocs.values())}


def _api_defang(body: Dict[str, Any]) -> Dict[str, Any]:
    from nexus.modules.osint.iocs import defang, refang
    text = str(body.get("input", ""))
    fn = refang if body.get("mode") == "refang" else defang
    return {"output": fn(text)}


ROUTES: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "/api/crypt/detect": _api_detect,
    "/api/crypt/decode": _api_decode,
    "/api/crypt/hash": _api_hash,
    "/api/crypt/hash-id": _api_hash_id,
    "/api/enum/code-id": _api_code_id,
    "/api/enum/ports": _api_ports,
    "/api/osint/iocs": _api_iocs,
    "/api/osint/defang": _api_defang,
}


class NexusHandler(BaseHTTPRequestHandler):
    server_version = f"Nexus/{__version__}"
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # silence default stderr logging
        pass

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, code: int, obj: Any) -> None:
        self._send(code, json.dumps(obj, default=str).encode("utf-8"), "application/json")

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/api/meta":
            self._send_json(200, {"version": __version__, "routes": sorted(ROUTES)})
            return
        self._serve_static(path)

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        handler = ROUTES.get(path)
        if handler is None:
            self._send_json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_BODY:
            self._send_json(413, {"error": "payload too large"})
            return
        try:
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw or b"{}")
            if not isinstance(body, dict):
                raise ValueError("expected a JSON object")
            self._send_json(200, handler(body))
        except Exception as e:
            self._send_json(400, {"error": str(e)})

    def _serve_static(self, path: str) -> None:
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        target = (STATIC_DIR / rel).resolve()
        # Prevent path traversal outside the static directory.
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
            self._send_json(404, {"error": "not found"})
            return
        ctype, _ = mimetypes.guess_type(str(target))
        self._send(200, target.read_bytes(), ctype or "application/octet-stream")


def serve(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    """Create (but do not start) a configured server instance."""
    return ThreadingHTTPServer((host, port), NexusHandler)


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    httpd = serve(host, port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
