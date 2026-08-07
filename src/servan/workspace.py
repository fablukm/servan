"""The project directory as an object: all path knowledge in one place."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Workspace:
    root: Path

    @property
    def agent_dir(self) -> Path:
        preferred = self.root / ".opencode/agent"       # official layout (singular)
        if preferred.is_dir():
            return preferred
        legacy = self.root / ".opencode/agents"          # tolerate legacy plural
        return legacy if legacy.is_dir() else preferred

    @property
    def opencode_config(self) -> Path:
        return self.root / "opencode.json"

    @property
    def project_toml(self) -> Path:
        return self.root / ".servan.toml"

    @property
    def wiki_dir(self) -> Path:
        return self.root / "wiki"

    @property
    def specs_dir(self) -> Path:
        return self.root / "specs"

    @property
    def status_page(self) -> Path:
        return self.wiki_dir / "status.md"
