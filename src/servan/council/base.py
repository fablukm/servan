"""VoterBackend ABC — one file per backend implementation next to this."""
from __future__ import annotations

import abc

from ..errors import ServanError
from ..team.resolved_model import ResolvedModel
from .vote import Vote


class CouncilError(ServanError):
    """Backend unreachable, key missing, or response off-schema. Message is user-facing."""
    exit_code = 1


class VoterBackend(abc.ABC):
    @abc.abstractmethod
    def vote(self, voter: ResolvedModel, agent: str, lane: str,
             proposal: str, objection_digest: str | None) -> Vote:
        """Round-1 calls pass objection_digest=None (independent, anonymized voting)."""

    @abc.abstractmethod
    def revise(self, editor: ResolvedModel, proposal: str, blocking_digest: str) -> str:
        """Single-editor revision between rounds; returns the revised proposal text."""

    @abc.abstractmethod
    def boss_question(self, boss: ResolvedModel, topic: str,
                      unresolved: tuple[str, ...]) -> str:
        """Deadlock tie-break: formulate the single question a human must answer."""
