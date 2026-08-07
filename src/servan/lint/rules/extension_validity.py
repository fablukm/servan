"""Rule: servan extension validity WHEN present — enums, superseded-yet-linked-as-current."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from ..base import LintRule
from ..finding import Finding, Severity
from ..page import WikiPage


class ExtensionValidityRule(LintRule):
    name = "extension-validity"

    def check(self, pages: Sequence[WikiPage]) -> list[Finding]:
        superseded = {p.page_id for p in pages
                      if p.frontmatter is not None and p.frontmatter.status == "superseded"}
        findings: list[Finding] = []
        for page in sorted(pages, key=lambda p: p.page_id):
            fm = page.frontmatter
            if fm is None:
                continue
            if isinstance(fm.timestamp, str):
                try:
                    datetime.fromisoformat(fm.timestamp)
                except ValueError:
                    findings.append(Finding(self.name, page.path,
                                            f"non-ISO timestamp: {fm.timestamp!r}",
                                            Severity.WARNING))
            for link in fm.links:
                target_id = link.target.removesuffix(".md")
                if link.rel != "supersedes" and target_id in superseded:
                    findings.append(Finding(
                        self.name, page.path,
                        f"links to superseded page {target_id!r} as current (rel={link.rel})",
                        Severity.WARNING))
        return findings
