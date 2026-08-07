"""Typer wiring. The ONLY module allowed to write to stdout/stderr (a CLI's UI);
all diagnostics go to the logfile (see logging_setup). Composition root: the only
module that instantiates concrete graphs; `_guarded` maps errors to exit codes."""
from __future__ import annotations

import pathlib
from collections.abc import Callable

import typer

from .. import __version__
from ..config.errors import ConfigError
from ..config.loader import ConfigLoader
from ..errors import ServanError
from ..infrastructure import SubprocessRunner, SystemClock
from ..ledger import BeadsLedger, LedgerError
from ..lint import LintEngine, Severity
from ..logging_setup import configure_logging, get_logger
from ..rendering.sync_service import SyncService
from ..scaffold import RepoTemplateSource, ScaffoldError, ScaffoldService
from ..status import StatusService

app = typer.Typer(no_args_is_help=True, add_completion=False, invoke_without_command=True,
                  help="House spirit for multi-agent coding.")
_log = get_logger("cli")


def _guarded[T](fn: Callable[..., T], *args, **kwargs) -> T:
    """Central exit-code guard (DESIGN.md table): known package errors -> 2,
    ServanError -> its exit_code, anything unexpected -> 1 with a logfile trace."""
    try:
        return fn(*args, **kwargs)
    except typer.Exit:
        raise
    except (ConfigError, LedgerError, ScaffoldError, ServanError) as exc:
        _log.error("%s", exc)
        typer.secho(f"servan: {exc}", fg="red", err=True)
        raise typer.Exit(getattr(exc, "exit_code", 2))
    except Exception as exc:  # noqa: BLE001 — central guard: unexpected -> exit 1 by design
        _log.exception("unexpected error")
        typer.secho(f"servan: unexpected error: {exc} (details in logfile)", fg="red", err=True)
        raise typer.Exit(1)


@app.callback()
def _main(ctx: typer.Context,
          version: bool = typer.Option(False, "--version", is_eager=True),
          config_dir: pathlib.Path | None = typer.Option(
              None, "--config-dir", help="Override $SERVAN_CONFIG_DIR.")) -> None:
    configure_logging(pathlib.Path.cwd())
    ctx.obj = config_dir
    if version:
        typer.echo(f"servan {__version__}")
        raise typer.Exit()


@app.command()
def sync(ctx: typer.Context,
         project: pathlib.Path = typer.Option(pathlib.Path("."), "--project", "-p"),
         check: bool = typer.Option(False, "--check",
                                    help="Diff-only: write nothing, exit 3 on drift.")) -> None:
    """Render layered TOML config -> opencode.json + agent model lines."""
    service = SyncService(ConfigLoader(ctx.obj))
    results = _guarded(service.sync, project, check=check)
    if check:
        drifted = [r for r in results if r.changed]
        for result in drifted:
            typer.echo(f"drift: {result.path} ({result.summary})")
        if drifted:
            raise typer.Exit(3)
        typer.echo(f"in sync ({len(results)} artifacts).")
        return
    for result in results:
        typer.echo(f"  {result.summary}")
    typer.echo(f"synced {len(results)} artifacts.")


@app.command()
def new(name: str, no_bd: bool = typer.Option(False, "--no-bd")) -> None:
    """Scaffold a new project from the servan template."""
    service = ScaffoldService(RepoTemplateSource(), SubprocessRunner())
    target = _guarded(service.create, pathlib.Path(name), with_ledger=not no_bd)
    typer.echo(f"created {target}")


@app.command()
def status(project: pathlib.Path = typer.Option(pathlib.Path("."), "--project", "-p")) -> None:
    """Task ledger -> wiki/status.md."""
    service = StatusService(BeadsLedger(project), SystemClock())
    target = _guarded(service.write, project)
    typer.echo(f"wrote {target}")


def _stub(task: str) -> None:
    _log.warning("stub command invoked (%s)", task)
    typer.secho(f"servan: not implemented yet — {task} in dev/BACKLOG.md", fg="yellow", err=True)
    raise typer.Exit(1)


@app.command()
def lint(project: pathlib.Path = typer.Option(pathlib.Path("."), "--project", "-p")) -> None:
    """Validate OKF conformance, servan extension, and the wiki link graph."""
    findings = _guarded(LintEngine().run, project)
    for finding in findings:
        typer.echo(f"{finding.severity.value}: {finding.rule}: "
                   f"{finding.path}: {finding.message}")
    if any(f.severity is Severity.ERROR for f in findings):
        raise typer.Exit(3)
    typer.echo("lint clean." if not findings else f"{len(findings)} warning(s), no errors.")


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
