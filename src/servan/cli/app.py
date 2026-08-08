"""Typer wiring. The ONLY module allowed to write to stdout/stderr (a CLI's UI);
all diagnostics go to the logfile (see logging_setup). Composition root: the only
module that instantiates concrete graphs; `_guarded` maps errors to exit codes."""
from __future__ import annotations

import pathlib
import urllib.parse
from collections.abc import Callable

import typer

from .. import __version__
from ..canary import CanaryReport, CanaryRunner, OpenCodeTrial
from ..config.errors import ConfigError
from ..config.loader import ConfigLoader
from ..config.provider import ProviderConfig, ProviderKind
from ..config.standards_loader import StandardsLoader
from ..council import (
    CouncilEngine,
    DispatchVoterBackend,
    MeetingMinutes,
    MinutesWriter,
    OllamaVoterBackend,
    OpenAICompatibleVoterBackend,
    VoterBackend,
)
from ..errors import ServanError
from ..infrastructure import SubprocessRunner, SystemClock
from ..ledger import BeadsLedger, LedgerError
from ..library.loader import LibraryLoader
from ..library.service import LibraryService
from ..lint import LintEngine, Severity
from ..logging_setup import configure_logging, get_logger
from ..observability import (
    ContextWarden,
    MetricsRegistry,
    MetricsServer,
    OpenCodeSessionControl,
    OpenCodeSessionSource,
    WatchDaemon,
    WatchError,
    summarize,
)
from ..rendering.standards_renderer import render_standards_md
from ..rendering.sync_service import SyncService
from ..scaffold import PackagedTemplateSource, ScaffoldError, ScaffoldService
from ..status import StatusService
from ..team.resolver import Team, TeamResolver

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
                                    help="Diff-only: write nothing, exit 3 on drift."),
         force: bool = typer.Option(False, "--force",
                                    help="Overwrite locally modified library installs.")) -> None:
    """Render layered TOML config -> opencode.json + agent model lines."""
    service = SyncService(ConfigLoader(ctx.obj))
    results = _guarded(service.sync, project, check=check, force=force)
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


standards_app = typer.Typer(no_args_is_help=True, help="Inspect the standards layer.")
app.add_typer(standards_app, name="standards")


@standards_app.command("list")
def standards_list(ctx: typer.Context) -> None:
    """Enumerate the standards available in the global config dir."""
    loader = StandardsLoader(ConfigLoader(ctx.obj).standards_dir)
    names = _guarded(loader.available)
    for name in names:
        typer.echo(name)
    if not names:
        typer.echo("no standards found.")


@standards_app.command("show")
def standards_show(ctx: typer.Context, name: str) -> None:
    """Print a standard with its `extends` chain merged in (preview)."""
    loader = StandardsLoader(ConfigLoader(ctx.obj).standards_dir)
    merged = _guarded(loader.load, name)
    typer.echo(render_standards_md(merged, (name,)), nl=False)


library_app = typer.Typer(no_args_is_help=True,
                          help="Mother library of reusable agents and skills.")
app.add_typer(library_app, name="library")


@library_app.command("list")
def library_list(ctx: typer.Context,
                 project: pathlib.Path = typer.Option(pathlib.Path("."), "--project", "-p")
                 ) -> None:
    """Show library agents and skills, with installed/available state for this project."""
    loader = LibraryLoader(ctx.obj)
    config = _guarded(lambda: ConfigLoader(ctx.obj).load_project(project))
    for kind, items in (("agents", loader.agents()), ("skills", loader.skills())):
        typer.echo(f"{kind}:")
        for name in items:
            state = "installed" if kind == "agents" and name in config.team.extra_agents \
                else "available"
            typer.echo(f"  {name} ({state})")
        if not items:
            typer.echo("  (none)")


@library_app.command("add")
def library_add(ctx: typer.Context, name: str,
                project: pathlib.Path = typer.Option(pathlib.Path("."), "--project", "-p")
                ) -> None:
    """Add a library agent to [team] extra_agents; it installs on the next sync."""
    typer.echo(_guarded(LibraryService(LibraryLoader(ctx.obj)).add, project, name))


@library_app.command("remove")
def library_remove(ctx: typer.Context, name: str,
                   project: pathlib.Path = typer.Option(pathlib.Path("."), "--project", "-p")
                   ) -> None:
    """Remove a library agent from [team]; deletes the install unless locally modified."""
    typer.echo(_guarded(LibraryService(LibraryLoader(ctx.obj)).remove, project, name))


@library_app.command("new")
def library_new(ctx: typer.Context, kind: str, name: str) -> None:
    """Scaffold a new library entry: `servan library new agent <name>`."""
    service = LibraryService(LibraryLoader(ctx.obj))
    if kind != "agent":
        typer.secho(f"servan: unknown library kind '{kind}' — supported: agent",
                    fg="red", err=True)
        raise typer.Exit(2)
    path = _guarded(service.new_agent, name)
    typer.echo(f"created {path}")


@app.command()
def new(name: str, no_bd: bool = typer.Option(False, "--no-bd")) -> None:
    """Scaffold a new project from the servan template."""
    service = ScaffoldService(PackagedTemplateSource(), SubprocessRunner())
    target = _guarded(service.create, pathlib.Path(name), with_ledger=not no_bd)
    typer.echo(f"created {target}")


@app.command()
def status(project: pathlib.Path = typer.Option(pathlib.Path("."), "--project", "-p"),
           as_json: bool = typer.Option(False, "--json",
                                        help="Print the dashboard JSON snapshot; writes nothing.")) -> None:
    """Task ledger -> wiki/status.md (or --json stdout for dashboards)."""
    service = StatusService(BeadsLedger(project), SystemClock())
    if as_json:
        snapshot = _guarded(service.collect)
        typer.echo(snapshot.to_json(), nl=False)
        return
    target = _guarded(service.write, project)
    typer.echo(f"wrote {target}")


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
def council(ctx: typer.Context, spec: pathlib.Path,
            project: pathlib.Path = typer.Option(pathlib.Path("."), "--project", "-p")) -> None:
    """Run the Delphi consensus loop over a spec."""
    path, minutes, backend, team = _guarded(_run_council, ctx.obj, spec, project)
    typer.echo(f"{minutes.outcome}: {len(minutes.rounds)} round(s); minutes at {path}")
    if minutes.outcome == "escalated":
        question = _guarded(backend.boss_question, team["orchestrator"],
                            minutes.topic, minutes.unresolved)
        typer.secho(f"escalated to human: {question}", fg="yellow")
        raise typer.Exit(4)


def _run_council(config_dir: pathlib.Path | None, spec: pathlib.Path,
                 project: pathlib.Path) -> tuple[pathlib.Path, MeetingMinutes, VoterBackend, Team]:
    if not spec.is_file():
        raise ConfigError(f"spec not found: {spec}")
    loader = ConfigLoader(config_dir)
    config = loader.load_global()
    project_config = loader.load_project(project)
    if not project_config.council.enabled:
        raise ConfigError("council disabled in .servan.toml ([council].enabled = false)")
    team = TeamResolver(config).resolve(project_config)
    backend = _council_backend(config.council, team)
    minutes = CouncilEngine(backend, config.council, team).run(
        topic=spec.stem, proposal=spec.read_text(encoding="utf-8"))
    path = MinutesWriter(SystemClock()).write(project, minutes)
    return path, minutes, backend, team


def _council_backend(settings, team: Team) -> VoterBackend:
    roles = {*settings.voters, "architect", "orchestrator"} & team.keys()
    providers = {team[role].provider_name: team[role].provider for role in sorted(roles)}
    return DispatchVoterBackend(
        {name: _backend_for(name, provider) for name, provider in providers.items()})


def _backend_for(name: str, provider: ProviderConfig) -> VoterBackend:
    if provider.kind is ProviderKind.BUILTIN:
        raise ConfigError(
            f"provider '{name}' is builtin — council needs an openai-compatible endpoint")
    base_url = provider.base_url or ""
    if urllib.parse.urlparse(base_url).port == 11434:
        return OllamaVoterBackend(base_url.removesuffix("/v1"))
    return OpenAICompatibleVoterBackend(provider)


@app.command()
def canary(ctx: typer.Context, role: str, candidate: str,
           project: pathlib.Path = typer.Option(pathlib.Path("."), "--project", "-p")) -> None:
    """Golden-bead regression check before a model swap."""
    report = _guarded(_run_canary, ctx.obj, role, candidate, project)
    typer.echo(f"canary {report.role}:")
    typer.echo("| side | model | pass rate |")
    typer.echo("|---|---|---|")
    typer.echo(f"| incumbent | {report.incumbent} | {report.incumbent_pass_rate:.0%} |")
    typer.echo(f"| candidate | {report.candidate} | {report.candidate_pass_rate:.0%} |")
    if report.regressed:
        typer.secho(f"regression: {report.candidate} {report.candidate_pass_rate:.0%} "
                    f"< {report.incumbent} {report.incumbent_pass_rate:.0%}", fg="red")
        raise typer.Exit(5)


def _run_canary(config_dir: pathlib.Path | None, role: str, candidate: str,
                root: pathlib.Path) -> CanaryReport:
    loader = ConfigLoader(config_dir)
    runner = SubprocessRunner()
    service = CanaryRunner(loader.load_global(), OpenCodeTrial(runner), runner)
    return service.run(root, loader.load_project(root), role, candidate)


def _start_metrics(registry: MetricsRegistry, port: int) -> MetricsServer:
    """Bind + start the exporter; a taken port is a user-facing config error (exit 2)."""
    try:
        server = MetricsServer(registry, "127.0.0.1", port)
    except OSError as exc:
        raise WatchError(f"cannot bind metrics port {port} ({exc}) — "
                         "another servan watch already running?") from exc
    server.start()
    return server


@app.command()
def watch(ctx: typer.Context,
          project: pathlib.Path = typer.Option(pathlib.Path("."), "--project", "-p"),
          server: str = typer.Option("http://localhost:4096", "--server",
                                     help="OpenCode server base URL."),
          port: int = typer.Option(9105, "--port",
                                   help="Prometheus /metrics listen port."),
          once: bool = typer.Option(False, "--once", help="Single poll, print actions, exit.")) -> None:
    """Context warden daemon + Prometheus exporter (S-15)."""
    config = _guarded(lambda: ConfigLoader(ctx.obj).load_global())
    registry = MetricsRegistry()
    daemon = WatchDaemon(OpenCodeSessionSource(server, config.models),
                         ContextWarden(config.warden),
                         BeadsLedger(project), OpenCodeSessionControl(server),
                         metrics=registry)
    if once:
        actions = _guarded(daemon.poll_once)
        for action in actions:
            typer.echo(f"{action.kind.value}: {action.session_id} ({action.reason})")
        if not actions:
            typer.echo("no warden actions.")
        return
    metrics_server = _guarded(_start_metrics, registry, port)
    typer.echo(f"metrics on http://127.0.0.1:{metrics_server.port}/metrics")
    _log.info("watch daemon starting (server=%s)", server)
    try:
        _guarded(daemon.serve_forever)
    finally:
        metrics_server.stop()


@app.command()
def cost(ctx: typer.Context,
         server: str = typer.Option("http://localhost:4096", "--server",
                                    help="OpenCode server base URL.")) -> None:
    """Cost accounting: live session usage x prices.toml, per project/role/model."""
    config = _guarded(lambda: ConfigLoader(ctx.obj).load_global())
    source = OpenCodeSessionSource(server, config.models)
    lines = _guarded(lambda: summarize(source.sessions(), config.prices))
    if not config.prices:
        typer.secho("servan: no prices.toml — every model shows n/a; "
                    "add [prices.<alias>] input_per_m/output_per_m (shadow prices for local)",
                    fg="yellow", err=True)
    typer.echo(f"{'project':<20} {'role':<14} {'model':<16} {'sess':>4} "
               f"{'tokens in/out/cached':>24} {'cost USD':>10}")
    total = 0.0
    for line in lines:
        tokens = f"{line.tokens_in}/{line.tokens_out}/{line.tokens_cached}"
        typer.echo(f"{line.project:<20.20} {line.role:<14.14} {line.model_alias:<16.16} "
                   f"{line.sessions:>4} {tokens:>24} "
                   f"{f'{line.cost:.4f}' if line.cost is not None else 'n/a':>10}")
        total += line.cost or 0.0
    typer.echo(f"{'total':<20} {'':<14} {'':<16} {sum(l.sessions for l in lines):>4} "
               f"{'':>24} {total:>10.4f}")
