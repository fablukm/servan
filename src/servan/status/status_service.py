"""StatusService — ledger -> wiki/status.md (S-04). Depends on the TaskLedger ABC only."""
from __future__ import annotations

import pathlib

from ..ledger.base import TaskLedger


class StatusService:
    def __init__(self, ledger: TaskLedger) -> None:
        self._ledger = ledger

    def write(self, root: pathlib.Path) -> pathlib.Path:
        """Render backlog(p4)/ready/in-flight/recently-closed into wiki/status.md (fenced,
        deterministic ordering; the only servan output allowed a timestamp)."""
        raise NotImplementedError("S-04 — see dev/BACKLOG.md")
