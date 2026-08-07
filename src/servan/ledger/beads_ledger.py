"""BeadsLedger — TaskLedger over the `bd` CLI (Dolt-backed; JSONL export in .beads/).

All calls use --json. Field names in TaskRecord are best-effort against bd ~0.60;
`bd prime` is the canonical reference — S-04 acceptance includes a flag-compat probe.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess

from pydantic import TypeAdapter, ValidationError

from ..logging_setup import get_logger
from .base import LedgerError, TaskLedger, TaskRecord, TaskStatus

_log = get_logger("ledger.beads")
_RECORDS = TypeAdapter(list[TaskRecord])


class BeadsLedger(TaskLedger):
    def __init__(self, root: pathlib.Path, executable: str = "bd") -> None:
        self._root = root
        self._exe = executable

    def ready(self) -> list[TaskRecord]:
        return self._parse(self._run("ready", "--json"))

    def list(self, status: TaskStatus | None = None, priority: int | None = None) -> list[TaskRecord]:
        args: list[str] = ["list", "--json"]
        if status is not None:
            args += ["--status", status.value]
        if priority is not None:
            args += ["--priority", str(priority)]
        return self._parse(self._run(*args))

    def claim(self, task_id: str) -> None:
        self._run("update", task_id, "--claim", "--json")

    def close(self, task_id: str, reason: str) -> None:
        self._run("close", task_id, "--reason", reason, "--json")

    def _run(self, *args: str) -> str:
        if shutil.which(self._exe) is None:
            raise LedgerError("`bd` not found — install Beads (github.com/gastownhall/beads) or use --no-bd projects")
        proc = subprocess.run([self._exe, *args], cwd=self._root, capture_output=True, text=True)
        _log.debug("bd %s -> rc=%d", " ".join(args), proc.returncode)
        if proc.returncode != 0:
            raise LedgerError(f"bd {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}")
        return proc.stdout

    @staticmethod
    def _parse(payload: str) -> list[TaskRecord]:
        if not payload.strip():
            return []
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise LedgerError(f"unparseable bd output: {exc}") from exc
        items = data if isinstance(data, list) else data.get("issues", data.get("beads", []))
        try:
            return _RECORDS.validate_python(items)
        except ValidationError as exc:
            raise LedgerError(f"unexpected bd JSON shape: {exc.errors()[0]['msg']}") from exc
