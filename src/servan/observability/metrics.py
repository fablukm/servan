"""Prometheus /metrics — dependency-free text exposition (S-15).
Registry is plain gauges (values are already cumulative/absolutes per poll);
render() is deterministic: samples sorted by name, labels sorted by key."""
from __future__ import annotations

import threading
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, HTTPServer


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _format(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else repr(float(value))


class MetricsRegistry:
    def __init__(self) -> None:
        self._samples: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}

    def set(self, name: str, value: float, labels: Mapping[str, str] | None = None) -> None:
        key = (name, tuple(sorted((labels or {}).items())))
        self._samples[key] = value

    def render(self) -> str:
        lines: list[str] = []
        seen: set[str] = set()
        for (name, labels), value in sorted(self._samples.items()):
            if name not in seen:
                seen.add(name)
                lines.append(f"# TYPE {name} gauge")
            label_text = ",".join(f'{k}="{_escape(v)}"' for k, v in labels)
            lines.append(f"{name}{{{label_text}}} {_format(value)}")
        return "\n".join(lines) + "\n"


class MetricsServer:
    """Thin stdlib HTTP server exposing GET /metrics. start() spawns a daemon thread."""

    def __init__(self, registry: MetricsRegistry, host: str, port: int) -> None:
        self._registry = registry
        self._server = HTTPServer((host, port), self._handler())
        self.port = self._server.server_port

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        registry = self._registry

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path != "/metrics":
                    self.send_response(404)
                    self.end_headers()
                    return
                body = registry.render().encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args: object) -> None:
                pass

        return _Handler

    def start(self) -> None:
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def stop(self) -> None:
        self._server.shutdown()
