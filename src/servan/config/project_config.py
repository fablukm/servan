"""ProjectConfig — instance layer (<repo>/.servan.toml)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ProjectCouncilConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = True


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile: str = "local-36gb"
    roles: dict[str, str] = {}
    council: ProjectCouncilConfig = ProjectCouncilConfig()
