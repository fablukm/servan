"""Rule: servan extension validity WHEN present — enums, superseded-yet-linked-as-current."""
from __future__ import annotations

from collections.abc import Sequence

from ..base import LintRule
from ..finding import Finding
from ..page import WikiPage


class ExtensionValidityRule(LintRule):
    name = "extension-validity"

    def check(self, pages: Sequence[WikiPage]) -> list[Finding]:  # S-07
        raise NotImplementedError("S-07 — see dev/BACKLOG.md")
