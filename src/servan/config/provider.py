"""ProviderConfig — transport layer entry (providers.toml)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator


class ProviderKind(str, Enum):
    BUILTIN = "builtin"
    OPENAI_COMPATIBLE = "openai-compatible"


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ProviderKind
    base_url: str | None = None
    api_key_env: str = ""
    api_key: str = ""

    @model_validator(mode="after")
    def _require_base_url(self) -> ProviderConfig:
        if self.kind is ProviderKind.OPENAI_COMPATIBLE and not self.base_url:
            raise ValueError("openai-compatible provider requires base_url")
        return self
