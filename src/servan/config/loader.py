"""ConfigLoader — layered TOML -> validated pydantic config objects."""
from __future__ import annotations

import os
import pathlib
import tomllib
from typing import Any

from pydantic import ValidationError

from ..logging_setup import get_logger
from .errors import ConfigError
from .global_config import GlobalConfig
from .project_config import ProjectConfig

_log = get_logger("config.loader")

SCHEMA_VERSION = 1
REQUIRED_LAYERS: tuple[str, ...] = ("providers", "models", "profiles")
OPTIONAL_LAYERS: tuple[str, ...] = ("prices",)


class ConfigLoader:
    """Loads ~/.config/servan/*.toml (override: SERVAN_CONFIG_DIR) and <repo>/.servan.toml."""

    def __init__(self, config_dir: pathlib.Path | None = None) -> None:
        self._dir = config_dir or pathlib.Path(
            os.environ.get("SERVAN_CONFIG_DIR", pathlib.Path.home() / ".config/servan")
        )

    @property
    def config_dir(self) -> pathlib.Path:
        return self._dir

    def load_global(self) -> GlobalConfig:
        merged: dict[str, Any] = {}
        for layer in REQUIRED_LAYERS:
            merged.update(self._load_layer(self._dir / f"{layer}.toml", layer))
        for layer in OPTIONAL_LAYERS:
            path = self._dir / f"{layer}.toml"
            if path.exists():
                merged.update(self._load_layer(path, layer))
        try:
            cfg = GlobalConfig.model_validate(merged)
        except ValidationError as exc:
            raise ConfigError(_summarize(exc)) from exc
        cfg.cross_validate()
        _log.info("loaded global config from %s (%d models, %d profiles)",
                  self._dir, len(cfg.models), len(cfg.profiles))
        return cfg

    def load_project(self, root: pathlib.Path) -> ProjectConfig:
        path = root / ".servan.toml"
        if not path.exists():
            _log.info("no .servan.toml in %s — using defaults", root)
            return ProjectConfig()
        try:
            return ProjectConfig.model_validate(self._read_toml(path))
        except ValidationError as exc:
            raise ConfigError(f"{path}: {_summarize(exc)}") from exc

    def _load_layer(self, path: pathlib.Path, layer: str) -> dict[str, Any]:
        data = self._read_toml(path)
        if data.pop("schema", None) != SCHEMA_VERSION:
            raise ConfigError(f"{layer}.toml: schema != {SCHEMA_VERSION} — migrate per manual §9")
        if layer == "prices":
            data.pop("currency", None)  # informational for dashboards; not modeled yet
        return data

    @staticmethod
    def _read_toml(path: pathlib.Path) -> dict[str, Any]:
        try:
            with open(path, "rb") as fh:
                return tomllib.load(fh)
        except FileNotFoundError as exc:
            raise ConfigError(f"missing {path} — see setup manual §3") from exc
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"invalid TOML in {path}: {exc}") from exc


def _summarize(exc: ValidationError) -> str:
    first = exc.errors()[0]
    loc = ".".join(str(part) for part in first["loc"])
    return f"config invalid at '{loc}': {first['msg']}"
