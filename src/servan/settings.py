"""Typed configuration model (options pattern).

Immutable dataclasses only; no I/O. Construction happens in `config` (the
repositories); everything downstream depends on these types, never on raw
TOML dicts. Resolution logic lives here because it is pure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .errors import ConfigError


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    name: str
    kind: str                       # "builtin" | "openai-compatible"
    base_url: str | None = None
    api_key_env: str | None = None
    api_key: str | None = None      # literal fallback (e.g. "ollama")


@dataclass(frozen=True, slots=True)
class ModelSpec:
    alias: str
    provider: str
    model_id: str
    ctx: int | None = None          # context window; the warden needs it


@dataclass(frozen=True, slots=True)
class ModelBinding:
    """A fully resolved assignment: provider spec + concrete model."""
    provider: ProviderSpec
    model: ModelSpec

    @property
    def qualified_id(self) -> str:
        return f"{self.provider.name}/{self.model.model_id}"


@dataclass(frozen=True, slots=True)
class PriceSpec:
    input_per_m: float
    output_per_m: float
    cached_per_m: float | None = None


@dataclass(frozen=True, slots=True)
class CouncilOptions:
    max_cycles: int = 2
    voters: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WardenOptions:
    soft: float = 0.70
    hard: float = 0.85
    recycle_beads: int = 10


@dataclass(frozen=True, slots=True)
class ProjectSettings:
    """The per-repo instance layer (.servan.toml)."""
    profile: str = "local-36gb"
    role_overrides: Mapping[str, str] = field(default_factory=dict)
    council_enabled: bool = True


@dataclass(frozen=True, slots=True)
class Settings:
    """Aggregate of the global layers. The single object services depend on."""
    providers: Mapping[str, ProviderSpec]
    models: Mapping[str, ModelSpec]
    profiles: Mapping[str, Mapping[str, str]]
    council: CouncilOptions = CouncilOptions()
    warden: WardenOptions = WardenOptions()
    prices: Mapping[str, PriceSpec] | None = None

    # -- resolution ---------------------------------------------------------
    def binding_for(self, alias: str) -> ModelBinding:
        model = self.models.get(alias)
        if model is None:
            raise ConfigError(f"model alias '{alias}' not in models.toml")
        provider = self.providers.get(model.provider)
        if provider is None:
            raise ConfigError(
                f"model '{alias}' references unknown provider '{model.provider}'")
        return ModelBinding(provider=provider, model=model)

    def roles_for(self, project: ProjectSettings) -> dict[str, str]:
        profile = self.profiles.get(project.profile)
        if profile is None:
            raise ConfigError(
                f"unknown profile '{project.profile}' — defined: {sorted(self.profiles)}")
        roles = dict(profile)
        roles.update(project.role_overrides)
        return roles

    def bindings_for(self, project: ProjectSettings) -> dict[str, ModelBinding]:
        """Resolve every role; raising here is the cross-layer validation."""
        return {role: self.binding_for(alias)
                for role, alias in self.roles_for(project).items()}
