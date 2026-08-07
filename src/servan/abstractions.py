"""Seams. Every external dependency of a service is one of these protocols,
injected through the constructor; concrete adapters live in `infrastructure`
or next to their service. Tests substitute doubles; the composition root
(`cli`) wires the real graph.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from .settings import ModelBinding, ProjectSettings, Settings


class SettingsSource(Protocol):
    def load(self) -> Settings: ...


class ProjectSource(Protocol):
    def load(self, root: Path) -> ProjectSettings: ...


class ProcessRunner(Protocol):
    """Wrapper over subprocess so services never touch `subprocess` directly."""
    def run(self, *argv: str, cwd: Path | None = None) -> str: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class Ledger(Protocol):
    """The task ledger (Beads) as the services see it."""
    def ready(self) -> list[dict]: ...
    def by_status(self, status: str) -> list[dict]: ...
    def by_priority(self, priority: int) -> list[dict]: ...
    def annotate(self, bead_id: str, note: str) -> None: ...


class ModelBackend(Protocol):
    """One JSON-schema-constrained completion; the council's only model seam."""
    def complete_json(self, binding: ModelBinding, system: str,
                      prompt: str, schema: Mapping) -> dict: ...


@dataclass(frozen=True, slots=True)
class SessionSample:
    session_id: str
    role: str
    model_alias: str
    tokens_in_context: int
    tokens_in: int
    tokens_out: int
    tokens_cached: int


class SessionSource(Protocol):
    """Live sessions (OpenCode server API adapter implements this)."""
    def sessions(self) -> Iterable[SessionSample]: ...


class MetricsSink(Protocol):
    def emit(self, name: str, value: float, labels: Mapping[str, str]) -> None: ...
