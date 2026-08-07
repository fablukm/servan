"""MeetingMinutes — the persistent, dissent-preserving record written to wiki/meetings/."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .vote import Vote


class RoundRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    number: int
    proposal_hash: str
    votes: tuple[Vote, ...]


class MeetingMinutes(BaseModel):
    model_config = ConfigDict(frozen=True)

    topic: str
    rounds: tuple[RoundRecord, ...]
    outcome: Literal["consensus", "escalated", "human"]
    unresolved: tuple[str, ...] = ()  # preserved dissent / the boss's open question
