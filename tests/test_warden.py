"""ContextWarden's decision policy is pure — testable without any daemon."""
from servan.config import WardenSettings
from servan.observability import AgentSession, ContextWarden, WardenActionKind


def _session(tokens: int, ctx: int | None = 10_000) -> AgentSession:
    return AgentSession(session_id="s1", role="engineer", model_alias="local/coder",
                        tokens_in_context=tokens, ctx=ctx)


def test_thresholds():
    warden = ContextWarden(WardenSettings(soft=0.7, hard=0.85))
    kinds = [warden.evaluate([_session(t)])[0].kind for t in (1_000, 7_500, 9_000)]
    assert kinds == [WardenActionKind.NONE, WardenActionKind.CHECKPOINT, WardenActionKind.REBOOT]


def test_abstains_without_ctx():
    warden = ContextWarden(WardenSettings())
    action = warden.evaluate([_session(10**9, ctx=None)])[0]
    assert action.kind is WardenActionKind.NONE and "abstain" in action.reason
