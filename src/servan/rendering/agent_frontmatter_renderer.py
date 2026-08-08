"""AgentFrontmatterRenderer — rewrites the `model:` line in .opencode/agent/<role>.md."""
from __future__ import annotations

import pathlib
import re

from ..config.global_config import GlobalConfig
from ..config.project_config import ProjectConfig
from ..logging_setup import get_logger
from ..team.resolver import Team
from .base import Renderer, RenderResult

_log = get_logger("rendering.agent_frontmatter")

_MODEL_LINE = re.compile(r"(?m)^model:.*$")


class AgentFrontmatterRenderer(Renderer):
    def render(self, team: Team, config: GlobalConfig, project: ProjectConfig,
               root: pathlib.Path, *, check: bool = False) -> list[RenderResult]:
        results: list[RenderResult] = []
        agent_dir = self._agent_dir(root)
        if agent_dir is None:
            _log.warning("no .opencode/agent directory under %s — nothing to rewrite", root)
            return results
        for role, model in sorted(team.items()):
            path = agent_dir / f"{role}.md"
            if not path.exists():
                _log.debug("no agent file for role '%s' — skipped", role)
                continue
            summary = f"{role} -> {model.qualified_id}"
            desired = _MODEL_LINE.sub(f"model: {model.qualified_id}", path.read_text())
            if check:
                changed = path.read_text() != desired
                results.append(RenderResult(path=path, summary=summary, changed=changed))
                continue
            path.write_text(desired)
            results.append(RenderResult(path=path, summary=summary))
        _log.info("%s %d agent files under %s",
                  "checked" if check else "rewrote", len(results), agent_dir)
        return results

    @staticmethod
    def _agent_dir(root: pathlib.Path) -> pathlib.Path | None:
        official = root / ".opencode/agent"      # documented layout (singular)
        legacy = root / ".opencode/agents"       # tolerated
        if official.is_dir():
            return official
        if legacy.is_dir():
            return legacy
        return None
