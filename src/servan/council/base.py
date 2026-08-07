"""VoterBackend ABC — one file per backend implementation next to this."""
from __future__ import annotations

import abc

from ..team.resolved_model import ResolvedModel
from .vote import Vote


class VoterBackend(abc.ABC):
    @abc.abstractmethod
    def vote(self, voter: ResolvedModel, agent: str, lane: str,
             proposal: str, objection_digest: str | None) -> Vote:
        """Round-1 calls pass objection_digest=None (independent, anonymized voting)."""

    @abc.abstractmethod
    def revise(self, editor: ResolvedModel, proposal: str, blocking_digest: str) -> str:
        """Single-editor revision between rounds; returns the revised proposal text."""
