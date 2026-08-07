"""S-04 `servan status` — acceptance: fenced sections, graceful "bd not installed"
(exit 2 + install hint), flag-compat probe for bd status names."""
import importlib
import json
import shutil
import subprocess
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from servan.cli.app import app
from servan.ledger import BeadsLedger, LedgerError, TaskLedger, TaskRecord, TaskStatus
from servan.status import StatusService


class FakeLedger(TaskLedger):
    def __init__(self) -> None:
        self.probed = False

    def probe(self) -> None:
        self.probed = True

    def ready(self) -> list[TaskRecord]:
        return [
            TaskRecord(id="bd-b2", status="open", priority=2, title="Ready two"),
            TaskRecord(id="bd-a1", status="open", priority=1, title="Ready one"),
        ]

    def list(self, status=None, priority=None) -> list[TaskRecord]:
        if priority == 4:
            return [TaskRecord(id="bd-c3", status="open", priority=4, title="Someday")]
        if status is TaskStatus.IN_PROGRESS:
            return [TaskRecord(id="bd-d4", status="in_progress", priority=1, title="WIP")]
        if status is TaskStatus.CLOSED:
            return [TaskRecord(id="bd-e5", status="closed", priority=1, title="Done")]
        return []

    def claim(self, task_id: str) -> None: ...
    def close(self, task_id: str, reason: str) -> None: ...


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 8, 7, 8, 57, tzinfo=UTC)


@pytest.fixture
def ledger():
    return FakeLedger()


def test_writes_fenced_sections(tmp_path, ledger):
    target = StatusService(ledger, FixedClock()).write(tmp_path)
    assert target == tmp_path / "wiki" / "status.md"
    text = target.read_text()
    assert ledger.probed                      # flag-compat probe runs first
    assert "_generated 2026-08-07 08:57 UTC" in text
    assert text.startswith("---\ntype: status\ntitle: Status\n"
                           "timestamp: 2026-08-07\nstatus: current\n---")  # OKF frontmatter (S-12)
    for header in ("## Backlog (p4)", "## Ready", "## In flight", "## Recently closed"):
        assert f"{header}\n\n```" in text     # every section is fenced
    assert text.count("```") == 8             # four opened + four closed
    assert text.index("bd-a1") < text.index("bd-b2")   # deterministic id ordering
    assert "bd-c3  p4  open  Someday" in text
    assert "bd-e5  p1  closed  Done" in text


def test_empty_sections_still_fenced(tmp_path):
    class EmptyLedger(FakeLedger):
        def ready(self): return []
        def list(self, status=None, priority=None): return []
    text = StatusService(EmptyLedger(), FixedClock()).write(tmp_path).read_text()
    assert text.count("```") == 8
    assert "## Ready\n\n```\n```" in text


def test_recently_closed_keeps_highest_ids(tmp_path):
    class ManyClosed(FakeLedger):
        def ready(self): return []
        def list(self, status=None, priority=None):
            if status is TaskStatus.CLOSED:
                return [TaskRecord(id=f"bd-{i:02d}", status="closed", priority=1, title=f"t{i}")
                        for i in range(25)]
            return []
    text = StatusService(ManyClosed(), FixedClock()).write(tmp_path).read_text()
    closed = text.split("## Recently closed")[1]
    assert "bd-24" in closed and "bd-05" in closed
    assert "bd-04" not in closed                  # capped at 20, tail kept


def test_bd_not_installed_is_graceful(tmp_path, monkeypatch):
    class MissingBd(FakeLedger):
        def probe(self):
            raise LedgerError("`bd` not found — install Beads (github.com/gastownhall/beads)")
    monkeypatch.setattr(importlib.import_module("servan.cli.app"),
                        "BeadsLedger", lambda root: MissingBd())
    result = CliRunner().invoke(app, ["status", "--project", str(tmp_path)])
    assert result.exit_code == 2
    assert "install Beads" in result.output
    assert not (tmp_path / "wiki" / "status.md").exists()   # no partial writes


def test_json_output_for_dashboards(tmp_path, monkeypatch):
    cli = importlib.import_module("servan.cli.app")
    monkeypatch.setattr(cli, "BeadsLedger", lambda root: FakeLedger())
    monkeypatch.setattr(cli, "SystemClock", FixedClock)
    result = CliRunner().invoke(app, ["status", "-p", str(tmp_path), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["generated"] == "2026-08-07T08:57:00+00:00"
    assert list(data["sections"]) == ["backlog", "ready", "in_flight", "closed"]
    ready = data["sections"]["ready"]
    assert [r["id"] for r in ready] == ["bd-a1", "bd-b2"]     # deterministic ordering
    assert ready[0] == {"id": "bd-a1", "title": "Ready one", "status": "open", "priority": 1}
    assert not (tmp_path / "wiki" / "status.md").exists()     # --json is side-effect free


def test_probe_detects_status_flag_drift(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda exe: "bd")  # pretend bd is installed

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 1, "", 'Error: invalid status "in_progress"')

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(LedgerError, match="flag drift"):
        BeadsLedger(tmp_path).probe()
