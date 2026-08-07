"""S-08 — Ollama/OpenAI voter backends over a fake HTTP seam + the minutes writer."""
import json
from datetime import UTC, datetime

import pytest

from servan.config import ModelSpec, ProviderConfig
from servan.config.errors import ConfigError
from servan.council import (
    CouncilError,
    MeetingMinutes,
    MinutesWriter,
    OllamaVoterBackend,
    OpenAICompatibleVoterBackend,
    RoundRecord,
    Vote,
    http,
)
from servan.team import ResolvedModel

OLLAMA = ProviderConfig(kind="openai-compatible", base_url="http://localhost:11434/v1")
API = ProviderConfig(kind="openai-compatible", base_url="https://api.example.com/v1",
                     api_key_env="SERVAN_TEST_KEY")

VOTE_PAYLOAD = Vote(agent="SPOOFED", lane="spoofed", verdict="approve", blocking=False,
                    steelman_against="could be wrong", confidence=0.9).model_dump()


def _model(provider: ProviderConfig) -> ResolvedModel:
    return ResolvedModel.from_spec("alias/x", ModelSpec(provider="p", id="model-1"), provider)


def test_ollama_vote_uses_schema_and_forces_attribution(monkeypatch):
    sent = {}

    def fake_post(url, payload, headers=None, timeout=120):
        sent.update(url=url, payload=payload)
        return {"message": {"content": json.dumps(VOTE_PAYLOAD)}}

    monkeypatch.setattr(http, "post_json", fake_post)
    vote = OllamaVoterBackend().vote(_model(OLLAMA), "engineer", "feasibility", "spec", None)
    assert vote.agent == "engineer" and vote.lane == "feasibility"   # not the spoofed values
    assert sent["url"] == "http://localhost:11434/api/chat"
    assert sent["payload"]["model"] == "model-1"
    assert sent["payload"]["format"]["title"] == "Vote"              # Vote.json_schema()
    assert sent["payload"]["stream"] is False


def test_ollama_revise_and_boss_question(monkeypatch):
    monkeypatch.setattr(http, "post_json",
                        lambda url, payload, headers=None, timeout=120:
                        {"message": {"content": " revised text "}})
    backend = OllamaVoterBackend()
    assert backend.revise(_model(OLLAMA), "spec", "[R1] claim") == "revised text"
    assert backend.boss_question(_model(OLLAMA), "topic", ("claim",)) == "revised text"


def test_ollama_off_schema_response_fails_loud(monkeypatch):
    monkeypatch.setattr(http, "post_json",
                        lambda url, payload, headers=None, timeout=120:
                        {"message": {"content": "not json"}})
    with pytest.raises(CouncilError, match="off-schema"):
        OllamaVoterBackend().vote(_model(OLLAMA), "engineer", "feasibility", "spec", None)


def test_openai_vote_reads_key_from_env(monkeypatch):
    sent = {}
    monkeypatch.setenv("SERVAN_TEST_KEY", "sekret")

    def fake_post(url, payload, headers=None, timeout=120):
        sent.update(url=url, payload=payload, headers=headers)
        return {"choices": [{"message": {"content": json.dumps(VOTE_PAYLOAD)}}]}

    monkeypatch.setattr(http, "post_json", fake_post)
    vote = OpenAICompatibleVoterBackend(API).vote(_model(API), "reviewer",
                                                  "correctness-security", "spec", "digest")
    assert vote.agent == "reviewer"
    assert sent["url"] == "https://api.example.com/v1/chat/completions"
    assert sent["headers"]["Authorization"] == "Bearer sekret"
    assert sent["payload"]["response_format"]["json_schema"]["schema"]["title"] == "Vote"


def test_openai_missing_key_env_fails_loud(monkeypatch):
    monkeypatch.delenv("SERVAN_TEST_KEY", raising=False)
    with pytest.raises(ConfigError, match="SERVAN_TEST_KEY"):  # config error -> exit 2
        OpenAICompatibleVoterBackend(API).vote(_model(API), "reviewer", "lane", "spec", None)


class _FixedClock:
    def now(self):
        return datetime(2026, 8, 7, 9, 30, tzinfo=UTC)


def test_minutes_writer(tmp_path):
    vote = Vote(agent="reviewer", lane="correctness-security", verdict="object", blocking=True,
                objections=({"id": "R1", "claim": "race condition", "severity": "must",
                             "evidence": "spec §3"},),
                steelman_against="it might be fine", confidence=0.7)
    minutes = MeetingMinutes(topic="Rate Limiter", outcome="escalated",
                             rounds=(RoundRecord(number=1, proposal_hash="abc123def456",
                                                 votes=(vote,)),),
                             unresolved=("race condition",))
    path = MinutesWriter(_FixedClock()).write(tmp_path, minutes)
    assert path == tmp_path / "wiki" / "meetings" / "2026-08-07-rate-limiter.md"
    text = path.read_text()
    assert "type: meeting" in text
    assert "proposal `abc123def456`" in text
    assert "| reviewer | correctness-security | object | yes | 0.70 |" in text
    assert "race condition" in text and "spec §3" in text      # dissent preserved
