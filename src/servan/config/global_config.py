"""GlobalConfig — the merged, validated union of all global TOML layers."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .council_settings import CouncilSettings
from .errors import ConfigError
from .model_spec import ModelSpec
from .price import ModelPrice
from .provider import ProviderConfig
from .warden_settings import WardenSettings


class GlobalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    providers: dict[str, ProviderConfig]
    models: dict[str, ModelSpec]
    profiles: dict[str, dict[str, str]]
    council: CouncilSettings = CouncilSettings()
    warden: WardenSettings = WardenSettings()
    prices: dict[str, ModelPrice] = {}

    def cross_validate(self) -> None:
        """Referential integrity across layers; raises ConfigError with actionable messages."""
        for alias, spec in self.models.items():
            if spec.provider not in self.providers:
                raise ConfigError(f"model '{alias}' references unknown provider '{spec.provider}'")
        for profile, roles in self.profiles.items():
            for role, alias in roles.items():
                if alias not in self.models:
                    raise ConfigError(
                        f"profile '{profile}' role '{role}': alias '{alias}' not in models.toml"
                    )
        for alias in self.prices:
            if alias not in self.models:
                raise ConfigError(f"prices.toml entry '{alias}' not in models.toml")
