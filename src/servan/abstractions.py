"""Shared seams. Every external dependency of a service is a protocol like these,
injected through the constructor; concrete adapters live in `infrastructure`
or next to their service. Tests substitute doubles; the composition root
(`cli`) wires the real graph. Service-specific seams live package-locally
(`ledger.TaskLedger`, `observability.SessionSource`, …).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol


class ProcessRunner(Protocol):
    """Wrapper over subprocess so services never touch `subprocess` directly."""
    def run(self, *argv: str, cwd: Path | None = None) -> str: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
