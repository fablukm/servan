"""StatusService — ledger -> wiki/status.md (S-04). Depends on the TaskLedger ABC only."""
from __future__ import annotations

import pathlib

from ..abstractions import Clock
from ..ledger.base import TaskLedger, TaskRecord, TaskStatus

_SECTION_LIMIT = 20  # backlog + recently-closed are capped, mirroring tools/wiki-status.sh


class StatusService:
    def __init__(self, ledger: TaskLedger, clock: Clock) -> None:
        self._ledger = ledger
        self._clock = clock

    def write(self, root: pathlib.Path) -> pathlib.Path:
        """Render backlog(p4)/ready/in-flight/recently-closed into wiki/status.md (fenced,
        deterministic ordering; the only servan output allowed a timestamp)."""
        self._ledger.probe()
        # keep_tail: "Recently closed" keeps the highest ids (id order proxies recency —
        # TaskRecord carries no closed-at field); other sections keep the head.
        sections = [
            ("Backlog (p4)", self._ledger.list(priority=4), False),
            ("Ready", self._ledger.ready(), False),
            ("In flight", self._ledger.list(status=TaskStatus.IN_PROGRESS), False),
            ("Recently closed", self._ledger.list(status=TaskStatus.CLOSED), True),
        ]
        lines = [
            "# Status",
            "",
            f"_generated {self._clock.now():%Y-%m-%d %H:%M UTC} from `bd` — do not edit_",
            "",
        ]
        for title, records, keep_tail in sections:
            lines += [f"## {title}", "", "```"]
            ordered = sorted(records, key=lambda record: record.id)
            capped = ordered[-_SECTION_LIMIT:] if keep_tail else ordered[:_SECTION_LIMIT]
            lines += [self._line(record) for record in capped]
            lines += ["```", ""]
        target = root / "wiki" / "status.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(lines))
        return target

    @staticmethod
    def _line(record: TaskRecord) -> str:
        priority = f"p{record.priority}" if record.priority is not None else "p-"
        return f"{record.id}  {priority}  {record.status}  {record.title}".rstrip()
