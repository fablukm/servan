"""StandardsLoader — reads standards/<name>.toml, resolves `extends` depth-first, merges."""
from __future__ import annotations

import pathlib
import tomllib
from collections.abc import Iterable

from pydantic import ValidationError

from ..logging_setup import get_logger
from .errors import ConfigError
from .loader import SCHEMA_VERSION, _summarize
from .standards_set import StandardsSet

_log = get_logger("config.standards")


class StandardsLoader:
    def __init__(self, standards_dir: pathlib.Path) -> None:
        self._dir = standards_dir

    def available(self) -> list[str]:
        if not self._dir.is_dir():
            return []
        return sorted(path.stem for path in self._dir.glob("*.toml"))

    def load_all(self, names: Iterable[str]) -> StandardsSet:
        """Merge a project's standards list left -> right (later wins)."""
        merged: StandardsSet | None = None
        for name in names:
            standard = self.load(name)
            merged = standard if merged is None else standard.merged_over(merged)
        if merged is None:
            raise ConfigError("no standards named")
        return merged

    def load(self, name: str) -> StandardsSet:
        return self._resolve(name, ())

    def _resolve(self, name: str, chain: tuple[str, ...]) -> StandardsSet:
        if name in chain:
            raise ConfigError(f"standards cycle: {' -> '.join((*chain, name))}")
        path = self._dir / f"{name}.toml"
        if not path.is_file():
            raise ConfigError(f"unknown standard '{name}' — expected {path} "
                              f"(available: {', '.join(self.available()) or 'none'})")
        try:
            with open(path, "rb") as fh:
                data = tomllib.load(fh)
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"invalid TOML in {path}: {exc}") from exc
        if data.pop("schema", None) != SCHEMA_VERSION:
            raise ConfigError(f"{path}: schema != {SCHEMA_VERSION}")
        meta = data.pop("meta", {})
        if not isinstance(meta, dict):
            raise ConfigError(f"{path}: [meta] must be a table")
        try:
            standard = StandardsSet.model_validate({
                "name": data.pop("name", name), "extends": data.pop("extends", []),
                "description": meta.get("description", ""), "sections": data})
        except ValidationError as exc:
            raise ConfigError(f"{path}: {_summarize(exc)}") from exc
        for parent in standard.extends:
            standard = standard.merged_over(self._resolve(parent, (*chain, name)))
        _log.info("loaded standard '%s' (%d sections)", name, len(standard.sections))
        return standard
