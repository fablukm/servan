"""S-15 `servan watch` exporter half — OpenCodeSessionSource maps the VERIFIED server
shapes (fixtures captured from a live v1.18.15 server, replayed by a fake server —
tests never touch a live server) and the daemon exposes Prometheus /metrics."""
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import ClassVar

import pytest

from servan.config import ModelSpec, WardenSettings
from servan.ledger.base import TaskLedger, TaskRecord, TaskStatus
from servan.observability import AgentSession, ContextWarden
from servan.observability.base import SessionControl, SessionSource
from servan.observability.daemon import WatchDaemon
from servan.observability.metrics import MetricsRegistry, MetricsServer
from servan.observability.opencode import OpenCodeSessionSource

FIXTURES = Path(__file__).parent / "fixtures" / "opencode"
MODELS = {"api/deepseek": ModelSpec(provider="deepseek", id="deepseek-v4-pro", ctx=131_072)}


class FakeSource(SessionSource):
    def __init__(self, sessions): self._sessions = sessions
    def sessions(self): return self._sessions


class FakeLedger(TaskLedger):
    def probe(self): pass
    def ready(self): return []
    def list(self, status=None, priority=None): return []
    def claim(self, task_id): pass
    def close(self, task_id, reason): pass
    def annotate(self, task_id, note): pass


class FakeControl(SessionControl):
    def respawn(self, session, note): pass


class _FixtureHandler(BaseHTTPRequestHandler):
    fixtures: ClassVar[Path] = FIXTURES

    def do_GET(self):
        if self.path == "/session":
            body = (self.fixtures / "sessions.json").read_bytes()
        elif self.path.startswith("/session/") and self.path.endswith("/message"):
            body = (self.fixtures / "messages.json").read_bytes()
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args): pass


@pytest.fixture
def fixture_server():
    server = HTTPServer(("127.0.0.1", 0), _FixtureHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_source_maps_verified_session_shape(fixture_server):
    sessions = OpenCodeSessionSource(fixture_server, MODELS).sessions()
    assert len(sessions) == 2                       # the fixture holds two sessions
    first = next(s for s in sessions if s.tokens_in_context > 0)
    assert first.session_id == "ses_022ac3477ffelKpvTxFIwJCLRq"
    assert first.role == "build"
    assert first.provider_id == "deepseek"
    assert first.tokens_in_context == 7_464         # last assistant message tokens.total
    assert first.cost == pytest.approx(0.003262935)
    assert first.directory == "C:\\Users\\fablu\\ocprobe"


def test_source_resolves_alias_and_ctx_via_models_toml(fixture_server):
    first = OpenCodeSessionSource(fixture_server, MODELS).sessions()[0]
    assert first.model_alias == "api/deepseek"
    assert first.ctx == 131_072
    assert first.fill == pytest.approx(7_464 / 131_072)


def test_source_abstains_on_unknown_model(fixture_server):
    sessions = OpenCodeSessionSource(fixture_server, {}).sessions()
    assert sessions[0].model_alias is None and sessions[0].ctx is None
    assert sessions[0].fill is None                 # warden abstains


def test_metrics_render_is_deterministic_prometheus_text():
    registry = MetricsRegistry()
    registry.set("servan_sessions_active", 1, {"project": "p", "role": "build",
                                               "model": "m", "provider": "deepseek"})
    registry.set("servan_context_fill_ratio", 0.75, {"project": "p", "role": "build",
                                                     "model": "m", "provider": "deepseek"})
    assert registry.render() == (
        "# TYPE servan_context_fill_ratio gauge\n"
        'servan_context_fill_ratio{model="m",project="p",provider="deepseek",role="build"} 0.75\n'
        "# TYPE servan_sessions_active gauge\n"
        'servan_sessions_active{model="m",project="p",provider="deepseek",role="build"} 1\n'
    )


def test_metrics_render_escapes_windows_paths():
    registry = MetricsRegistry()
    registry.set("servan_sessions_active", 1, {"project": "C:\\proj"})
    assert 'project="C:\\\\proj"' in registry.render()


def test_daemon_emits_session_metrics():
    registry = MetricsRegistry()
    live = AgentSession(session_id="s1", role="build", model_alias="api/deepseek",
                        provider_id="deepseek", directory="proj",
                        tokens_in_context=7_500, ctx=10_000, cost=0.5,
                        tokens_in=7_000, tokens_out=500, tokens_cached=0, bead_id="bd-1")
    daemon = WatchDaemon(FakeSource([live]), ContextWarden(WardenSettings()),
                         FakeLedger(), FakeControl(), metrics=registry)
    daemon.poll_once()
    rendered = registry.render()
    labels = 'model="api/deepseek",project="proj",provider="deepseek",role="build"'
    assert f"servan_sessions_active{{{labels}}} 1\n" in rendered
    assert f"servan_context_fill_ratio{{{labels}}} 0.75\n" in rendered
    assert f"servan_cost_usd_total{{{labels}}} 0.5\n" in rendered
    assert ('servan_tokens_total{kind="input",' + labels + '} 7000\n') in rendered


def test_daemon_emits_bead_counts():
    class TwoOpen(FakeLedger):
        def list(self, status=None, priority=None):
            if status is TaskStatus.OPEN:
                return [TaskRecord(id="bd-1"), TaskRecord(id="bd-2")]
            return []
    registry = MetricsRegistry()
    daemon = WatchDaemon(FakeSource([]), ContextWarden(WardenSettings()),
                         TwoOpen(), FakeControl(), metrics=registry)
    daemon.poll_once()
    assert 'servan_beads{status="open"} 2' in registry.render()
    assert 'servan_beads{status="closed"} 0' in registry.render()


def test_cli_watch_fails_loud_when_metrics_port_taken(cfg_dir):
    import socket

    blocker = socket.socket()          # no SO_REUSEADDR: holds the port exclusively
    blocker.bind(("127.0.0.1", 0))
    blocker.listen()
    try:
        from typer.testing import CliRunner

        from servan.cli import app
        result = CliRunner().invoke(app, ["watch", "--port", str(blocker.getsockname()[1]),
                                          "--server", "http://127.0.0.1:1"])
        assert result.exit_code == 2
        assert "cannot bind metrics port" in result.output
    finally:
        blocker.close()


def test_metrics_server_serves_rendered_registry():
    registry = MetricsRegistry()
    registry.set("servan_sessions_active", 3, {"project": "p"})
    server = MetricsServer(registry, "127.0.0.1", 0)
    server.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{server.port}/metrics") as resp:
            body = resp.read().decode()
        assert resp.status == 200
        assert 'servan_sessions_active{project="p"} 3' in body
    finally:
        server.stop()
