"""Cost accounting (S-14) — pure: usage x prices.toml in, CostLine rows out.
Cached tokens bill at cached_per_m when set, else at input_per_m; a model without
a price yields cost=None — the CLI prints n/a (visible, never a silent zero)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..config.price import ModelPrice
from .session import AgentSession

_PER_MILLION = 1_000_000


def session_cost(tokens_in: int, tokens_out: int, tokens_cached: int,
                 price: ModelPrice | None) -> float | None:
    """USD for one session. Cached tokens are a subset of input billed at the cache rate."""
    if price is None:
        return None
    cached_rate = price.cached_per_m if price.cached_per_m is not None else price.input_per_m
    uncached_in = max(tokens_in - tokens_cached, 0)
    return (uncached_in * price.input_per_m + tokens_cached * cached_rate
            + tokens_out * price.output_per_m) / _PER_MILLION


@dataclass(frozen=True, slots=True)
class CostLine:
    project: str
    role: str
    model_alias: str
    sessions: int
    tokens_in: int
    tokens_out: int
    tokens_cached: int
    cost: float | None                    # None = model has no price entry


def summarize(sessions: Sequence[AgentSession],
              prices: Mapping[str, ModelPrice]) -> tuple[CostLine, ...]:
    """Aggregate sessions per (project, role, model); sorted for deterministic output."""
    buckets: dict[tuple[str, str, str], list[AgentSession]] = {}
    for session in sessions:
        key = (session.directory or "unknown",
               session.role or "unknown",
               session.model_alias or "unknown")
        buckets.setdefault(key, []).append(session)
    lines = []
    for (project, role, alias), group in sorted(buckets.items()):
        price = prices.get(alias)
        lines.append(CostLine(
            project, role, alias, len(group),
            sum(s.tokens_in for s in group),
            sum(s.tokens_out for s in group),
            sum(s.tokens_cached for s in group),
            sum(c for c in (session_cost(s.tokens_in, s.tokens_out, s.tokens_cached, price)
                            for s in group) if c is not None) if price is not None else None))
    return tuple(lines)
