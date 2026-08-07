"""Finding + Severity — immutable lint result value objects."""
from __future__ import annotations

import pathlib
from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"      # exit 3
    WARNING = "warning"  # reported, non-fatal


@dataclass(frozen=True, slots=True)
class Finding:
    rule: str
    path: pathlib.Path
    message: str
    severity: Severity
