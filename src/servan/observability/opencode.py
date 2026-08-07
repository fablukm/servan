"""OpenCode server adapters (S-13). ENDPOINT SHAPES UNVERIFIED — S-15 verifies them
against the opencode.ai server docs. Until then the source expects AgentSession-shaped
JSON entries from GET {base}/session (extra keys are tolerated, so a superset shape
keeps working); control.respawn fails loud instead of guessing a kill endpoint."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from pydantic import ValidationError

from .base import SessionControl, SessionSource, WatchError
from .session import AgentSession


class OpenCodeSessionSource(SessionSource):
    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def sessions(self) -> list[AgentSession]:
        try:
            with urllib.request.urlopen(f"{self._base}/session",
                                        timeout=self._timeout) as response:
                data = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise WatchError(f"cannot poll OpenCode server at {self._base} ({exc}) — "
                             "is `opencode serve` running?") from exc
        items = data if isinstance(data, list) else data.get("sessions", [])
        try:
            return [AgentSession.model_validate(item) for item in items]
        except ValidationError as exc:
            raise WatchError(f"unexpected /session shape: {exc.errors()[0]['msg']} — "
                             "endpoint drift? verify against opencode.ai docs (S-15)") from exc


class OpenCodeSessionControl(SessionControl):
    def __init__(self, base_url: str) -> None:
        self._base = base_url.rstrip("/")

    def respawn(self, session: AgentSession, note: str) -> None:
        raise WatchError(f"kill+respawn for session {session.session_id} not wired — "
                         "OpenCode session-control endpoints unverified (S-15); "
                         "session left running, respawn manually")
