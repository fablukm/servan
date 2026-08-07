"""RepoTemplateSource — ships `template/` from the repo root (wheel data = S-11)."""
from __future__ import annotations

import shutil
from pathlib import Path

from .base import ScaffoldError, TemplateSource


class RepoTemplateSource(TemplateSource):
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[3] / "template"

    def copy_tree(self, target: Path) -> None:
        if not self.root.is_dir():
            raise ScaffoldError(f"template directory not found: {self.root}")
        shutil.copytree(self.root, target, dirs_exist_ok=True)
