"""Rule: OKF conformance — frontmatter exists with a non-empty `type` (the spec's only MUST)."""
from __future__ import annotations

from collections.abc import Sequence

from ..base import LintRule
from ..finding import Finding, Severity
from ..page import WikiPage


class OkfConformanceRule(LintRule):
    name = "okf-conformance"

    def check(self, pages: Sequence[WikiPage]) -> list[Finding]:
        findings: list[Finding] = []
        for page in sorted(pages, key=lambda p: p.page_id):
            if page.frontmatter is None or not page.frontmatter.type.strip():
                findings.append(Finding(
                    self.name, page.path,
                    "missing or invalid frontmatter — OKF v0.1 requires a non-empty `type`",
                    Severity.ERROR))
        return findings
