"""OpenCode server adapters. SHAPES VERIFIED 2026-08-07 against a live v1.18.15 server
(fixtures: tests/fixtures/opencode/):

- GET /session                    -> list of {id, agent, directory, cost,
                                     model: {id, providerID}, tokens: {...}, ...}
- GET /session/{id}/message       -> list of {info: {role, tokens: {total, ...}}, parts}

tokens_in_context = the LAST assistant message's tokens.total (the context the next
turn starts from). model_alias/ctx resolve via models.toml (spec.id + provider match);
unresolvable models stay alias/ctx=None so the warden abstains (fail-safe).
Session-control (kill/respawn) endpoints remain UNVERIFIED — respawn fails loud."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from ..config.model_spec import ModelSpec
from .base import SessionControl, SessionSource, WatchError
from .session import AgentSession


class OpenCodeSessionSource(SessionSource):
    def __init__(self, base_url: str, models: Mapping[str, ModelSpec],
                 timeout: float = 5.0) -> None:
        self._base = base_url.rstrip("/")
        self._models = models
        self._timeout = timeout

    def sessions(self) -> list[AgentSession]:
        raw = self._get("/session")
        if not isinstance(raw, list):
            raise WatchError(f"unexpected /session shape: expected list, got {type(raw).__name__}")
        return [self._map(item) for item in raw]

    def _map(self, item: dict[str, Any]) -> AgentSession:
        model = item.get("model") or {}
        alias, spec = self._resolve(model.get("id"), model.get("providerID"))
        tokens = item.get("tokens") or {}
        cache = tokens.get("cache") or {}
        try:
            return AgentSession(
                session_id=item["id"],
                role=item.get("agent"),
                model_alias=alias,
                provider_id=model.get("providerID"),
                directory=item.get("directory"),
                tokens_in_context=self._context_tokens(item["id"]),
                ctx=spec.ctx if spec else None,
                cost=float(item.get("cost") or 0.0),
                tokens_in=int(tokens.get("input") or 0),
                tokens_out=int(tokens.get("output") or 0),
                tokens_cached=int(cache.get("read") or 0),
            )
        except (KeyError, ValidationError, TypeError) as exc:
            raise WatchError(f"unexpected session entry shape: {exc} — "
                             "server version drift? re-verify fixtures (tests/fixtures/opencode/)") from exc

    def _context_tokens(self, session_id: str) -> int:
        """The context the next turn starts from: last assistant message's tokens.total."""
        messages = self._get(f"/session/{session_id}/message")
        if not isinstance(messages, list):
            return 0
        assistants = [m.get("info", {}) for m in messages
                      if isinstance(m, dict) and m.get("info", {}).get("role") == "assistant"]
        if not assistants:
            return 0
        return int((assistants[-1].get("tokens") or {}).get("total") or 0)

    def _resolve(self, model_id: str | None,
                 provider_id: str | None) -> tuple[str | None, ModelSpec | None]:
        for alias, spec in self._models.items():
            if spec.id == model_id and spec.provider == provider_id:
                return alias, spec
        for alias, spec in self._models.items():          # fallback: id-only match
            if spec.id == model_id:
                return alias, spec
        return None, None

    def _get(self, path: str) -> Any:
        try:
            with urllib.request.urlopen(f"{self._base}{path}",
                                        timeout=self._timeout) as response:
                return json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise WatchError(f"cannot poll OpenCode server at {self._base} ({exc}) — "
                             "is `opencode serve` running?") from exc


class OpenCodeSessionControl(SessionControl):
    def __init__(self, base_url: str) -> None:
        self._base = base_url.rstrip("/")

    def respawn(self, session: AgentSession, note: str) -> None:
        raise WatchError(f"kill+respawn for session {session.session_id} not wired — "
                         "OpenCode session-control endpoints unverified; "
                         "session left running, respawn manually")
