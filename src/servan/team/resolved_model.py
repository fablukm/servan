"""ResolvedModel — immutable value object: a role's alias resolved through the config layers."""
from __future__ import annotations

from dataclasses import dataclass

from ..config.model_spec import ModelSpec
from ..config.provider import ProviderConfig


@dataclass(frozen=True, slots=True)
class ResolvedModel:
    alias: str
    provider_name: str
    provider: ProviderConfig
    model_id: str
    ctx: int | None

    @property
    def qualified_id(self) -> str:
        """The `provider/model` string OpenCode expects."""
        return f"{self.provider_name}/{self.model_id}"

    @classmethod
    def from_spec(cls, alias: str, spec: ModelSpec, provider: ProviderConfig) -> "ResolvedModel":
        return cls(alias=alias, provider_name=spec.provider, provider=provider,
                   model_id=spec.id, ctx=spec.ctx)
