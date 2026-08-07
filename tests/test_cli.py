"""S-05 CLI polish — --version, --config-dir, central exit-code table, sync --check."""
import json

from typer.testing import CliRunner

from servan import __version__
from servan.cli.app import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_config_dir_option(cfg_dir, project, monkeypatch):
    monkeypatch.delenv("SERVAN_CONFIG_DIR", raising=False)  # prove the flag, not env, is used
    result = runner.invoke(app, ["--config-dir", str(cfg_dir), "sync", "-p", str(project)])
    assert result.exit_code == 0, result.output
    payload = json.loads((project / "opencode.json").read_text())
    assert payload["model"] == "ollama/qwen3-coder:30b"


def test_sync_check_writes_nothing_and_exits_3_on_drift(cfg_dir, project):
    result = runner.invoke(app, ["sync", "-p", str(project), "--check"])
    assert result.exit_code == 3
    assert "drift" in result.output
    assert not (project / "opencode.json").exists()          # diff-only, no write


def test_sync_check_passes_after_sync(cfg_dir, project):
    assert runner.invoke(app, ["sync", "-p", str(project)]).exit_code == 0
    result = runner.invoke(app, ["sync", "-p", str(project), "--check"])
    assert result.exit_code == 0, result.output
    assert "in sync" in result.output


def test_sync_check_detects_agent_drift(cfg_dir, project):
    assert runner.invoke(app, ["sync", "-p", str(project)]).exit_code == 0
    agent = project / ".opencode/agent/engineer.md"
    agent.write_text(agent.read_text().replace("qwen3-coder:30b", "stale-model:1"))
    result = runner.invoke(app, ["sync", "-p", str(project), "--check"])
    assert result.exit_code == 3
    assert "engineer.md" in result.output


def test_config_error_exits_2(tmp_path, monkeypatch):
    monkeypatch.setenv("SERVAN_CONFIG_DIR", str(tmp_path))   # dir without any .toml layers
    result = runner.invoke(app, ["sync", "-p", str(tmp_path)])
    assert result.exit_code == 2
    assert "servan:" in result.output


def test_unexpected_error_exits_1(cfg_dir, project, monkeypatch):
    import importlib

    cli_module = importlib.import_module("servan.cli.app")

    def boom(self, root, *, check=False):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli_module.SyncService, "sync", boom)
    result = runner.invoke(app, ["sync", "-p", str(project)])
    assert result.exit_code == 1
    assert "unexpected error" in result.output
