"""LibraryLock — .servan/library.lock.json: what servan installed, with content hashes."""
from __future__ import annotations

import hashlib
import json
import pathlib

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..config.errors import ConfigError

LOCK_PATH = pathlib.Path(".servan/library.lock.json")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class LockEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: str
    source: str
    date: str
    sha256: str


class LibraryLock(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    version: int = Field(default=1, alias="schema")
    installs: dict[str, LockEntry] = {}

    @classmethod
    def load(cls, root: pathlib.Path) -> LibraryLock:
        path = root / LOCK_PATH
        if not path.exists():
            return cls()
        try:
            return cls.model_validate_json(path.read_text(encoding="utf-8"))
        except (ValidationError, ValueError) as exc:
            raise ConfigError(f"invalid {path}: {exc}") from exc

    def save(self, root: pathlib.Path) -> None:
        path = root / LOCK_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema": self.version,
                   "installs": {key: entry.model_dump()
                                for key, entry in sorted(self.installs.items())}}
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
