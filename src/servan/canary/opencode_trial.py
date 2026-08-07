"""OpenCodeTrial — BeadTrial via the OpenCode CLI (external, like bd).

Golden bead format: markdown task text; optional YAML frontmatter with a `check:`
shell command (default: `uv run pytest -q`). NOTE: the `opencode run --model` flag
shape is best-effort against current OpenCode — verify against the installed CLI
(same class of risk as the bd JSON shapes; see Decisions log)."""
from __future__ import annotations

from pathlib import Path

import yaml

from ..abstractions import ProcessRunner
from ..config.errors import ConfigError
from ..errors import ProcessError
from ..team.resolved_model import ResolvedModel
from .trial import BeadTrial

_DEFAULT_CHECK = "uv run pytest -q"


class OpenCodeTrial(BeadTrial):
    def __init__(self, runner: ProcessRunner) -> None:
        self._runner = runner

    def trial(self, worktree: Path, bead: Path, model: ResolvedModel) -> bool:
        instructions, check = _parse_bead(bead)
        try:
            self._runner.run("opencode", "run", "--model", model.qualified_id,
                             instructions, cwd=worktree)
            self._runner.run("sh", "-c", check, cwd=worktree)
        except ProcessError:
            return False
        return True


def _parse_bead(bead: Path) -> tuple[str, str]:
    """(task text, check command); frontmatter `check:` overrides the default."""
    text = bead.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text.strip(), _DEFAULT_CHECK
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            data = yaml.safe_load("\n".join(lines[1:index])) or {}
            if not isinstance(data, dict):
                raise ConfigError(f"{bead}: frontmatter must be a mapping")
            return "\n".join(lines[index + 1:]).strip(), str(data.get("check", _DEFAULT_CHECK))
    raise ConfigError(f"{bead}: unterminated frontmatter")
