"""Concrete adapters for the runtime seams."""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .errors import ProcessError


class SubprocessRunner:
    def run(self, *argv: str, cwd: Path | None = None) -> str:
        result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            raise ProcessError(
                f"`{' '.join(argv)}` failed ({result.returncode}): {result.stderr.strip()}")
        return result.stdout


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)
