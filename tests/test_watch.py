"""S-13 `servan watch` warden half — poll loop + side effects around the pure
ContextWarden. SessionSource/SessionControl are faked; the OpenCode HTTP adapter
is covered in test_exporter.py against recorded fixtures (S-15)."""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

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


def test_opencode_source_fails_loud_when_server_down():
    with pytest.raises(WatchError, match="opencode serve"):
        OpenCodeSessionSource("http://127.0.0.1:1", {}, timeout=0.5).sessions()


class _DeadHandler(BaseHTTPRequestHandler):
    """Every request fails — the adapter must surface it as WatchError."""
    def do_POST(self): self.send_response(500); self.end_headers()
    def do_DELETE(self): self.send_response(500); self.end_headers()
    def log_message(self, *args): pass


def test_control_respawn_runs_the_kill_respawn_protocol():
    calls: list[tuple[str, str, dict | None]] = []

    class _Handler(BaseHTTPRequestHandler):
        def _record(self, body=None):
            calls.append((self.command, self.path, body))
            self.send_response(200 if self.path != "/session/ses_new/prompt_async" else 204)
            self.end_headers()
            if self.command == "POST" and self.path == "/session":
                self.wfile.write(json.dumps({"id": "ses_new"}).encode())
            elif self.command != "POST" or "prompt_async" not in self.path:
                self.wfile.write(b"true")

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            self._record(json.loads(self.rfile.read(length)) if length else None)

        def do_DELETE(self):
            self._record()

        def log_message(self, *args): pass

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        OpenCodeSessionControl(f"http://127.0.0.1:{server.server_port}").respawn(
            _session(9_000), "warden reboot note")
    finally:
        server.shutdown()
    assert calls == [
        ("POST", "/session/s1/abort", None),
        ("DELETE", "/session/s1", None),
        ("POST", "/session", {"title": "warden respawn: engineer"}),
        ("POST", "/session/ses_new/prompt_async",
         {"agent": "engineer", "parts": [{"type": "text", "text": "warden reboot note"}]}),
    ]


def test_control_respawn_fails_loud_mid_sequence():
    server = HTTPServer(("127.0.0.1", 0), _DeadHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with pytest.raises(WatchError):
            OpenCodeSessionControl(f"http://127.0.0.1:{server.server_port}").respawn(
                _session(9_000), "note")
    finally:
        server.shutdown()


def test_cli_watch_once_reports_action(cfg_dir, monkeypatch):
    cli_module = sys.modules["servan.cli.app"]   # package attr `app` is the Typer instance
    monkeypatch.setattr(cli_module, "OpenCodeSessionSource",
                        lambda base_url, models: FakeSource([_session(7_500)]))
    monkeypatch.setattr(cli_module, "BeadsLedger", lambda root: FakeLedger())
    result = CliRunner().invoke(app, ["watch", "--once", "--server", "http://unused"])
    assert result.exit_code == 0, result.output
    assert "checkpoint: s1" in result.output


def test_cli_watch_once_fails_loud_when_server_down(cfg_dir):
    result = CliRunner().invoke(app, ["watch", "--once", "--server", "http://127.0.0.1:1"])
    assert result.exit_code == 2
    assert "opencode serve" in result.output
