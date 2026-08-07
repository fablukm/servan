import textwrap

import pytest


@pytest.fixture
def cfg_dir(tmp_path, monkeypatch):
    """Minimal valid three-layer config; SERVAN_CONFIG_DIR points at it."""
    d = tmp_path / "cfg"; d.mkdir()
    (d / "providers.toml").write_text(textwrap.dedent("""\
        schema = 1
        [providers.ollama]
        kind = "openai-compatible"
        base_url = "http://localhost:11434/v1"
        api_key_env = ""
        api_key = "ollama"
        [providers.anthropic]
        kind = "builtin"
    """))
    (d / "models.toml").write_text(textwrap.dedent("""\
        schema = 1
        [models]
        "local/coder" = { provider = "ollama", id = "qwen3-coder:30b" }
        "local/small" = { provider = "ollama", id = "qwen2.5-coder:7b" }
        "api/sonnet"  = { provider = "anthropic", id = "claude-sonnet-5" }
    """))
    (d / "profiles.toml").write_text(textwrap.dedent("""\
        schema = 1
        [profiles.test]
        orchestrator = "local/coder"
        engineer     = "local/coder"
        reviewer     = "local/small"
        [council]
        max_cycles = 2
        voters = ["engineer", "reviewer"]
    """))
    monkeypatch.setenv("SERVAN_CONFIG_DIR", str(d))
    return d

@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    (root / ".opencode/agent").mkdir(parents=True)
    (root / ".servan.toml").write_text('profile = "test"\n')
    (root / ".opencode/agent/engineer.md").write_text(
        "---\ndescription: x\nmode: subagent\nmodel: PLACEHOLDER\n---\nprompt\n")
    return root
