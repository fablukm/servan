"""Vote + Objection — pydantic models ARE the structured-output JSON schema for voters."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Objection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    claim: str
    severity: Literal["must", "should"]
    evidence: str = Field(description="wiki page anchor, test run, or spec section")


class Vote(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    agent: str
    lane: str
    verdict: Literal["approve", "object", "abstain"]
    blocking: bool
    objections: tuple[Objection, ...] = ()
    counter_proposal: str | None = Field(default=None, description="concrete spec edit, <=80 tokens")
    steelman_against: str = Field(description="strongest argument against my own verdict")
    confidence: float = Field(ge=0.0, le=1.0)

    @classmethod
    def json_schema(cls) -> dict[str, Any]:
        """Feed this to the backend's structured-output parameter."""
        return cls.model_json_schema()
