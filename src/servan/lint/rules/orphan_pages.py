"""Rule: orphan pages — no inbound links (index/log/status exempt) (WARNING)."""
from __future__ import annotations

from collections.abc import Sequence

from ..base import LintRule
from ..finding import Finding
from ..page import WikiPage


class OrphanPagesRule(LintRule):
    name = "orphan-pages"

    def check(self, pages: Sequence[WikiPage]) -> list[Finding]:  # S-07
        raise NotImplementedError("S-07 — see dev/BACKLOG.md")
