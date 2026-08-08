"""ProjectConfig — instance layer (<repo>/.servan.toml)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ProjectCouncilConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = True


class ProjectTeamConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    extra_agents: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile: str = "local-36gb"
    roles: dict[str, str] = {}
    standards: tuple[str, ...] = ()
    team: ProjectTeamConfig = ProjectTeamConfig()
    council: ProjectCouncilConfig = ProjectCouncilConfig()
