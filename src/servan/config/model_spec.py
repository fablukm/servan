"""ModelSpec — inventory layer entry (models.toml): alias -> provider/id (+ context size)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str
    id: str
    ctx: int | None = Field(default=None, ge=1024, description="context window; used by the warden")
