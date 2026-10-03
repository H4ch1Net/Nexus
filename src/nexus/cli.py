"""Nexus command-line entry point.

A thin wrapper that loads configuration and registers each module's command
group. All real work lives in the module packages under ``nexus.modules`` and
``nexus.web``.
"""
from __future__ import annotations

import click

from nexus import __version__
from nexus.core.config import load_config
from nexus.modules.cryptography.commands import crypt
from nexus.modules.enumeration.commands import enum
from nexus.modules.log_analysis.commands import log
from nexus.modules.osint.commands import osint
from nexus.web.commands import serve

_BANNER = """\
nexus — local-first toolkit for cryptography, OSINT, logs, and enumeration.
Runs entirely offline. No accounts, no telemetry.
"""


@click.group(help=_BANNER)
@click.version_option(__version__, "-V", "--version", prog_name="nexus")
@click.option("--config", default="~/.nexus/config.toml", show_default=True,
              help="Path to the config TOML.")
@click.pass_context
def cli(ctx, config):
    ctx.obj = load_config(config)


cli.add_command(crypt)
cli.add_command(enum)
cli.add_command(osint)
cli.add_command(log)
cli.add_command(serve)


if __name__ == "__main__":  # pragma: no cover
    cli()
