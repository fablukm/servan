"""Renderer ABC + RenderResult. A Renderer projects the resolved team into one harness artifact.

Extension point: adding a harness (Claude Code tier env, Kilo mode profiles, ...) means
adding one Renderer subclass file here — SyncService needs no change.
"""
from __future__ import annotations

import abc
import pathlib
from dataclasses import dataclass

from ..config.global_config import GlobalConfig
from ..team.resolver import Team


@dataclass(frozen=True, slots=True)
class RenderResult:
    path: pathlib.Path
    summary: str


class Renderer(abc.ABC):
    @abc.abstractmethod
    def render(self, team: Team, config: GlobalConfig, root: pathlib.Path) -> list[RenderResult]:
        """Write artifact(s) under `root`, deterministically. Return what was written."""
