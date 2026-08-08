"""LibraryLoader — enumerates the mother library (~/.config/servan/library/)."""
from __future__ import annotations

import os
import pathlib

from ..config.errors import ConfigError
from ..config.loader import ConfigLoader
from ..logging_setup import get_logger

_log = get_logger("library.loader")


class LibraryLoader:
    def __init__(self, config_dir: pathlib.Path | None = None) -> None:
        override = os.environ.get("SERVAN_LIBRARY_DIR")
        self._dir = (pathlib.Path(override) if override
                     else ConfigLoader(config_dir).config_dir / "library")

    @property
    def library_dir(self) -> pathlib.Path:
        return self._dir

    def agents(self) -> dict[str, pathlib.Path]:
        folder = self._dir / "agents"
        if not folder.is_dir():
            return {}
        return {path.stem: path for path in sorted(folder.glob("*.md"))}

    def skills(self) -> dict[str, pathlib.Path]:
        folder = self._dir / "skills"
        if not folder.is_dir():
            return {}
        return {path.name: path / "SKILL.md" for path in sorted(folder.iterdir())
                if (path / "SKILL.md").is_file()}

    def agent_source(self, name: str) -> str:
        agents = self.agents()
        if name not in agents:
            raise ConfigError(f"unknown library agent '{name}' — available: "
                              f"{', '.join(agents) or 'none'} ({self._dir / 'agents'})")
        return agents[name].read_text(encoding="utf-8")

    def skill_source_dir(self, name: str) -> pathlib.Path:
        skills = self.skills()
        if name not in skills:
            raise ConfigError(f"unknown library skill '{name}' — available: "
                              f"{', '.join(skills) or 'none'} ({self._dir / 'skills'})")
        return skills[name].parent
