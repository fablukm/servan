"""S-13 `servan watch` warden half — poll loop + side effects around the pure
ContextWarden. SessionSource/SessionControl are faked; the OpenCode HTTP adapter
is tested against a fake-server double (endpoint shapes still UNVERIFIED — S-15)."""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar

import pytest
from typer.testing import CliRunner

from servan.cli import app
from servan.config import WardenSettings
from servan.ledger.base import TaskLedger
from servan.observability import AgentSession, ContextWarden, WardenActionKind
from servan.observability.base import SessionControl, SessionSource, WatchError
from servan.observability.daemon import WatchDaemon
from servan.observability.opencode import OpenCodeSessionControl, OpenCodeSessionSource


def _session(tokens: int, ctx: int | None = 10_000, bead_id: str | None = "bd-1",
             session_id: str = "s1") -> AgentSession:
    return AgentSession(session_id=session_id, role="engineer", model_alias="local/coder",
                        tokens_in_context=tokens, ctx=ctx, bead_id=bead_id)


class FakeSource(SessionSource):
    def __init__(self, sessions): self._sessions = sessions
    def sessions(self): return self._sessions


class FakeLedger(TaskLedger):
    def __init__(self): self.notes: list[tuple[str, str]] = []
    def probe(self): pass
    def ready(self): return []
    def list(self, status=None, priority=None): return []
    def claim(self, task_id): pass
    def close(self, task_id, reason): pass
    def annotate(self, task_id, note): self.notes.append((task_id, note))


class FakeControl(SessionControl):
    def __init__(self): self.respawned: list[tuple[AgentSession, str]] = []
    def respawn(self, session, note): self.respawned.append((session, note))


def _daemon(sessions):
    ledger, control = FakeLedger(), FakeControl()
    daemon = WatchDaemon(FakeSource(sessions), ContextWarden(WardenSettings(soft=0.7, hard=0.85)),
                         ledger, control)
    return daemon, ledger, control


def test_checkpoint_annotates_the_claimed_bead():
    daemon, ledger, control = _daemon([_session(7_500)])
    actions = daemon.poll_once()
    assert [a.kind for a in actions] == [WardenActionKind.CHECKPOINT]
    assert len(ledger.notes) == 1
    bead_id, note = ledger.notes[0]
    assert bead_id == "bd-1"
    assert "checkpoint" in note and "75%" in note     # reason carried into the note
    assert control.respawned == []


def test_reboot_kills_and_respawns_with_note():
    daemon, ledger, control = _daemon([_session(9_000)])
    actions = daemon.poll_once()
    assert [a.kind for a in actions] == [WardenActionKind.REBOOT]
    assert ledger.notes == []
    session, note = control.respawned[0]
    assert session.session_id == "s1" and "reboot" in note


def test_below_threshold_and_unknown_ctx_are_side_effect_free():
    daemon, ledger, control = _daemon([_session(1_000), _session(10**9, ctx=None, session_id="s2")])
    assert daemon.poll_once() == []
    assert ledger.notes == [] and control.respawned == []


def test_checkpoint_without_claimed_bead_skips_note():
    daemon, ledger, _control = _daemon([_session(7_500, bead_id=None)])
    assert daemon.poll_once() == []                      # nothing applied, nothing raised
    assert ledger.notes == []


class _SessionHandler(BaseHTTPRequestHandler):
    payload: ClassVar[list[dict]] = []

    def do_GET(self):
        assert self.path == "/session"
        body = json.dumps(self.payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args): pass                  # keep test output quiet


@pytest.fixture
def fake_server():
    _SessionHandler.payload = [
        {"session_id": "s1", "role": "engineer", "model_alias": "local/coder",
         "tokens_in_context": 7_500, "ctx": 10_000, "bead_id": "bd-1",
         "unrelated_future_field": {"nested": True}},   # extra keys must be tolerated
    ]
    server = HTTPServer(("127.0.0.1", 0), _SessionHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_opencode_source_parses_fake_server_sessions(fake_server):
    sessions = OpenCodeSessionSource(fake_server).sessions()
    assert len(sessions) == 1
    session = sessions[0]
    assert session.session_id == "s1" and session.bead_id == "bd-1"
    assert session.fill == pytest.approx(0.75)


def test_opencode_source_fails_loud_when_server_down():
    with pytest.raises(WatchError, match="opencode serve"):
        OpenCodeSessionSource("http://127.0.0.1:1", timeout=0.5).sessions()


def test_control_respawn_is_explicitly_unverified_until_s15():
    with pytest.raises(WatchError, match="S-15"):
        OpenCodeSessionControl("http://127.0.0.1:1").respawn(_session(9_000), "note")


def test_cli_watch_once_reports_action(cfg_dir, fake_server, monkeypatch):
    cli_module = sys.modules["servan.cli.app"]   # package attr `app` is the Typer instance
    monkeypatch.setattr(cli_module, "OpenCodeSessionSource",
                        lambda base_url: FakeSource([_session(7_500)]))
    monkeypatch.setattr(cli_module, "BeadsLedger", lambda root: FakeLedger())
    result = CliRunner().invoke(app, ["watch", "--once", "--server", fake_server])
    assert result.exit_code == 0, result.output
    assert "checkpoint: s1" in result.output


def test_cli_watch_once_fails_loud_when_server_down(cfg_dir):
    result = CliRunner().invoke(app, ["watch", "--once", "--server", "http://127.0.0.1:1"])
    assert result.exit_code == 2
    assert "opencode serve" in result.output
