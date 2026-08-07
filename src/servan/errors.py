"""Error hierarchy: one base, exit codes carried by the type (mapped centrally in cli)."""
from __future__ import annotations


class ServanError(Exception):
    """Base for all expected failures. `exit_code` is honored by the CLI guard."""
    exit_code: int = 1


class ConfigError(ServanError):
    """Invalid or inconsistent configuration. Message is user-facing."""
    exit_code = 2


class ProcessError(ServanError):
    """An external tool (git, bd, …) failed."""
    exit_code = 1


class NotYetImplemented(ServanError):
    """Declared surface without an implementation yet — points at the backlog task."""
    exit_code = 1

    def __init__(self, task: str) -> None:
        super().__init__(f"not implemented yet — {task} in dev/BACKLOG.md")
        self.task = task
