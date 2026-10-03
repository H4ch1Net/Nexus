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
    from nexus import __version__
    from nexus.web.server import serve as make_server

    try:
        httpd = make_server(host, port)
    except OSError as e:
        click.echo(render.fault(f"cannot bind {host}:{port} ({e.strerror or e}). Try --port."), err=True)
        raise SystemExit(1)
    url = f"http://{host}:{port}/"
    click.echo(render.lockup([
        f"{render.c('nexus', 'bold')} {render.note('console ' + __version__)}",
        render.c(url, "signal"),
        render.note("local · offline · ctrl+c to stop"),
    ]))
    if host not in ("127.0.0.1", "localhost", "::1"):
        click.echo("\n" + render.note(f"warning: bound to {host}; the console is reachable from your network."))
    if open_browser and host in ("127.0.0.1", "localhost"):
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        click.echo("\n" + render.note("stopped"))
    finally:
        httpd.server_close()
