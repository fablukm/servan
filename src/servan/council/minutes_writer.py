"""MinutesWriter — MeetingMinutes -> wiki/meetings/<date>-<slug>.md (dissent preserved)."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from ..abstractions import Clock
from .minutes import MeetingMinutes


class MinutesWriter:
    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def write(self, root: Path, minutes: MeetingMinutes) -> Path:
        date = self._clock.now()
        path = root / "wiki" / "meetings" / f"{date:%Y-%m-%d}-{_slug(minutes.topic)}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._render(minutes, date))
        return path

    def _render(self, minutes: MeetingMinutes, date: datetime) -> str:
        lines = [
            "---",
            "type: meeting",
            f"title: Council — {minutes.topic}",
            f"timestamp: {date:%Y-%m-%d}",
            "status: current",
            "---",
            "",
            f"# Council — {minutes.topic}",
            "",
            f"_outcome: {minutes.outcome} · rounds: {len(minutes.rounds)}_",
            "",
        ]
        for round_ in minutes.rounds:
            lines += [f"## Round {round_.number} — proposal `{round_.proposal_hash}`", "",
                      "| voter | lane | verdict | blocking | confidence | steelman |",
                      "|---|---|---|---|---|---|"]
            for vote in round_.votes:
                lines.append(
                    f"| {_cell(vote.agent)} | {_cell(vote.lane)} | {vote.verdict} | "
                    f"{'yes' if vote.blocking else 'no'} | {vote.confidence:.2f} | "
                    f"{_cell(vote.steelman_against)} |")
            objections = [(v.agent, o) for v in round_.votes for o in v.objections]
            if objections:
                lines += ["", "### Objections"]
                lines += [f"- [{o.id}] ({agent}, {o.severity}) {o.claim} — evidence: {o.evidence}"
                          for agent, o in objections]
            counters = [v for v in round_.votes if v.counter_proposal]
            if counters:
                lines += ["", "### Counter-proposals"]
                lines += [f"- {v.agent}: {v.counter_proposal}" for v in counters]
            lines.append("")
        if minutes.unresolved:
            lines += ["## Unresolved (escalated to human)"]
            lines += [f"- {claim}" for claim in minutes.unresolved]
        return "\n".join(lines)


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _slug(topic: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", topic.lower())).strip("-")
