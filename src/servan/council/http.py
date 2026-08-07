"""post_json — the single HTTP seam both voter backends share (stdlib urllib).
Tests substitute this function; backends never touch urllib directly."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .base import CouncilError


def post_json(url: str, payload: dict[str, Any],
              headers: dict[str, str] | None = None, timeout: int = 120) -> dict[str, Any]:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.URLError as exc:
        raise CouncilError(
            f"cannot reach model backend at {url} — is the server running? ({exc})") from exc
    except json.JSONDecodeError as exc:
        raise CouncilError(f"invalid JSON response from {url}: {exc}") from exc
