"""SyncService — composes Renderers over a resolved team. The `servan sync` use-case."""
from __future__ import annotations

import pathlib
from collections.abc import Sequence

from ..config.loader import ConfigLoader
from ..logging_setup import get_logger
from ..team.resolver import TeamResolver
from .agent_frontmatter_renderer import AgentFrontmatterRenderer
from .base import Renderer, RenderResult
from .opencode_json_renderer import OpencodeJsonRenderer

_log = get_logger("rendering.sync")


class SyncService:
    def __init__(self, loader: ConfigLoader | None = None,
                 renderers: Sequence[Renderer] | None = None) -> None:
        self._loader = loader or ConfigLoader()
        self._renderers: tuple[Renderer, ...] = tuple(
            renderers if renderers is not None
            else (OpencodeJsonRenderer(), AgentFrontmatterRenderer())
        )

    def sync(self, root: pathlib.Path, *, check: bool = False) -> list[RenderResult]:
        config = self._loader.load_global()
        project = self._loader.load_project(root)
        team = TeamResolver(config).resolve(project)
        results: list[RenderResult] = []
        for renderer in self._renderers:
            results.extend(renderer.render(team, config, root, check=check))
        _log.info("sync %s for %s: %d artifacts", "check" if check else "complete",
                  root, len(results))
        return results
