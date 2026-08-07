"""OpenAICompatibleVoterBackend — any provider speaking the OpenAI chat API."""
from __future__ import annotations

import json
import os

from pydantic import ValidationError

from ..config.errors import ConfigError
from ..config.provider import ProviderConfig
from ..team.resolved_model import ResolvedModel
from . import http
from .base import CouncilError, VoterBackend
from .prompts import boss_messages, revise_messages, vote_messages
from .vote import Vote


class OpenAICompatibleVoterBackend(VoterBackend):
    def __init__(self, provider: ProviderConfig) -> None:
        self._provider = provider

    def vote(self, voter: ResolvedModel, agent: str, lane: str,
             proposal: str, objection_digest: str | None) -> Vote:
        body = self._chat(voter.model_id,
                          vote_messages(agent, lane, proposal, objection_digest),
                          response_format={"type": "json_schema", "json_schema": {
                              "name": "vote", "strict": True, "schema": Vote.json_schema()}})
        try:
            data = json.loads(body["choices"][0]["message"]["content"])
            # agent/lane are forced from our side — never trust the model's self-report.
            return Vote.model_validate({**data, "agent": agent, "lane": lane})
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as exc:
            raise CouncilError(
                f"openai-compatible vote off-schema for {voter.qualified_id}: {exc}") from exc

    def revise(self, editor: ResolvedModel, proposal: str, blocking_digest: str) -> str:
        return self._text(editor.model_id, revise_messages(proposal, blocking_digest))

    def boss_question(self, boss: ResolvedModel, topic: str,
                      unresolved: tuple[str, ...]) -> str:
        return self._text(boss.model_id, boss_messages(topic, unresolved))

    def _text(self, model_id: str, messages: list[dict[str, str]]) -> str:
        body = self._chat(model_id, messages)
        try:
            return body["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, AttributeError) as exc:
            raise CouncilError(f"unexpected chat-completions response shape: {exc}") from exc

    def _chat(self, model_id: str, messages: list[dict[str, str]], **extra) -> dict:
        url = f"{(self._provider.base_url or '').rstrip('/')}/chat/completions"
        return http.post_json(url, {"model": model_id, "messages": messages, **extra},
                              headers=self._headers())

    def _headers(self) -> dict[str, str]:
        if self._provider.api_key_env:
            key = os.environ.get(self._provider.api_key_env, "")
            if not key:
                raise ConfigError(  # config/validation error -> exit 2
                    f"provider API key: env {self._provider.api_key_env} is not set")
            return {"Authorization": f"Bearer {key}"}
        if self._provider.api_key:
            return {"Authorization": f"Bearer {self._provider.api_key}"}
        return {}
