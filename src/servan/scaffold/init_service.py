"""InitService — the `servan init` use-case: non-destructive brownfield scaffold (S-19).
Copies only missing template files; existing AGENTS.md -> AGENTS.servan.md; .gitignore
gets missing lines under a marker; bd init when .beads/ is absent; core.hooksPath set
only when unset. plan() is side-effect-free; apply() executes and returns the same plan."""
from __future__ import annotations

import pathlib
from dataclasses import dataclass

from ..abstractions import ProcessRunner
from ..errors import ProcessError
from ..logging_setup import get_logger
from ..survey import SurveyCollector
from .base import ScaffoldError, TemplateSource
from .scaffolder import EXECUTABLE_DIRS

_log = get_logger("scaffold.init")

GITIGNORE_MARKER = "# --- servan ---"


@dataclass(frozen=True, slots=True)
class InitAction:
    kind: str      # create | keep | append | git | run
    path: str
    detail: str = ""

    @property
    def line(self) -> str:
        return f"{self.kind} {self.path}" + (f" ({self.detail})" if self.detail else "")


class InitService:
    def __init__(self, templates: TemplateSource, runner: ProcessRunner,
                 survey: SurveyCollector) -> None:
        self._templates = templates
        self._runner = runner
        self._survey = survey

    def plan(self, root: pathlib.Path, *, scan: bool = False) -> list[InitAction]:
        root = root.expanduser().resolve()
        if not (root / ".git").exists():
            raise ScaffoldError(f"{root} is not a git repo — run `git init` first")
        files = self._templates.read_files()
        actions: list[InitAction] = []
        for rel in sorted(files):
            target = root / rel
            if rel == "AGENTS.md" and target.exists():
                if (root / "AGENTS.servan.md").exists():
                    actions.append(InitAction("keep", "AGENTS.servan.md", "already adopted"))
                else:
                    actions.append(InitAction("create", "AGENTS.servan.md",
                                              "from template AGENTS.md; AGENTS.md untouched"))
            elif rel == ".gitignore" and target.exists():
                missing = self._missing_gitignore_lines(files[rel], target)
                actions.append(InitAction(
                    "append", ".gitignore", f"{len(missing)} line(s) under {GITIGNORE_MARKER}")
                    if missing else
                    InitAction("keep", ".gitignore", "all template lines present"))
            elif target.exists():
                actions.append(InitAction("keep", rel, "exists"))
            else:
                actions.append(InitAction("create", rel))
        hookspath = self._read_hookspath(root)
        if hookspath is None:
            actions.append(InitAction("git", "core.hooksPath", "set to .githooks"))
        elif hookspath == ".githooks":
            actions.append(InitAction("keep", "core.hooksPath", "already .githooks"))
        else:
            actions.append(InitAction("keep", "core.hooksPath",
                                      f"kept existing value: {hookspath}"))
        if not (root / ".beads").exists():
            actions.append(InitAction("run", "bd init"))
        if scan:
            actions.append(InitAction("run", "servan survey",
                                      "raw/survey/inventory.{md,json}"))
        return actions

    def apply(self, root: pathlib.Path, *, scan: bool = False) -> list[InitAction]:
        actions = self.plan(root, scan=scan)
        root = root.expanduser().resolve()
        files = self._templates.read_files()
        created: list[str] = []
        for action in actions:
            if action.kind == "create":
                source = "AGENTS.md" if action.path == "AGENTS.servan.md" else action.path
                target = root / action.path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(files[source])
                created.append(action.path)
            elif action.kind == "append":
                self._append_gitignore(root / ".gitignore", files[".gitignore"])
            elif action.kind == "git":
                self._runner.run("git", "config", "core.hooksPath", ".githooks", cwd=root)
            elif action.kind == "run" and action.path == "bd init":
                try:  # --skip-agents: bd would otherwise append its block to AGENTS.md
                    self._runner.run("bd", "init", "--skip-agents", cwd=root)
                except ProcessError as exc:
                    raise ScaffoldError(
                        f"`bd init` failed ({exc}) — install Beads first") from exc
            elif action.kind == "run" and action.path == "servan survey":
                self._survey.write(self._survey.collect(root), root / "raw/survey")
        for rel in created:
            if rel.split("/")[0] in EXECUTABLE_DIRS:
                path = root / rel
                path.chmod(path.stat().st_mode | 0o111)
        _log.info("init %s: %d actions (%d created)", root, len(actions), len(created))
        return actions

    def _read_hookspath(self, root: pathlib.Path) -> str | None:
        try:
            return self._runner.run("git", "config", "core.hooksPath",
                                    cwd=root).strip() or None
        except ProcessError:
            return None  # git exits non-zero when the key is unset

    @staticmethod
    def _missing_gitignore_lines(template: bytes, target: pathlib.Path) -> list[str]:
        existing = target.read_text(encoding="utf-8").splitlines()
        return [line for line in template.decode().splitlines()
                if line.strip() and not line.startswith("#") and line not in existing]

    def _append_gitignore(self, path: pathlib.Path, template: bytes) -> None:
        missing = self._missing_gitignore_lines(template, path)
        if not missing:
            return
        text = path.read_text(encoding="utf-8")
        block = "\n".join(missing)
        if GITIGNORE_MARKER in text:
            text = text.replace(GITIGNORE_MARKER, f"{GITIGNORE_MARKER}\n{block}", 1)
        else:
            if not text.endswith("\n"):
                text += "\n"
            text += f"\n{GITIGNORE_MARKER}\n{block}\n"
        path.write_text(text, encoding="utf-8")
