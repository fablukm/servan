"""TaskLedger ABC + task value types. Backend-agnostic view of the episodic memory."""
from __future__ import annotations

import abc
from enum import Enum

from pydantic import BaseModel, ConfigDict


class LedgerError(Exception):
    """Ledger backend unavailable or a command failed. Message is user-facing."""


class TaskStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    CLOSED = "closed"


class TaskRecord(BaseModel):
    """One task. extra='allow' because backend JSON shapes evolve (verify: `bd prime`)."""
    model_config = ConfigDict(extra="allow", frozen=True)

    id: str
    title: str = ""
    status: str = ""
    priority: int | None = None
    assignee: str | None = None


class TaskLedger(abc.ABC):
    @abc.abstractmethod
    def probe(self) -> None:
        """Fail fast (LedgerError) if the backend is missing or its CLI drifted."""

    @abc.abstractmethod
    def ready(self) -> list[TaskRecord]: ...

    @abc.abstractmethod
    def list(self, status: TaskStatus | None = None, priority: int | None = None) -> list[TaskRecord]: ...

    @abc.abstractmethod
    def claim(self, task_id: str) -> None: ...

    @abc.abstractmethod
    def close(self, task_id: str, reason: str) -> None: ...
