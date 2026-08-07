"""`servan watch` — S-13/S-15 (stubs): context warden + Prometheus exporter.

One daemon, two halves, three seams: SessionSource (OpenCode server API adapter,
endpoint shapes to verify — S-15), Ledger (checkpoint notes), MetricsSink.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .abstractions import Ledger, MetricsSink, SessionSample, SessionSource
from .errors import NotYetImplemented
from .settings import Settings, WardenOptions

Action = Literal["none", "checkpoint", "recycle"]


class WardenPolicy:
    """Pure decision function over a session sample — trivially unit-testable."""

    def __init__(self, options: WardenOptions, settings: Settings) -> None:
        self._options = options
        self._settings = settings

    def decide(self, sample: SessionSample) -> Action:
        model = self._settings.models.get(sample.model_alias)
        if model is None or not model.ctx:
            return "none"                       # no ctx declared -> warden abstains
        fill = sample.tokens_in_context / model.ctx
        if fill >= self._options.hard:
            return "recycle"
        if fill >= self._options.soft:
            return "checkpoint"
        return "none"


@dataclass(frozen=True, slots=True)
class WatchOptions:
    port: int = 9105
    poll_seconds: float = 5.0


class WatchService:
    def __init__(self, sessions: SessionSource, ledger: Ledger,
                 sink: MetricsSink, policy: WardenPolicy,
                 options: WatchOptions = WatchOptions()) -> None:
        self._sessions = sessions
        self._ledger = ledger
        self._sink = sink
        self._policy = policy
        self._options = options

    def serve_forever(self) -> None:
        raise NotYetImplemented("S-13")
