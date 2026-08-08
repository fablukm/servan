"""Renderer ABC + RenderResult. A Renderer projects the resolved team into one harness artifact.

Extension point: adding a harness (Claude Code tier env, Kilo mode profiles, ...) means
adding one Renderer subclass file here — SyncService needs no change.
"""
from __future__ import annotations

import abc
import pathlib
import re
from dataclasses import dataclass

from ..config.global_config import GlobalConfig
from ..config.project_config import ProjectConfig
from ..team.resolver import Team

MODEL_LINE = re.compile(r"(?m)^model:.*$")  # frontmatter line every harness renderer rewrites


@dataclass(frozen=True, slots=True)
class RenderResult:
    path: pathlib.Path
    summary: str
    changed: bool = True  # in check mode: desired content differs from disk (drift)


class Renderer(abc.ABC):
    @abc.abstractmethod
    def render(self, team: Team, config: GlobalConfig, project: ProjectConfig,
               root: pathlib.Path, *, check: bool = False, force: bool = False) -> list[RenderResult]:
        """Write artifact(s) under `root`, deterministically. Return what was written.
        With check=True: diff-only — write nothing, report drift via RenderResult.changed.
        With force=True: overwrite locally modified managed files (library installs)."""
