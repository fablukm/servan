"""WikiPage + frontmatter models: OKF v0.1 core (required `type`) + the servan extension."""
from __future__ import annotations

import pathlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TypedLink(BaseModel):
    """servan extension: typed edge. Targets are concept ids (path minus .md)."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    rel: Literal["supersedes", "extends", "contradicts", "relates"]
    target: str


class Frontmatter(BaseModel):
    """OKF core (`type` required; unknown keys tolerated per spec) + servan extension fields."""
    model_config = ConfigDict(extra="allow", frozen=True)

    type: str = Field(min_length=1)
    title: str | None = None
    tags: tuple[str, ...] = ()
    timestamp: str | None = None
    status: Literal["current", "draft", "superseded"] | None = None  # servan extension
    links: tuple[TypedLink, ...] = ()                                # servan extension


class WikiPage(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    path: pathlib.Path
    frontmatter: Frontmatter | None  # None = no/unparseable frontmatter block
    body: str
