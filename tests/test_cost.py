"""S-14 `servan cost` — pure, cached-aware cost accounting (usage x prices.toml)
and the CLI summary per project/role/model. No server in tests: sessions are faked."""
import sys

from typer.testing import CliRunner

from servan.cli import app
from servan.config import ModelPrice
from servan.observability import AgentSession
from servan.observability.base import SessionSource
from servan.observability.cost import session_cost, summarize


class FakeSource(SessionSource):
    def __init__(self, sessions): self._sessions = sessions
    def sessions(self): return self._sessions

PRICE = ModelPrice(input_per_m=2.0, output_per_m=10.0, cached_per_m=0.5)


def _session(project="proj", role="engineer", alias="api/sonnet", tokens_in=0,
             tokens_out=0, tokens_cached=0) -> AgentSession:
    return AgentSession(session_id="s", role=role, model_alias=alias, directory=project,
                        tokens_in_context=0, tokens_in=tokens_in, tokens_out=tokens_out,
                        tokens_cached=tokens_cached)


def test_session_cost_is_cached_aware():
    # cached tokens bill at cached_per_m, not input_per_m: (800k*2 + 200k*0.5 + 500k*10)/1M
    cost = session_cost(tokens_in=1_000_000, tokens_out=500_000,
                        tokens_cached=200_000, price=PRICE)
    assert cost == 6.7


def test_session_cost_without_cached_rate_bills_input_rate():
    price = ModelPrice(input_per_m=2.0, output_per_m=10.0)
    assert session_cost(tokens_in=1_000_000, tokens_out=0,
                        tokens_cached=400_000, price=price) == 2.0


def test_session_cost_without_price_is_none():
    assert session_cost(tokens_in=1, tokens_out=1, tokens_cached=0, price=None) is None


def test_summarize_groups_and_sorts_deterministically():
    sessions = [
        _session(project="b", tokens_in=1_000_000),
        _session(project="a", role="reviewer", tokens_in=1_000_000),
        _session(project="a", tokens_in=500_000),
        _session(project="a", tokens_in=500_000),   # same bucket as above -> merges
        _session(project="a", alias="local/coder", tokens_in=9_000_000),  # unpriced
    ]
    lines = summarize(sessions, {"api/sonnet": PRICE})
    assert [(line.project, line.role, line.model_alias) for line in lines] == [
        ("a", "engineer", "api/sonnet"), ("a", "engineer", "local/coder"),
        ("a", "reviewer", "api/sonnet"), ("b", "engineer", "api/sonnet"),
    ]
    merged = lines[0]
    assert merged.tokens_in == 1_000_000 and merged.sessions == 2
    assert merged.cost == 2.0                        # 1M input tokens @ 2/M
    assert lines[1].cost is None                     # unpriced model stays visible


def test_cli_cost_table(cfg_dir, monkeypatch):
    (cfg_dir / "prices.toml").write_text(
        'schema = 1\ncurrency = "USD"\n'
        '[prices."local/coder"]\ninput_per_m = 0.5\noutput_per_m = 2.0\ncached_per_m = 0.1\n')
    cli_module = sys.modules["servan.cli.app"]
    monkeypatch.setattr(cli_module, "OpenCodeSessionSource",
                        lambda base_url, models: FakeSource([
                            _session(alias="local/coder", tokens_in=2_000_000)]))
    result = CliRunner().invoke(app, ["cost", "--server", "http://unused"])
    assert result.exit_code == 0, result.output
    assert "local/coder" in result.output
    assert "1.0000" in result.output               # 2M input @ 0.5/M
    assert "total" in result.output


def test_cli_cost_fails_loud_when_server_down(cfg_dir):
    result = CliRunner().invoke(app, ["cost", "--server", "http://127.0.0.1:1"])
    assert result.exit_code == 2
    assert "opencode serve" in result.output
