"""S-10 canary — golden beads in tasks/golden/, scratch worktrees, pass-rate compare,
exit 5 + table on regression."""
import importlib
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from servan.canary import CanaryRunner
from servan.canary.trial import BeadTrial
from servan.cli.app import app
from servan.config import GlobalConfig, ModelSpec, ProjectConfig, ProviderConfig
from servan.config.errors import ConfigError


def _config() -> GlobalConfig:
    provider = ProviderConfig(kind="openai-compatible", base_url="http://x")
    return GlobalConfig(
        providers={"ollama": provider},
        models={"local/coder": ModelSpec(provider="ollama", id="qwen3-coder:30b"),
                "local/new": ModelSpec(provider="ollama", id="qwen3-coder:14b")},
        profiles={"test": {"orchestrator": "local/coder", "engineer": "local/coder"}},
    )


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, ...], Path | None]] = []

    def run(self, *argv: str, cwd: Path | None = None) -> str:
        self.calls.append((argv, cwd))
        return ""


class FakeTrial(BeadTrial):
    """Models whose id is in `failing_ids` fail beads b2/b4; everyone else passes."""

    def __init__(self, failing_ids: set[str]) -> None:
        self._failing = failing_ids

    def trial(self, worktree, bead, model) -> bool:
        return not (model.model_id in self._failing and bead.stem in {"b2", "b4"})


def _beads(root: Path, names=("b1", "b2", "b3", "b4")) -> None:
    golden = root / "tasks" / "golden"
    golden.mkdir(parents=True)
    for name in names:
        (golden / f"{name}.md").write_text(f"# {name}\n\ndo the thing\n")


def test_pass_rates_and_worktree_isolation(tmp_path):
    _beads(tmp_path)
    runner = FakeRunner()
    report = CanaryRunner(_config(), FakeTrial({"qwen3-coder:14b"}), runner).run(
        tmp_path, ProjectConfig(profile="test"), "engineer", "local/new")
    assert report.incumbent == "local/coder" and report.candidate == "local/new"
    assert report.incumbent_pass_rate == 1.0
    assert report.candidate_pass_rate == 0.5
    assert report.regressed
    adds = [argv for argv, _ in runner.calls if argv[:3] == ("git", "worktree", "add")]
    prunes = [argv for argv, _ in runner.calls if argv[:3] == ("git", "worktree", "prune")]
    assert len(adds) == 2 and len(prunes) == 2            # one scratch worktree per side
    assert all(cwd == tmp_path for _, cwd in runner.calls)
    assert all(not Path(argv[4]).exists() for argv in adds)  # scratch cleaned up


def test_unknown_candidate_alias_fails_loud(tmp_path):
    _beads(tmp_path)
    with pytest.raises(ConfigError, match="unknown model alias 'nope'"):
        CanaryRunner(_config(), FakeTrial(set()), FakeRunner()).run(
            tmp_path, ProjectConfig(profile="test"), "engineer", "nope")


def test_missing_golden_beads_fail_loud(tmp_path):
    with pytest.raises(ConfigError, match="golden beads"):
        CanaryRunner(_config(), FakeTrial(set()), FakeRunner()).run(
            tmp_path, ProjectConfig(profile="test"), "engineer", "local/new")


@pytest.fixture
def canary_env(tmp_path, monkeypatch):
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / "providers.toml").write_text(textwrap.dedent("""\
        schema = 1
        [providers.ollama]
        kind = "openai-compatible"
        base_url = "http://localhost:11434/v1"
        api_key = "ollama"
    """))
    (cfg / "models.toml").write_text(textwrap.dedent("""\
        schema = 1
        [models]
        "local/coder" = { provider = "ollama", id = "qwen3-coder:30b" }
        "local/new"   = { provider = "ollama", id = "qwen3-coder:14b" }
    """))
    (cfg / "profiles.toml").write_text(textwrap.dedent("""\
        schema = 1
        [profiles.test]
        orchestrator = "local/coder"
        engineer     = "local/coder"
    """))
    monkeypatch.setenv("SERVAN_CONFIG_DIR", str(cfg))
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".servan.toml").write_text('profile = "test"\n')
    _beads(project)
    return project


def _patch_trial(monkeypatch, trial: BeadTrial) -> None:
    cli = importlib.import_module("servan.cli.app")
    monkeypatch.setattr(cli, "OpenCodeTrial", lambda runner: trial)
    monkeypatch.setattr(cli, "SubprocessRunner", FakeRunner)  # no real git in tmp projects


def test_regression_exit5_with_table(canary_env, monkeypatch):
    _patch_trial(monkeypatch, FakeTrial({"qwen3-coder:14b"}))
    result = CliRunner().invoke(app, ["canary", "engineer", "local/new", "-p", str(canary_env)])
    assert result.exit_code == 5
    assert "| incumbent | local/coder | 100% |" in result.output
    assert "| candidate | local/new | 50% |" in result.output
    assert "regression" in result.output


def test_no_regression_exit0(canary_env, monkeypatch):
    _patch_trial(monkeypatch, FakeTrial(set()))
    result = CliRunner().invoke(app, ["canary", "engineer", "local/new", "-p", str(canary_env)])
    assert result.exit_code == 0, result.output
    assert "| candidate | local/new | 100% |" in result.output
