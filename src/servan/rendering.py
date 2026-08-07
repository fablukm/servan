"""Renderers: Settings + role map -> the artifacts OpenCode actually reads."""
from __future__ import annotations

import json
import re
from collections.abc import Mapping

from .settings import ModelBinding, Settings
from .workspace import Workspace


class OpencodeConfigRenderer:
    """Builds the opencode.json document. Deterministic: sorted, trailing newline."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def render(self, bindings: Mapping[str, ModelBinding],
               default_role: str = "orchestrator") -> dict:
        document: dict = {"$schema": "https://opencode.ai/config.json", "provider": {}}
        used = {binding.provider.name for binding in bindings.values()}
        for name in sorted(used):
            provider = self._settings.providers[name]
            if provider.kind != "openai-compatible":
                continue                       # builtin providers need no block
            models = {binding.model.model_id: {"name": binding.model.alias}
                      for binding in sorted(bindings.values(),
                                            key=lambda b: b.model.alias)
                      if binding.provider.name == name}
            options: dict = {"baseURL": provider.base_url}
            if provider.api_key_env:
                options["apiKey"] = f"{{env:{provider.api_key_env}}}"
            elif provider.api_key:
                options["apiKey"] = provider.api_key   # literal, e.g. "ollama"
            document["provider"][name] = {
                "npm": "@ai-sdk/openai-compatible", "name": name,
                "options": options, "models": models}
        document["model"] = bindings[default_role].qualified_id
        return document

    @staticmethod
    def serialize(document: dict) -> str:
        return json.dumps(document, indent=2) + "\n"


class AgentModelWriter:
    """Rewrites the `model:` frontmatter line in each role's agent file."""

    _MODEL_LINE = re.compile(r"(?m)^model:.*$")

    def apply(self, workspace: Workspace,
              bindings: Mapping[str, ModelBinding]) -> list[str]:
        applied: list[str] = []
        for role, binding in sorted(bindings.items()):
            path = workspace.agent_dir / f"{role}.md"
            if not path.exists():
                continue
            path.write_text(self._MODEL_LINE.sub(
                f"model: {binding.qualified_id}", path.read_text()))
            applied.append(f"{role} -> {binding.qualified_id}")
        return applied
