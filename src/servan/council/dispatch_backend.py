"""DispatchVoterBackend — routes each call to the backend of the model's provider.
Council roles may mix providers (local voters, API boss); composition root builds the map."""
from __future__ import annotations

from ..team.resolved_model import ResolvedModel
from .base import VoterBackend
from .vote import Vote


class DispatchVoterBackend(VoterBackend):
    def __init__(self, backends: dict[str, VoterBackend]) -> None:
        self._backends = dict(backends)

    def vote(self, voter: ResolvedModel, agent: str, lane: str,
             proposal: str, objection_digest: str | None) -> Vote:
        return self._for(voter.provider_name).vote(voter, agent, lane, proposal,
                                                   objection_digest)

    def revise(self, editor: ResolvedModel, proposal: str, blocking_digest: str) -> str:
        return self._for(editor.provider_name).revise(editor, proposal, blocking_digest)

    def boss_question(self, boss: ResolvedModel, topic: str,
                      unresolved: tuple[str, ...]) -> str:
        return self._for(boss.provider_name).boss_question(boss, topic, unresolved)

    def _for(self, provider_name: str) -> VoterBackend:
        return self._backends[provider_name]
