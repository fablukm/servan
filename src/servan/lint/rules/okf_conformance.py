"""Rule: OKF conformance — frontmatter exists with a non-empty `type` (the spec's only MUST)."""
from __future__ import annotations

from collections.abc import Sequence

from ..base import LintRule
from ..finding import Finding
from ..page import WikiPage


class OkfConformanceRule(LintRule):
    name = "okf-conformance"

    def check(self, pages: Sequence[WikiPage]) -> list[Finding]:  # S-07
        raise NotImplementedError("S-07 — see dev/BACKLOG.md")
