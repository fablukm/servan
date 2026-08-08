"""ScaffoldService — the `servan new` use-case. Contract in dev/DESIGN.md (S-03)."""
from __future__ import annotations

import pathlib

from ..abstractions import ProcessRunner
from ..errors import ProcessError
from .base import ScaffoldError, TemplateSource

EXECUTABLE_DIRS = (".githooks", "tools")  # freshly written files here get +x


class ScaffoldService:
    def __init__(self, templates: TemplateSource, runner: ProcessRunner) -> None:
        self._templates = templates
        self._runner = runner

    def create(self, target: pathlib.Path, with_ledger: bool = True) -> pathlib.Path:
        """Copy template, git init, core.hooksPath .githooks, chmod hooks/tools,
        `bd init` when with_ledger, initial commit. Refuses a non-empty target."""
        target = target.expanduser().resolve()
        if target.exists() and any(target.iterdir()):
            raise ScaffoldError(f"target directory is not empty: {target}")
        self._templates.copy_tree(target)
        self._runner.run("git", "init", cwd=target)
        self._runner.run("git", "config", "core.hooksPath", ".githooks", cwd=target)
        self._make_executable(target)
        if with_ledger:
            try:
                self._runner.run("bd", "init", cwd=target)
            except ProcessError as exc:
                raise ScaffoldError(
                    f"`bd init` failed ({exc}) — install Beads or rerun with --no-bd") from exc
        self._runner.run("git", "add", "-A", cwd=target)
        self._runner.run("git", "commit", "-m", "[init] servan scaffold", cwd=target)
        return target

    def _make_executable(self, target: pathlib.Path) -> None:
        for dirname in EXECUTABLE_DIRS:
            directory = target / dirname
            if not directory.is_dir():
                continue
            for path in sorted(directory.iterdir()):
                if path.is_file():
                    path.chmod(path.stat().st_mode | 0o111)
