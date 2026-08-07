"""Rule: every markdown link and servan `links[].target` resolves inside wiki/ + specs/ (ERROR)."""
from __future__ import annotations

from collections.abc import Sequence

from ..base import LintRule
from ..finding import Finding, Severity
from ..page import WikiPage, body_link_targets, resolve_link


class LinkResolutionRule(LintRule):
    name = "link-resolution"

    def check(self, pages: Sequence[WikiPage]) -> list[Finding]:
        known = {p.page_id for p in pages}
        findings: list[Finding] = []
        for page in sorted(pages, key=lambda p: p.page_id):
            for target in body_link_targets(page.body):
                if not resolve_link(target, page, known):
                    findings.append(Finding(self.name, page.path,
                                            f"broken markdown link: {target}", Severity.ERROR))
            if page.frontmatter is not None:
                for link in page.frontmatter.links:
                    if not resolve_link(link.target, page, known):
                        findings.append(Finding(
                            self.name, page.path,
                            f"broken typed link ({link.rel}): {link.target}", Severity.ERROR))
        return findings
