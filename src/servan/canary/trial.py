"""BeadTrial ABC — one golden-bead attempt by one model in a scratch worktree."""
from __future__ import annotations

import abc
from pathlib import Path

from ..team.resolved_model import ResolvedModel


class BeadTrial(abc.ABC):
    @abc.abstractmethod
    def trial(self, worktree: Path, bead: Path, model: ResolvedModel) -> bool:
        """True when the bead's check passes after the model worked the bead."""
