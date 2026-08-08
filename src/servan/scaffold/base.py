"""TemplateSource seam — where scaffold content comes from — + scaffold error type."""
from __future__ import annotations

import abc
from pathlib import Path


class ScaffoldError(Exception):
    """Unusable target, missing template, or failed scaffold step. Message is user-facing."""


class TemplateSource(abc.ABC):
    @abc.abstractmethod
    def copy_tree(self, target: Path) -> None:
        """Copy the full template tree into `target` (which may not exist yet)."""

    @abc.abstractmethod
    def read_files(self) -> dict[str, bytes]:
        """All template files as {posix relpath: content} — for non-destructive init."""
