"""AgentSession — one live OpenCode session as seen by watch/warden (S-13/S-15)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AgentSession(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    role: str | None = None
    model_alias: str | None = None
    tokens_in_context: int = Field(ge=0)
    ctx: int | None = Field(default=None, ge=1024)
    bead_id: str | None = None  # the bead this session claimed; None = not on a bead

    @property
    def fill(self) -> float | None:
        """Context-fill ratio; None when the model's ctx is unknown."""
        return None if not self.ctx else min(self.tokens_in_context / self.ctx, 1.0)
