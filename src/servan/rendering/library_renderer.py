"""LibraryRenderer — installs [team] extra_agents from the library into .opencode/agent/.
Copies (never symlinks) with a provenance comment and the profile's model; installs are
tracked in .servan/library.lock.json so local edits survive sync unless force=True."""
from __future__ import annotations

import pathlib
import re
import shutil

from ..abstractions import Clock
from ..config.errors import ConfigError
from ..config.global_config import GlobalConfig
from ..config.project_config import ProjectConfig
from ..library.loader import LibraryLoader
from ..library.lockfile import LibraryLock, LockEntry, content_hash, folder_hash
from ..logging_setup import get_logger
from ..team.resolver import Team
from .base import MODEL_LINE, Renderer, RenderResult

_log = get_logger("rendering.library")

PROVENANCE = "<!-- installed by servan from library:{name} -->"
_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


class LibraryRenderer(Renderer):
    def __init__(self, loader: LibraryLoader, clock: Clock) -> None:
        self._loader = loader
        self._clock = clock

    def render(self, team: Team, config: GlobalConfig, project: ProjectConfig,
               root: pathlib.Path, *, check: bool = False, force: bool = False
               ) -> list[RenderResult]:
        results: list[RenderResult] = []
        if not project.team.extra_agents and not project.team.skills:
            return results
        lock = LibraryLock.load(root)
        dirty = False
        for name in sorted(project.team.extra_agents):
            desired = self._desired(name, team[name].qualified_id)
            path = root / ".opencode/agent" / f"{name}.md"
            key = f"agent:{name}"
            entry = lock.installs.get(key)
            current = path.read_text(encoding="utf-8") if path.exists() else None
            managed = entry is not None and current is not None \
                and content_hash(current) == entry.sha256
            if current == desired:
                results.append(RenderResult(path=path, summary=f"library agent {name} in sync",
                                            changed=False))
                continue
            if current is not None and not managed and not force:
                note = "local edits" if entry else "no lock entry"
                _log.info("kept %s (%s)", path, note)
                results.append(RenderResult(path=path,
                                            summary=f"library agent {name} kept ({note})",
                                            changed=False))
                continue
            summary = f"library agent {name} -> {team[name].qualified_id}"
            if check:
                results.append(RenderResult(path=path, summary=summary, changed=True))
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(desired, encoding="utf-8")
            lock.installs[key] = LockEntry(
                kind="agent", source=f"agents/{name}.md",
                date=self._clock.now().date().isoformat(), sha256=content_hash(desired))
            dirty = True
            _log.info("installed library agent '%s' -> %s", name, path)
            results.append(RenderResult(path=path, summary=summary))
        for name in sorted(project.team.skills):
            result, installed = self._render_skill(name, root, lock, check=check, force=force)
            dirty = dirty or installed
            results.append(result)
        if dirty:
            lock.save(root)
        return results

    def _render_skill(self, name: str, root: pathlib.Path, lock: LibraryLock,
                      *, check: bool, force: bool) -> tuple[RenderResult, bool]:
        """Verbatim folder copy; no header injection (SKILL.md stays spec-clean)."""
        source = self._loader.skill_source_dir(name)
        desired = folder_hash(source)
        target = root / ".opencode/skills" / name
        key = f"skill:{name}"
        entry = lock.installs.get(key)
        current = folder_hash(target) if target.is_dir() else None
        managed = entry is not None and current is not None and current == entry.sha256
        summary = f"library skill {name} -> .opencode/skills/{name}"
        if current is not None and current == desired and managed:
            return RenderResult(path=target, summary=f"library skill {name} in sync",
                                changed=False), False
        if current is not None and not managed and not force:
            note = "local edits" if entry else "no lock entry"
            _log.info("kept %s (%s)", target, note)
            return RenderResult(path=target, summary=f"library skill {name} kept ({note})",
                                changed=False), False
        if check:
            return RenderResult(path=target, summary=summary, changed=True), False
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
        lock.installs[key] = LockEntry(kind="skill", source=f"skills/{name}",
                                       date=self._clock.now().date().isoformat(),
                                       sha256=desired)
        _log.info("installed library skill '%s' -> %s", name, target)
        return RenderResult(path=target, summary=summary), True

    def _desired(self, name: str, qualified_id: str) -> str:
        source = self._loader.agent_source(name)
        if not MODEL_LINE.search(source):
            raise ConfigError(
                f"library agent '{name}' has no model: line in its frontmatter — "
                f"add one (sync replaces it with the profile's model)")
        stamped = PROVENANCE.format(name=name)
        header = _FRONTMATTER.match(source)
        if header is None:
            return f"{stamped}\n\n{MODEL_LINE.sub(f'model: {qualified_id}', source)}"
        frontmatter = MODEL_LINE.sub(f"model: {qualified_id}", source[:header.end()])
        return f"{frontmatter}\n{stamped}\n{source[header.end():]}"
