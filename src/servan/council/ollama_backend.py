"""OllamaVoterBackend — native structured outputs (format=json_schema). S-08, implement first."""
from __future__ import annotations

from ..team.resolved_model import ResolvedModel
from .base import VoterBackend
from .vote import Vote


class OllamaVoterBackend(VoterBackend):
    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        self._base_url = base_url

    def vote(self, voter: ResolvedModel, agent: str, lane: str,
             proposal: str, objection_digest: str | None) -> Vote:
        raise NotImplementedError("S-08 — see dev/BACKLOG.md")

    def revise(self, editor: ResolvedModel, proposal: str, blocking_digest: str) -> str:
        raise NotImplementedError("S-08 — see dev/BACKLOG.md")
