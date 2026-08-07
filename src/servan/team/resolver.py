"""TeamResolver — profile + project overrides -> {role: ResolvedModel}."""
from __future__ import annotations

from ..config.errors import ConfigError
from ..config.global_config import GlobalConfig
from ..config.project_config import ProjectConfig
from ..logging_setup import get_logger
from .resolved_model import ResolvedModel

_log = get_logger("team.resolver")

Team = dict[str, ResolvedModel]


class TeamResolver:
    def __init__(self, config: GlobalConfig) -> None:
        self._config = config

    def resolve(self, project: ProjectConfig) -> Team:
        try:
            roles: dict[str, str] = dict(self._config.profiles[project.profile])
        except KeyError as exc:
            raise ConfigError(
                f"unknown profile '{project.profile}' — defined: {sorted(self._config.profiles)}"
            ) from exc
        roles.update(project.roles)

        team: Team = {}
        for role, alias in roles.items():
            spec = self._config.models.get(alias)
            if spec is None:
                raise ConfigError(f"role '{role}': model alias '{alias}' not in models.toml")
            team[role] = ResolvedModel.from_spec(alias, spec, self._config.providers[spec.provider])
        if "orchestrator" not in team:
            raise ConfigError(f"profile '{project.profile}' defines no 'orchestrator' role")
        _log.info("resolved team for profile '%s': %d roles", project.profile, len(team))
        return team
