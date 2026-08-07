"""S-08 — CLI wiring: council SPEC.md -> minutes file; deadlock -> boss question + exit 4."""
import importlib
import textwrap

import pytest
from typer.testing import CliRunner

from servan.cli.app import app
from servan.council import Objection, Vote, VoterBackend


class FakeBackend(VoterBackend):
    """Objects (in-lane, must) while objecting is True; boss answers with a canned question."""

    def __init__(self, objecting: bool) -> None:
        self._objecting = objecting

    def vote(self, voter, agent, lane, proposal, objection_digest):
        blocking = self._objecting and agent == "reviewer"
        return Vote(agent=agent, lane=lane,
                    verdict="object" if blocking else "approve", blocking=blocking,
                    objections=(Objection(id="R1", claim="race condition", severity="must",
                                          evidence="spec §3"),) if blocking else (),
                    steelman_against="n/a", confidence=0.8)

    def revise(self, editor, proposal, blocking_digest):
        return proposal + "\n<!-- revised -->"

    def boss_question(self, boss, topic, unresolved):
        return "Which consistency guarantee does the spec promise?"


@pytest.fixture
def council_env(tmp_path, monkeypatch):
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
    """))
    (cfg / "profiles.toml").write_text(textwrap.dedent("""\
        schema = 1
        [profiles.test]
        orchestrator = "local/coder"
        architect    = "local/coder"
        engineer     = "local/coder"
        reviewer     = "local/coder"
        [council]
        max_cycles = 2
        voters = ["engineer", "reviewer"]
    """))
    monkeypatch.setenv("SERVAN_CONFIG_DIR", str(cfg))
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".servan.toml").write_text('profile = "test"\n')
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n\nBuild the thing.\n")
    return project, spec


def _patch_backend(monkeypatch, backend):
    cli = importlib.import_module("servan.cli.app")
    monkeypatch.setattr(cli, "_council_backend", lambda settings, team: backend)


def test_consensus_writes_minutes(council_env, monkeypatch):
    project, spec = council_env
    _patch_backend(monkeypatch, FakeBackend(objecting=False))
    result = CliRunner().invoke(app, ["council", str(spec), "-p", str(project)])
    assert result.exit_code == 0, result.output
    assert "consensus" in result.output
    minutes = list((project / "wiki" / "meetings").glob("*.md"))
    assert len(minutes) == 1


def test_deadlock_boss_question_exit4(council_env, monkeypatch):
    project, spec = council_env
    _patch_backend(monkeypatch, FakeBackend(objecting=True))
    result = CliRunner().invoke(app, ["council", str(spec), "-p", str(project)])
    assert result.exit_code == 4
    assert "Which consistency guarantee does the spec promise?" in result.output
    minutes = list((project / "wiki" / "meetings").glob("*.md"))
    assert len(minutes) == 1 and "race condition" in minutes[0].read_text()
