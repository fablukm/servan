"""WardenSettings — policy layer (profiles.toml [warden]); see DESIGN.md `watch` contract."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WardenSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    soft: float = Field(default=0.70, gt=0, lt=1, description="checkpoint threshold (context fill)")
    hard: float = Field(default=0.85, gt=0, lt=1, description="kill+respawn threshold")
    recycle_beads: int = Field(default=10, ge=1, description="orchestrator session recycling")
