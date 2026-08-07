"""Rule: every markdown link and servan `links[].target` resolves inside wiki/ + specs/ (ERROR)."""
from __future__ import annotations

from collections.abc import Sequence

from ..base import LintRule
from ..finding import Finding
from ..page import WikiPage


class LinkResolutionRule(LintRule):
    name = "link-resolution"

    def check(self, pages: Sequence[WikiPage]) -> list[Finding]:  # S-07
        raise NotImplementedError("S-07 — see dev/BACKLOG.md")
