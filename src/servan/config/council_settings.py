"""CouncilSettings — policy layer (profiles.toml [council])."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CouncilSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_cycles: int = Field(default=2, ge=1, le=5)
    voters: tuple[str, ...] = ("engineer", "tester", "reviewer", "librarian")
