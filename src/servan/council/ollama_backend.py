"""OllamaVoterBackend — native structured outputs (format=json_schema) via /api/chat."""
from __future__ import annotations

import json

from pydantic import ValidationError

from ..team.resolved_model import ResolvedModel
from . import http
from .base import CouncilError, VoterBackend
from .prompts import boss_messages, revise_messages, vote_messages
from .vote import Vote


class OllamaVoterBackend(VoterBackend):
    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        self._base_url = base_url.rstrip("/")

    def vote(self, voter: ResolvedModel, agent: str, lane: str,
             proposal: str, objection_digest: str | None) -> Vote:
        body = http.post_json(f"{self._base_url}/api/chat",
                              {"model": voter.model_id,
                               "messages": vote_messages(agent, lane, proposal, objection_digest),
                               "format": Vote.json_schema(), "stream": False})
        try:
            data = json.loads(body["message"]["content"])
            # agent/lane are forced from our side — never trust the model's self-report.
            return Vote.model_validate({**data, "agent": agent, "lane": lane})
        except (KeyError, TypeError, json.JSONDecodeError, ValidationError) as exc:
            raise CouncilError(
                f"ollama vote off-schema for {voter.qualified_id}: {exc}") from exc

    def revise(self, editor: ResolvedModel, proposal: str, blocking_digest: str) -> str:
        return self._text(editor.model_id, revise_messages(proposal, blocking_digest))

    def boss_question(self, boss: ResolvedModel, topic: str,
                      unresolved: tuple[str, ...]) -> str:
        return self._text(boss.model_id, boss_messages(topic, unresolved))

    def _text(self, model_id: str, messages: list[dict[str, str]]) -> str:
        body = http.post_json(f"{self._base_url}/api/chat",
                              {"model": model_id, "messages": messages, "stream": False})
        try:
            return body["message"]["content"].strip()
        except (KeyError, AttributeError) as exc:
            raise CouncilError(f"unexpected ollama response shape: {exc}") from exc
