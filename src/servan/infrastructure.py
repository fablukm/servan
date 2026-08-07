"""Concrete adapters for the runtime seams."""
from __future__ import annotations

import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .errors import ProcessError


class SubprocessRunner:
    def run(self, *argv: str, cwd: Path | None = None) -> str:
        # which() first: PATHEXT-aware (Windows npm shims are .cmd) and turns a
        # missing executable into one actionable ProcessError, not WinError 2.
        exe = shutil.which(argv[0])
        if exe is None:
            raise ProcessError(f"`{argv[0]}` not found on PATH")
        try:
            result = subprocess.run([exe, *argv[1:]], cwd=cwd,
                                    capture_output=True, text=True, check=False)
        except OSError as exc:
            raise ProcessError(f"`{' '.join(argv)}` failed to start: {exc}") from exc
        if result.returncode != 0:
            raise ProcessError(
                f"`{' '.join(argv)}` failed ({result.returncode}): {result.stderr.strip()}")
        return result.stdout


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)
