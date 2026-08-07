"""WatchDaemon — poll sessions, evaluate the pure ContextWarden, apply the
side effects (S-13): checkpoint -> bd note on the claimed bead; reboot ->
kill+respawn via SessionControl. One poll is one atomic, testable unit."""
from __future__ import annotations

import time

from ..ledger.base import TaskLedger, TaskStatus
from ..logging_setup import get_logger
from .base import SessionControl, SessionSource
from .metrics import MetricsRegistry
from .session import AgentSession
from .warden import ContextWarden, WardenAction, WardenActionKind

_log = get_logger("watch.daemon")

_CHECKPOINT_NOTE = ("warden checkpoint request ({reason}) — write a ≤200-token progress "
                    "note on this bead and commit as `wip:`")
_REBOOT_NOTE = "warden reboot ({reason}) — respawn with bead + this note + linked wiki pages only"


class WatchDaemon:
    def __init__(self, source: SessionSource, warden: ContextWarden,
                 ledger: TaskLedger, control: SessionControl,
                 poll_seconds: float = 5.0,
                 metrics: MetricsRegistry | None = None) -> None:
        self._source = source
        self._warden = warden
        self._ledger = ledger
        self._control = control
        self._poll_seconds = poll_seconds
        self._metrics = metrics

    def poll_once(self) -> list[WardenAction]:
        """One poll: evaluate all sessions, apply side effects, return the actions taken."""
        sessions = list(self._source.sessions())
        if self._metrics is not None:
            self._emit(sessions)
        by_id = {session.session_id: session for session in sessions}
        applied: list[WardenAction] = []
        for action in self._warden.evaluate(sessions):
            session = by_id[action.session_id]
            if action.kind is WardenActionKind.CHECKPOINT and self._checkpoint(session, action):
                applied.append(action)
            elif action.kind is WardenActionKind.REBOOT:
                self._control.respawn(session, _REBOOT_NOTE.format(reason=action.reason))
                applied.append(action)
        return applied

    def serve_forever(self) -> None:
        while True:
            self.poll_once()
            time.sleep(self._poll_seconds)

    def _emit(self, sessions: list[AgentSession]) -> None:
        """DESIGN.md label contract: {project,role,model,provider} per session."""
        metrics = self._metrics
        assert metrics is not None
        for session in sessions:
            labels = {"project": session.directory or "unknown",
                      "role": session.role or "unknown",
                      "model": session.model_alias or "unknown",
                      "provider": session.provider_id or "unknown"}
            metrics.set("servan_sessions_active", 1, labels)
            metrics.set("servan_cost_usd_total", session.cost, labels)
            for kind, value in (("input", session.tokens_in),
                                ("output", session.tokens_out),
                                ("cached", session.tokens_cached)):
                metrics.set("servan_tokens_total", value, {"kind": kind, **labels})
            if session.fill is not None:
                metrics.set("servan_context_fill_ratio", session.fill, labels)
        for status in TaskStatus:
            metrics.set("servan_beads", len(self._ledger.list(status=status)),
                        {"status": status.value})

    def _checkpoint(self, session: AgentSession, action: WardenAction) -> bool:
        if session.bead_id is None:
            _log.warning("checkpoint skipped for %s — no claimed bead", session.session_id)
            return False
        self._ledger.annotate(session.bead_id, _CHECKPOINT_NOTE.format(reason=action.reason))
        return True
