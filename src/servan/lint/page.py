"""WikiPage + frontmatter models: OKF v0.1 core (required `type`) + the servan extension."""
from __future__ import annotations

import pathlib
import posixpath
import re
from datetime import date
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
    timestamp: date | str | None = None  # YAML parses bare dates into `date`
    status: Literal["current", "draft", "superseded"] | None = None  # servan extension
    links: tuple[TypedLink, ...] = ()                                # servan extension


class WikiPage(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    path: pathlib.Path
    page_id: str                     # concept id: root-relative path minus .md, posix
    frontmatter: Frontmatter | None  # None = no/unparseable frontmatter block
    body: str


_BODY_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def body_link_targets(body: str) -> list[str]:
    """Markdown link targets in a page body; externals dropped, #fragments stripped."""
    targets: list[str] = []
    for match in _BODY_LINK.finditer(body):
        target = match.group(1).split("#", 1)[0]
        if target and not target.startswith(("http://", "https://", "mailto:")):
            targets.append(target)
    return targets


def resolve_link(target: str, page: WikiPage, known_ids: set[str]) -> list[str]:
    """Known page ids matching a markdown or typed link target (root- then page-relative)."""
    target = target.removesuffix(".md")
    base = posixpath.dirname(page.page_id)
    candidates = (posixpath.normpath(target), posixpath.normpath(posixpath.join(base, target)))
    return [c for c in dict.fromkeys(candidates) if c in known_ids]
