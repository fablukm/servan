"""StatusService — ledger -> wiki/status.md (S-04) or a JSON snapshot (S-09).
Depends on the TaskLedger ABC only."""
from __future__ import annotations

import pathlib

from ..abstractions import Clock
from ..ledger.base import TaskLedger, TaskRecord, TaskStatus
from .snapshot import Section, StatusSnapshot

_SECTION_LIMIT = 20  # backlog + recently-closed are capped, mirroring tools/wiki-status.sh


class StatusService:
    def __init__(self, ledger: TaskLedger, clock: Clock) -> None:
        self._ledger = ledger
        self._clock = clock

    def collect(self) -> StatusSnapshot:
        """Probe the ledger, then gather the four views (id-sorted, capped)."""
        self._ledger.probe()
        return StatusSnapshot(generated=self._clock.now(), sections=(
            Section("backlog", "Backlog (p4)", self._cap(self._ledger.list(priority=4))),
            Section("ready", "Ready", self._cap(self._ledger.ready())),
            Section("in_flight", "In flight",
                    self._cap(self._ledger.list(status=TaskStatus.IN_PROGRESS))),
            # tail: highest ids proxy most recent (TaskRecord has no closed-at field)
            Section("closed", "Recently closed",
                    self._cap(self._ledger.list(status=TaskStatus.CLOSED), tail=True)),
        ))

    def write(self, root: pathlib.Path) -> pathlib.Path:
        """Render the snapshot into wiki/status.md (fenced, deterministic ordering;
        the only servan output allowed a timestamp)."""
        snapshot = self.collect()
        lines = [
            "---",
            "type: status",
            "title: Status",
            f"timestamp: {snapshot.generated:%Y-%m-%d}",
            "status: current",
            "---",
            "",
            "# Status",
            "",
            f"_generated {snapshot.generated:%Y-%m-%d %H:%M UTC} from `bd` — do not edit_",
            "",
        ]
        for section in snapshot.sections:
            lines += [f"## {section.title}", "", "```"]
            lines += [self._line(record) for record in section.records]
            lines += ["```", ""]
        target = root / "wiki" / "status.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(lines))
        return target

    @staticmethod
    def _cap(records: list[TaskRecord], *, tail: bool = False) -> tuple[TaskRecord, ...]:
        ordered = sorted(records, key=lambda record: record.id)
        capped = ordered[-_SECTION_LIMIT:] if tail else ordered[:_SECTION_LIMIT]
        return tuple(capped)

    @staticmethod
    def _line(record: TaskRecord) -> str:
        priority = f"p{record.priority}" if record.priority is not None else "p-"
        return f"{record.id}  {priority}  {record.status}  {record.title}".rstrip()
