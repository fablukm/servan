"""LintRule ABC. One rule per file under rules/; the engine runs them in registry order."""
from __future__ import annotations

import abc
from collections.abc import Sequence

from .finding import Finding
from .page import WikiPage


class LintRule(abc.ABC):
    name: str

    @abc.abstractmethod
    def check(self, pages: Sequence[WikiPage]) -> list[Finding]:
        """Pure function of the page set — no filesystem access inside rules."""
