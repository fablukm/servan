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
        resource = importlib.resources.files(_PACKAGE).joinpath(_RESOURCE)
        if not resource.is_dir():
            raise ScaffoldError(f"packaged template missing: {_PACKAGE}/{_RESOURCE}")
        with importlib.resources.as_file(resource) as root:
            shutil.copytree(root, target, dirs_exist_ok=True)
