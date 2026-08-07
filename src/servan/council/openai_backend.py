"""OpenAICompatibleVoterBackend — any provider speaking the OpenAI chat API. S-08, second."""
from __future__ import annotations

from ..config.provider import ProviderConfig
from ..team.resolved_model import ResolvedModel
from .base import VoterBackend
from .vote import Vote


class OpenAICompatibleVoterBackend(VoterBackend):
    def __init__(self, provider: ProviderConfig) -> None:
        self._provider = provider

    def vote(self, voter: ResolvedModel, agent: str, lane: str,
             proposal: str, objection_digest: str | None) -> Vote:
        raise NotImplementedError("S-08 — see dev/BACKLOG.md")

    def revise(self, editor: ResolvedModel, proposal: str, blocking_digest: str) -> str:
        raise NotImplementedError("S-08 — see dev/BACKLOG.md")
