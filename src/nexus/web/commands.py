"""The `nexus serve` command: launch the local web UI."""
from __future__ import annotations

import webbrowser

import click

from nexus.core import render


@click.command("serve")
@click.option("--host", default="127.0.0.1", show_default=True, help="Interface to bind.")
@click.option("--port", default=8765, show_default=True, type=int, help="Port to listen on.")
@click.option("--open/--no-open", "open_browser", default=True, help="Open a browser window.")
def serve(host, port, open_browser):
    """Start the offline web UI (binds to loopback by default)."""
    from nexus.web.server import serve as make_server

    httpd = make_server(host, port)
    url = f"http://{host}:{port}/"
    click.echo(render.c("Nexus web UI", "bold", "cyan"))
    click.echo(render.kv([("url", url), ("bind", f"{host}:{port}")]))
    click.echo(render.c("Press Ctrl+C to stop.", "gray"))
    if open_browser and host in ("127.0.0.1", "localhost"):
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        click.echo("\n" + render.c("stopped", "yellow"))
    finally:
        httpd.server_close()
