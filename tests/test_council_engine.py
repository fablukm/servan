"""CouncilEngine is deterministic and testable with a fake backend (no LLM)."""
from servan.config import CouncilSettings
from servan.council import CouncilEngine, Objection, Vote, VoterBackend


class _FakeBackend(VoterBackend):
    def __init__(self, object_rounds: int) -> None:
        self._object_rounds = object_rounds
        self._round = 0
        self.revisions = 0

    def vote(self, voter, agent, lane, proposal, objection_digest):
        objecting = self._round < self._object_rounds and agent == "reviewer"
        return Vote(
            agent=agent, lane=lane,
            verdict="object" if objecting else "approve",
            blocking=objecting,
            objections=(Objection(id="R1", claim="race condition", severity="must",
                                  evidence="spec §3"),) if objecting else (),
            steelman_against="n/a", confidence=0.8,
        )

    def revise(self, editor, proposal, blocking_digest):
        self._round += 1
        self.revisions += 1
        return proposal + f"\n<!-- revision {self.revisions} -->"

    def boss_question(self, boss, topic, unresolved):
        return "boss question"


def _team():
    from servan.config import ModelSpec, ProviderConfig
    from servan.team import ResolvedModel
    provider = ProviderConfig(kind="openai-compatible", base_url="http://x")
    make = lambda a: ResolvedModel.from_spec(a, ModelSpec(provider="p", id=a), provider)
    return {name: make(name) for name in ("engineer", "tester", "reviewer", "librarian", "architect")}


def test_consensus_first_round():
    minutes = CouncilEngine(_FakeBackend(0), CouncilSettings(), _team()).run("t", "proposal")
    assert minutes.outcome == "consensus" and len(minutes.rounds) == 1


def test_revision_then_consensus():
    backend = _FakeBackend(1)
    minutes = CouncilEngine(backend, CouncilSettings(), _team()).run("t", "proposal")
    assert minutes.outcome == "consensus" and len(minutes.rounds) == 2 and backend.revisions == 1


def test_deadlock_escalates_with_dissent_preserved():
    minutes = CouncilEngine(_FakeBackend(99), CouncilSettings(), _team()).run("t", "proposal")
    assert minutes.outcome == "escalated"
    assert minutes.unresolved == ("race condition",)
