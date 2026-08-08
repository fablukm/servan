"""LibraryService — the `servan library add|remove|new` use-cases (TOML + file effects)."""
from __future__ import annotations

import json
import pathlib
import re
import tomllib

from ..config.errors import ConfigError
from ..logging_setup import get_logger
from .loader import LibraryLoader
from .lockfile import LibraryLock, content_hash

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
        self._loader.agent_source(name)  # validates the name, fail loud
        path = root / ".servan.toml"
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        extras = _team_values(text, "extra_agents")
        if name in extras:
            return f"library agent {name} already in [team] extra_agents"
        path.write_text(_set_team_list(text, "extra_agents", sorted([*extras, name])),
                        encoding="utf-8")
        _log.info("added library agent '%s' to %s", name, path)
        return (f"added {name} to [team] extra_agents — installs on next sync; "
                f'it needs a model: [roles] {name} = "<alias>"')

    def remove(self, root: pathlib.Path, name: str) -> str:
        path = root / ".servan.toml"
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        extras = _team_values(text, "extra_agents")
        if name not in extras:
            raise ConfigError(f"library agent '{name}' is not in [team] extra_agents")
        path.write_text(_set_team_list(text, "extra_agents",
                                       [a for a in extras if a != name]), encoding="utf-8")
        note = self._uninstall(root, name)
        _log.info("removed library agent '%s' from %s (%s)", name, path, note)
        return f"removed {name} from [team] extra_agents; {note}"

    def new_agent(self, name: str) -> pathlib.Path:
        path = self._loader.library_dir / "agents" / f"{name}.md"
        if path.exists():
            raise ConfigError(f"library agent '{name}' already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(AGENT_SKELETON, encoding="utf-8")
        _log.info("scaffolded library agent %s", path)
        return path

    @staticmethod
    def _uninstall(root: pathlib.Path, name: str) -> str:
        lock = LibraryLock.load(root)
        entry = lock.installs.pop(f"agent:{name}", None)
        installed = root / ".opencode/agent" / f"{name}.md"
        if entry is None:
            return "no managed install found"
        if installed.exists():
            if content_hash(installed.read_text(encoding="utf-8")) == entry.sha256:
                installed.unlink()
                note = "deleted .opencode/agent install"
            else:
                note = "kept locally modified .opencode/agent copy"
        else:
            note = "install already gone"
        lock.save(root)
        return note
