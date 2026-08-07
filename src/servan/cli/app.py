"""Typer wiring. The ONLY module allowed to write to stdout/stderr (a CLI's UI);
all diagnostics go to the logfile (see logging_setup)."""
from __future__ import annotations

import pathlib

import typer

from .. import __version__
from ..config.errors import ConfigError
from ..infrastructure import SubprocessRunner
from ..logging_setup import configure_logging, get_logger
from ..rendering.sync_service import SyncService
from ..scaffold import RepoTemplateSource, ScaffoldError, ScaffoldService

app = typer.Typer(no_args_is_help=True, add_completion=False,
                  help="House spirit for multi-agent coding.")
_log = get_logger("cli")


@app.callback()
def _main(version: bool = typer.Option(False, "--version", is_eager=True)) -> None:
    configure_logging(pathlib.Path.cwd())
    if version:
        typer.echo(f"servan {__version__}")
        raise typer.Exit()


@app.command()
def sync(project: pathlib.Path = typer.Option(pathlib.Path("."), "--project", "-p")) -> None:
    """Render layered TOML config -> opencode.json + agent model lines."""
    try:
        results = SyncService().sync(project)
    except ConfigError as exc:
        _log.error("sync failed: %s", exc)
        typer.secho(f"servan: {exc}", fg="red", err=True)
        raise typer.Exit(2)
    for result in results:
        typer.echo(f"  {result.summary}")
    typer.echo(f"synced {len(results)} artifacts.")


def _stub(task: str) -> None:
    _log.warning("stub command invoked (%s)", task)
    typer.secho(f"servan: not implemented yet — {task} in dev/BACKLOG.md", fg="yellow", err=True)
    raise typer.Exit(1)


@app.command()
def new(name: str, no_bd: bool = typer.Option(False, "--no-bd")) -> None:
    """Scaffold a new project from the servan template."""
    service = ScaffoldService(RepoTemplateSource(), SubprocessRunner())
    try:
        target = service.create(pathlib.Path(name), with_ledger=not no_bd)
    except ScaffoldError as exc:
        _log.error("new failed: %s", exc)
        typer.secho(f"servan: {exc}", fg="red", err=True)
        raise typer.Exit(2)
    typer.echo(f"created {target}")


@app.command()
def status() -> None:
    """Task ledger -> wiki/status.md."""
    _stub("S-04")


@app.command()
def lint() -> None:
    """Validate OKF conformance, servan extension, and the wiki link graph."""
    _stub("S-07")


@app.command()
def council(spec: pathlib.Path) -> None:
    """Run the Delphi consensus loop over a spec."""
    _stub("S-08")


@app.command()
def canary(role: str, candidate: str) -> None:
    """Golden-bead regression check before a model swap."""
    _stub("S-10")


@app.command()
def watch(port: int = typer.Option(9105, "--port")) -> None:
    """Context warden + Prometheus exporter daemon."""
    _stub("S-13/S-15")
