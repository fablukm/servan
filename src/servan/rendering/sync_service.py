"""SyncService — composes Renderers over a resolved team. The `servan sync` use-case."""
from __future__ import annotations

import pathlib
from collections.abc import Sequence

from ..abstractions import Clock
from ..config.loader import ConfigLoader
from ..config.standards_loader import StandardsLoader
from ..infrastructure import SystemClock
from ..library.loader import LibraryLoader
from ..logging_setup import get_logger
from ..team.resolver import TeamResolver
from .agent_frontmatter_renderer import AgentFrontmatterRenderer
from .base import Renderer, RenderResult
from .library_renderer import LibraryRenderer
from .opencode_json_renderer import OpencodeJsonRenderer
from .standards_renderer import StandardsRenderer

_log = get_logger("rendering.sync")


class SyncService:
    def __init__(self, loader: ConfigLoader | None = None,
                 renderers: Sequence[Renderer] | None = None,
                 clock: Clock | None = None) -> None:
        self._loader = loader or ConfigLoader()
        self._renderers: tuple[Renderer, ...] = tuple(
            renderers if renderers is not None
            else (LibraryRenderer(LibraryLoader(self._loader.config_dir),
                                  clock or SystemClock()),
                  OpencodeJsonRenderer(), AgentFrontmatterRenderer(),
                  StandardsRenderer(StandardsLoader(self._loader.standards_dir)))
        )

    def sync(self, root: pathlib.Path, *, check: bool = False,
             force: bool = False) -> list[RenderResult]:
        config = self._loader.load_global()
        project = self._loader.load_project(root)
        team = TeamResolver(config).resolve(project)
        results: list[RenderResult] = []
        for renderer in self._renderers:
            results.extend(renderer.render(team, config, project, root,
                                           check=check, force=force))
        _log.info("sync %s for %s: %d artifacts", "check" if check else "complete",
                  root, len(results))
        return results
