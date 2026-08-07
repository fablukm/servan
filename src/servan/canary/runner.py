"""CanaryRunner — golden-bead regression check before a model swap (S-10)."""
from __future__ import annotations

import pathlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CanaryReport:
    role: str
    incumbent: str
    candidate: str
    incumbent_pass_rate: float
    candidate_pass_rate: float

    @property
    def regressed(self) -> bool:
        return self.candidate_pass_rate < self.incumbent_pass_rate


class CanaryRunner:
    def run(self, root: pathlib.Path, role: str, candidate_alias: str) -> CanaryReport:
        raise NotImplementedError("S-10 — see dev/BACKLOG.md")
