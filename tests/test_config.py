import pytest

from servan.config import ConfigError, ConfigLoader


def test_load_merge(cfg_dir):
    cfg = ConfigLoader().load_global()
    assert set(cfg.models) == {"local/coder", "local/small", "api/sonnet"}
    assert cfg.council.max_cycles == 2
    assert cfg.warden.soft == 0.70  # defaults kick in without a [warden] table


def test_unknown_profile(cfg_dir, project):
    from servan.config import ProjectConfig
    from servan.team import TeamResolver
    cfg = ConfigLoader().load_global()
    with pytest.raises(ConfigError, match="unknown profile"):
        TeamResolver(cfg).resolve(ProjectConfig(profile="nope"))


def test_cross_validation_unknown_provider(cfg_dir):
    models = cfg_dir / "models.toml"
    models.write_text(models.read_text().replace('provider = "ollama"', 'provider = "ghost"', 1))
    with pytest.raises(ConfigError, match="unknown provider"):
        ConfigLoader().load_global()


def test_missing_layer(cfg_dir):
    (cfg_dir / "models.toml").unlink()
    with pytest.raises(ConfigError, match="missing"):
        ConfigLoader().load_global()


def test_schema_guard(cfg_dir):
    path = cfg_dir / "providers.toml"
    path.write_text(path.read_text().replace("schema = 1", "schema = 2"))
    with pytest.raises(ConfigError, match="schema"):
        ConfigLoader().load_global()


def test_openai_compatible_requires_base_url(cfg_dir):
    path = cfg_dir / "providers.toml"
    path.write_text(path.read_text().replace('base_url = "http://localhost:11434/v1"\n', ""))
    with pytest.raises(ConfigError, match="base_url"):
        ConfigLoader().load_global()
