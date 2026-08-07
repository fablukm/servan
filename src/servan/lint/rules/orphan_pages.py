"""Rule: orphan pages — no inbound links (index/log/status exempt) (WARNING)."""
from __future__ import annotations

from collections.abc import Sequence

from ..base import LintRule
from ..finding import Finding, Severity
from ..page import WikiPage, body_link_targets, resolve_link

_EXEMPT_FILENAMES = {"index.md", "log.md", "status.md"}


class OrphanPagesRule(LintRule):
    name = "orphan-pages"

    def check(self, pages: Sequence[WikiPage]) -> list[Finding]:
        known = {p.page_id for p in pages}
        inbound: set[str] = set()
        for page in pages:
            for target in body_link_targets(page.body):
                inbound.update(resolve_link(target, page, known))
            if page.frontmatter is not None:
                for link in page.frontmatter.links:
                    inbound.update(resolve_link(link.target, page, known))
        findings: list[Finding] = []
        for page in sorted(pages, key=lambda p: p.page_id):
            if page.path.name in _EXEMPT_FILENAMES or page.page_id in inbound:
                continue
            findings.append(Finding(self.name, page.path,
                                    "orphan page — no inbound links", Severity.WARNING))
        return findings
