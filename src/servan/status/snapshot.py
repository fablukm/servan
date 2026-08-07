"""StatusSnapshot + Section — immutable ledger views; JSON shape is the dashboard contract."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from ..ledger.base import TaskRecord


@dataclass(frozen=True, slots=True)
class Section:
    key: str        # JSON key: backlog | ready | in_flight | closed
    title: str      # markdown heading
    records: tuple[TaskRecord, ...]


@dataclass(frozen=True, slots=True)
class StatusSnapshot:
    generated: datetime
    sections: tuple[Section, ...]

    def to_json(self) -> str:
        """Deterministic: stable key order, records pre-sorted by the service."""
        payload = {
            "generated": self.generated.isoformat(),
            "sections": {
                section.key: [
                    {"id": r.id, "title": r.title, "status": r.status, "priority": r.priority}
                    for r in section.records
                ]
                for section in self.sections
            },
        }
        return json.dumps(payload, indent=2) + "\n"
