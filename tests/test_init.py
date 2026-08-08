"""S-19 `servan init` — non-destructive brownfield scaffold: copies only missing template
files, AGENTS.md -> AGENTS.servan.md, .gitignore marker-append, bd init when absent,
core.hooksPath, --dry-run/--scan; idempotent; refuses non-git repos."""
import pathlib
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from servan.cli.app import app
from servan.errors import ProcessError
from servan.scaffold import InitService, PackagedTemplateSource, ScaffoldError
from servan.survey import SurveyCollector

TEMPLATE_FILES = PackagedTemplateSource().read_files()


class FakeClock:
    def now(self):
        return datetime(2026, 8, 8, tzinfo=UTC)


class FakeRunner:
    """Records calls; git config hooksPath behaves like real git (unset -> error)."""

    def __init__(self, hookspath: str | None = None):
        self.calls: list[tuple[str, ...]] = []
        self._hookspath = hookspath

    def run(self, *argv: str, cwd: pathlib.Path | None = None) -> str:
        self.calls.append(argv)
        if argv[:2] == ("git", "config") and len(argv) == 3:      # read
            if self._hookspath is None:
                raise ProcessError("unset")
            return self._hookspath
        if argv[:2] == ("git", "config"):                         # write
            self._hookspath = argv[3] + "\n"
            return ""
        if argv[0] == "bd":
            return ""
        raise ProcessError(f"unexpected argv: {argv}")            # -> survey walk fallback


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "legacy"
    (root / ".git").mkdir(parents=True)
    (root / "src").mkdir()
    (root / "src/app.py").write_text("print('legacy')\n")
    (root / "AGENTS.md").write_text("# our own agent rules\n")
    (root / ".gitignore").write_text("*.pyc\n")
    return root


def service(runner):
    return InitService(PackagedTemplateSource(), runner,
                       SurveyCollector(runner, FakeClock()))


def lines(plan):
    return [action.line for action in plan]


def test_refuses_when_not_a_git_repo(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(ScaffoldError, match="git init"):
        service(FakeRunner()).plan(plain)
    result = CliRunner().invoke(app, ["init", "-p", str(plain)])
    assert result.exit_code == 2


def test_copies_only_missing_and_never_overwrites(repo):
    runner = FakeRunner()
    plan = service(runner).apply(repo)
    assert (repo / "AGENTS.md").read_text() == "# our own agent rules\n"
    assert ("bd", "init", "--skip-agents") in runner.calls  # bd would edit AGENTS.md
    assert (repo / "AGENTS.servan.md").read_bytes() == TEMPLATE_FILES["AGENTS.md"]
    gitignore = (repo / ".gitignore").read_text()
    assert gitignore.startswith("*.pyc\n") and "# --- servan ---" in gitignore
    template_lines = [l for l in TEMPLATE_FILES[".gitignore"].decode().splitlines()
                      if l.strip() and not l.startswith("#")]
    assert all(line in gitignore.splitlines() for line in template_lines)
    assert (repo / "wiki/index.md").is_file() and (repo / ".servan.toml").is_file()
    assert (repo / ".githooks/pre-commit").is_file()
    assert any(a.kind == "append" and a.path == ".gitignore" for a in plan)
    assert any(a.kind == "create" and a.path == "AGENTS.servan.md" for a in plan)


def test_second_run_changes_nothing(repo):
    runner = FakeRunner()
    service(runner).apply(repo)
    (repo / ".beads").mkdir()                                # bd init's real effect
    snapshot = {p.relative_to(repo): p.read_bytes()
                for p in repo.rglob("*") if p.is_file()}
    calls_before = len(runner.calls)
    plan = service(runner).apply(repo)
    assert all(a.kind == "keep" for a in plan)
    assert len(runner.calls) == calls_before + 1             # only the hooksPath read
    assert {p.relative_to(repo): p.read_bytes()
            for p in repo.rglob("*") if p.is_file()} == snapshot


def test_dry_run_writes_nothing_and_matches_real_report(repo):
    dry = lines(service(FakeRunner()).plan(repo))
    assert not (repo / "AGENTS.servan.md").exists()
    assert not (repo / "wiki").exists()
    real = lines(service(FakeRunner()).apply(repo))
    assert dry == real


def test_bd_init_skipped_when_beads_exist(repo):
    (repo / ".beads").mkdir()
    runner = FakeRunner()
    service(runner).apply(repo)
    assert all(argv[0] != "bd" for argv in runner.calls)


def test_existing_hookspath_is_kept(repo):
    runner = FakeRunner(hookspath="custom-hooks\n")
    plan = service(runner).apply(repo)
    assert not any(len(argv) == 4 for argv in runner.calls)  # never overwritten
    assert any("custom-hooks" in a.detail for a in plan)


def test_scan_also_runs_survey(repo):
    plan = service(FakeRunner()).apply(repo, scan=True)
    assert (repo / "raw/survey/inventory.md").is_file()
    assert (repo / "raw/survey/inventory.json").is_file()
    assert any("survey" in a.path for a in plan)
