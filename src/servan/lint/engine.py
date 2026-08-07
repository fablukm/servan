"""LintEngine — loads wiki/spec pages, runs rules, aggregates findings.

Page loading (frontmatter is YAML per OKF) requires the pyyaml dependency planned in
S-07 — add it with a Decisions-log justification when implementing.
"""
from __future__ import annotations

import pathlib
from collections.abc import Sequence

from .base import LintRule
from .finding import Finding
from .page import WikiPage
from .rules import ALL_RULES


class LintEngine:
    def __init__(self, rules: Sequence[LintRule] = ALL_RULES) -> None:
        self._rules: tuple[LintRule, ...] = tuple(rules)

    def run(self, root: pathlib.Path) -> list[Finding]:
        pages = self.load_pages(root)
        findings: list[Finding] = []
        for rule in self._rules:
            findings.extend(rule.check(pages))
        return findings

    def load_pages(self, root: pathlib.Path) -> list[WikiPage]:  # S-07
        raise NotImplementedError("S-07 — see dev/BACKLOG.md")
