"""PackagedTemplateSource — `template/` ships inside the wheel as package data,
resolved via importlib.resources (S-11)."""
from __future__ import annotations

import importlib.resources
import shutil
from pathlib import Path

from .base import ScaffoldError, TemplateSource

_PACKAGE = "servan"
_RESOURCE = "template"


class PackagedTemplateSource(TemplateSource):
    def copy_tree(self, target: Path) -> None:
        with self._root() as root:
            shutil.copytree(root, target, dirs_exist_ok=True)

    def read_files(self) -> dict[str, bytes]:
        with self._root() as root:
            return {path.relative_to(root).as_posix(): path.read_bytes()
                    for path in sorted(root.rglob("*")) if path.is_file()}

    @staticmethod
    def _root():
        resource = importlib.resources.files(_PACKAGE).joinpath(_RESOURCE)
        if not resource.is_dir():
            raise ScaffoldError(f"packaged template missing: {_PACKAGE}/{_RESOURCE}")
        return importlib.resources.as_file(resource)
