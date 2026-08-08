"""OpencodeJsonRenderer — writes opencode.json (providers in use, {env:VAR} keys, default model)."""
from __future__ import annotations

import json
import pathlib
from typing import Any

from ..config.global_config import GlobalConfig
from ..config.project_config import ProjectConfig
from ..config.provider import ProviderKind
from ..logging_setup import get_logger
from ..team.resolver import Team
from .base import Renderer, RenderResult

_log = get_logger("rendering.opencode_json")


class OpencodeJsonRenderer(Renderer):
    def render(self, team: Team, config: GlobalConfig, project: ProjectConfig,
               root: pathlib.Path, *, check: bool = False, force: bool = False) -> list[RenderResult]:
        payload = self._build(team, config)
        path = root / "opencode.json"
        desired = json.dumps(payload, indent=2) + "\n"
        summary = f"default model {payload['model']}"
        if check:
            changed = not path.exists() or path.read_text() != desired
            _log.info("check %s: %s", path, "drift" if changed else "in sync")
            return [RenderResult(path=path, summary=summary, changed=changed)]
        path.write_text(desired)
        _log.info("wrote %s (%d provider blocks)", path, len(payload["provider"]))
        return [RenderResult(path=path, summary=summary)]

    def _build(self, team: Team, config: GlobalConfig) -> dict[str, Any]:
        out: dict[str, Any] = {"$schema": "https://opencode.ai/config.json", "provider": {}}
        used = sorted({m.provider_name for m in team.values()})
        for name in used:
            provider = config.providers[name]
            if provider.kind is not ProviderKind.OPENAI_COMPATIBLE:
                continue  # builtin providers need no block
            models = {m.model_id: {"name": m.alias}
                      for m in sorted(team.values(), key=lambda r: r.alias)
                      if m.provider_name == name}
            options: dict[str, str] = {"baseURL": provider.base_url or ""}
            if provider.api_key_env:
                options["apiKey"] = f"{{env:{provider.api_key_env}}}"
            elif provider.api_key:
                options["apiKey"] = provider.api_key  # literal dummy, e.g. "ollama"
            out["provider"][name] = {"npm": "@ai-sdk/openai-compatible", "name": name,
                                     "options": options, "models": models}
        out["model"] = team["orchestrator"].qualified_id
        return out
