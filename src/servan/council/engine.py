"""CouncilEngine — the deterministic Delphi loop (docs/report §5.5). Backend-agnostic."""
from __future__ import annotations

import hashlib

from ..config.council_settings import CouncilSettings
from ..logging_setup import get_logger
from ..team.resolver import Team
from .base import VoterBackend
from .minutes import MeetingMinutes, RoundRecord
from .vote import Objection, Vote

_log = get_logger("council.engine")

# Lanes: a voter may BLOCK only in-lane; out-of-lane objections are recorded, non-blocking.
LANES: dict[str, str] = {
    "engineer": "feasibility",
    "tester": "testability",
    "reviewer": "correctness-security",
    "librarian": "consistency-with-wiki",
}


class CouncilEngine:
    def __init__(self, backend: VoterBackend, settings: CouncilSettings, team: Team) -> None:
        self._backend = backend
        self._settings = settings
        self._team = team

    def run(self, topic: str, proposal: str) -> MeetingMinutes:
        rounds: list[RoundRecord] = []
        digest: str | None = None  # round 1: independent + anonymized
        for cycle in range(1, self._settings.max_cycles + 1):
            votes = tuple(
                self._backend.vote(self._team[name], name, LANES.get(name, "general"),
                                   proposal, digest)
                for name in self._settings.voters if name in self._team
            )
            rounds.append(RoundRecord(number=cycle, proposal_hash=_sha(proposal), votes=votes))
            blocking = _blocking_objections(votes)
            _log.info("council '%s' round %d: %d blocking objections", topic, cycle, len(blocking))
            if not blocking:
                return MeetingMinutes(topic=topic, rounds=tuple(rounds), outcome="consensus")
            if cycle == self._settings.max_cycles:
                break
            digest = _digest(blocking)
            proposal = self._backend.revise(self._team["architect"], proposal, digest)
        unresolved = tuple(o.claim for o in _blocking_objections(rounds[-1].votes))
        return MeetingMinutes(topic=topic, rounds=tuple(rounds), outcome="escalated",
                              unresolved=unresolved)


def _blocking_objections(votes: tuple[Vote, ...]) -> list[Objection]:
    return [o for v in votes if v.blocking and v.lane == LANES.get(v.agent, "general")
            for o in v.objections if o.severity == "must"]


def _digest(objections: list[Objection]) -> str:
    return "\n".join(f"[{o.id}] {o.claim} (evidence: {o.evidence})" for o in objections)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]
