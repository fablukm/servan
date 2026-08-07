"""ContextWarden — checkpoint/reboot policy over live sessions (S-13). Pure decisions;
side effects (bd notes, session kill/respawn, /metrics serving) live in the watch daemon."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..config.warden_settings import WardenSettings
from .session import AgentSession


class WardenActionKind(str, Enum):
    NONE = "none"
    CHECKPOINT = "checkpoint"   # soft threshold: <=200-token progress note + wip: commit
    REBOOT = "reboot"           # hard threshold: kill; respawn with bead + note + wiki links


@dataclass(frozen=True, slots=True)
class WardenAction:
    session_id: str
    kind: WardenActionKind
    reason: str


class ContextWarden:
    def __init__(self, settings: WardenSettings) -> None:
        self._settings = settings

    def evaluate(self, sessions: list[AgentSession]) -> list[WardenAction]:
        """Pure threshold policy. Sessions without a known ctx are never touched."""
        actions: list[WardenAction] = []
        for session in sessions:
            fill = session.fill
            if fill is None:
                kind, reason = WardenActionKind.NONE, "ctx unknown — abstain"
            elif fill >= self._settings.hard:
                kind, reason = WardenActionKind.REBOOT, f"fill {fill:.0%} >= hard {self._settings.hard:.0%}"
            elif fill >= self._settings.soft:
                kind, reason = WardenActionKind.CHECKPOINT, f"fill {fill:.0%} >= soft {self._settings.soft:.0%}"
            else:
                kind, reason = WardenActionKind.NONE, f"fill {fill:.0%}"
            actions.append(WardenAction(session_id=session.session_id, kind=kind, reason=reason))
        return actions
