"""LintEngine — loads wiki/spec pages, runs rules, aggregates findings.
Pure core: files-in -> findings-out; rules never touch the filesystem.
"""
from __future__ import annotations

import pathlib
from collections.abc import Sequence

import yaml
from pydantic import ValidationError

from ..logging_setup import get_logger
from .base import LintRule
from .finding import Finding
from .page import Frontmatter, WikiPage
from .rules import ALL_RULES

_log = get_logger("lint.engine")


class LintEngine:
    def __init__(self, rules: Sequence[LintRule] = ALL_RULES) -> None:
        self._rules: tuple[LintRule, ...] = tuple(rules)

    def run(self, root: pathlib.Path) -> list[Finding]:
        pages = self.load_pages(root)
        findings: list[Finding] = []
        for rule in self._rules:
            findings.extend(rule.check(pages))
        return findings

    def load_pages(self, root: pathlib.Path) -> list[WikiPage]:
        pages: list[WikiPage] = []
        for sub in ("wiki", "specs"):
            base = root / sub
            if not base.is_dir():
                continue
            for path in sorted(base.rglob("*.md")):
                pages.append(self._load(root, path))
        _log.info("loaded %d pages from %s", len(pages), root)
        return pages

    @staticmethod
    def _load(root: pathlib.Path, path: pathlib.Path) -> WikiPage:
        text = path.read_text(encoding="utf-8")
        page_id = path.relative_to(root).with_suffix("").as_posix()
        frontmatter, body = _split_frontmatter(text)
        return WikiPage(path=path, page_id=page_id, frontmatter=frontmatter, body=body)


def _split_frontmatter(text: str) -> tuple[Frontmatter | None, str]:
    """(Frontmatter, body); frontmatter is None when absent, invalid YAML, or schema-invalid."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            raw = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1:])
            try:
                data = yaml.safe_load(raw)
                if not isinstance(data, dict):
                    return None, body
                return Frontmatter.model_validate(data), body
            except (yaml.YAMLError, ValidationError):
                return None, body
    return None, text
