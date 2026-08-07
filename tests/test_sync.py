import json

from servan.rendering import SyncService


def test_sync_renders_and_rewrites(cfg_dir, project):
    results = SyncService().sync(project)
    payload = json.loads((project / "opencode.json").read_text())
    assert payload["model"] == "ollama/qwen3-coder:30b"
    assert "ollama" in payload["provider"] and "anthropic" not in payload["provider"]
    assert payload["provider"]["ollama"]["options"]["apiKey"] == "ollama"  # literal dummy key
    agent = (project / ".opencode/agent/engineer.md").read_text()
    assert "model: ollama/qwen3-coder:30b" in agent
    assert any(r.summary.startswith("engineer ->") for r in results)


def test_project_override(cfg_dir, project):
    (project / ".servan.toml").write_text('profile = "test"\n[roles]\nengineer = "api/sonnet"\n')
    SyncService().sync(project)
    agent = (project / ".opencode/agent/engineer.md").read_text()
    assert "model: anthropic/claude-sonnet-5" in agent


def test_deterministic_output(cfg_dir, project):
    SyncService().sync(project)
    first = (project / "opencode.json").read_text()
    SyncService().sync(project)
    assert (project / "opencode.json").read_text() == first
