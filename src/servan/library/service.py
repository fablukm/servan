"""LibraryService — the `servan library add|remove|new` use-cases (TOML + file effects)."""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import tomllib

from ..config.errors import ConfigError
from ..logging_setup import get_logger
from .loader import LibraryLoader
from .lockfile import LibraryLock, content_hash, folder_hash

_log = get_logger("library.service")

_TEAM_SECTION = re.compile(r"(?ms)^\[team\].*?(?=^\[|\Z)")

AGENT_SKELETON = """\
---
description: TODO — one line: what this role does, and what it must NOT do
mode: subagent
model: ollama/CHANGE-ME
---
You are <name>. State your inputs, your outputs, and your hard limits.
"""

SKILL_SKELETON = """\
---
name: {name}
description: TODO — what this skill helps with and when to use it
---
# {name}

Instructions, examples, and references for the agent.
"""


def _set_team_list(text: str, key: str, values: list[str]) -> str:
    rendered = f"{key} = [{', '.join(json.dumps(v) for v in values)}]"
    section = _TEAM_SECTION.search(text)
    if section is None:
        if text and not text.endswith("\n"):
            text += "\n"
        return f"{text}\n[team]\n{rendered}\n" if text else f"[team]\n{rendered}\n"
    body = section.group(0)
    line = re.search(rf"(?ms)^{key}\s*=\s*\[[^\]]*\]", body)
    if line:
        body = body[:line.start()] + rendered + body[line.end():]
    else:
        header_end = body.index("\n") + 1
        body = body[:header_end] + rendered + "\n" + body[header_end:]
    return text[:section.start()] + body + text[section.end():]


def _team_values(text: str, key: str) -> list[str]:
    return list(tomllib.loads(text).get("team", {}).get(key, []))


class LibraryService:
    def __init__(self, loader: LibraryLoader) -> None:
        self._loader = loader

    def add(self, root: pathlib.Path, name: str) -> str:
        if name in self._loader.agents():
            key, hint = "extra_agents", f' it needs a model: [roles] {name} = "<alias>"'
        elif name in self._loader.skills():
            key, hint = "skills", ""
        else:
            raise ConfigError(f"unknown library item '{name}' — "
                              f"agents: {', '.join(self._loader.agents()) or 'none'}; "
                              f"skills: {', '.join(self._loader.skills()) or 'none'}")
        path = root / ".servan.toml"
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        values = _team_values(text, key)
        if name in values:
            return f"library item {name} already in [team] {key}"
        path.write_text(_set_team_list(text, key, sorted([*values, name])),
                        encoding="utf-8")
        _log.info("added library item '%s' to [team] %s in %s", name, key, path)
        return f"added {name} to [team] {key} — installs on next sync{';' + hint if hint else '.'}"

    def remove(self, root: pathlib.Path, name: str) -> str:
        path = root / ".servan.toml"
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        key = next((k for k in ("extra_agents", "skills") if name in _team_values(text, k)),
                   None)
        if key is None:
            raise ConfigError(f"library item '{name}' is not in [team] extra_agents or skills")
        path.write_text(_set_team_list(text, key, [v for v in _team_values(text, key)
                                                   if v != name]), encoding="utf-8")
        note = self._uninstall(root, name, "agent" if key == "extra_agents" else "skill")
        _log.info("removed library item '%s' from %s (%s)", name, path, note)
        return f"removed {name} from [team] {key}; {note}"

    def new_agent(self, name: str) -> pathlib.Path:
        path = self._loader.library_dir / "agents" / f"{name}.md"
        if path.exists():
            raise ConfigError(f"library agent '{name}' already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(AGENT_SKELETON, encoding="utf-8")
        _log.info("scaffolded library agent %s", path)
        return path

    def new_skill(self, name: str) -> pathlib.Path:
        path = self._loader.library_dir / "skills" / name / "SKILL.md"
        if path.exists():
            raise ConfigError(f"library skill '{name}' already exists: {path.parent}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(SKILL_SKELETON.format(name=name), encoding="utf-8")
        _log.info("scaffolded library skill %s", path.parent)
        return path

    def import_claude(self, source: pathlib.Path) -> pathlib.Path:
        """Copy a Claude Code skill folder into the library, unchanged."""
        if not (source / "SKILL.md").is_file():
            raise ConfigError(f"no SKILL.md in {source} — not a skill folder")
        target = self._loader.library_dir / "skills" / source.name
        if target.exists():
            raise ConfigError(
                f"skill '{source.name}' already exists in the library: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
        _log.info("imported Claude skill %s -> %s", source, target)
        return target

    @staticmethod
    def _uninstall(root: pathlib.Path, name: str, kind: str) -> str:
        lock = LibraryLock.load(root)
        entry = lock.installs.pop(f"{kind}:{name}", None)
        if entry is None:
            return "no managed install found"
        installed = (root / ".opencode/agent" / f"{name}.md" if kind == "agent"
                     else root / ".opencode/skills" / name)
        note = "install already gone"
        if kind == "agent" and installed.is_file():
            if content_hash(installed.read_text(encoding="utf-8")) == entry.sha256:
                installed.unlink()
                note = "deleted .opencode/agent install"
            else:
                note = "kept locally modified .opencode/agent copy"
        elif kind == "skill" and installed.is_dir():
            if folder_hash(installed) == entry.sha256:
                shutil.rmtree(installed)
                note = "deleted .opencode/skills install"
            else:
                note = "kept locally modified .opencode/skills copy"
        lock.save(root)
        return note
