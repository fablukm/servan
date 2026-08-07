"""Watch seams — SessionSource / SessionControl ABCs + WatchError (S-13).
Package-local, matching the scaffold/ledger/council convention."""
from __future__ import annotations

import abc

from ..errors import ServanError
from .session import AgentSession


class WatchError(ServanError):
    """OpenCode server unreachable, unexpected payload shape, or failed warden side effect."""
    exit_code = 2


class SessionSource(abc.ABC):
    @abc.abstractmethod
    def sessions(self) -> list[AgentSession]:
        """All live agent sessions as one snapshot."""


class SessionControl(abc.ABC):
    @abc.abstractmethod
    def respawn(self, session: AgentSession, note: str) -> None:
        """Kill the session; respawn its role with bead + note + linked wiki pages only."""
