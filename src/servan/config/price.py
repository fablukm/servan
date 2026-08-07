"""ModelPrice — economics layer entry (prices.toml), USD per 1M tokens."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelPrice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    input_per_m: float = Field(ge=0)
    output_per_m: float = Field(ge=0)
    cached_per_m: float | None = Field(default=None, ge=0)
