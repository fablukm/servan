"""Seams. Every external dependency of a service is one of these protocols,
injected through the constructor; concrete adapters live in `infrastructure`
or next to their service. Tests substitute doubles; the composition root
(`cli`) wires the real graph.
"""
from __future__ import annotations

from collections.abc import Mapping
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


class ModelBackend(Protocol):
    """One JSON-schema-constrained completion; the council's only model seam."""
    def complete_json(self, binding: ModelBinding, system: str,
                      prompt: str, schema: Mapping) -> dict: ...
