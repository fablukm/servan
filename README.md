# servan

*A house spirit for multi-agent coding.* In Swiss folklore, the servan quietly keeps the
household running. This servan scaffolds, configures, and audits a role-split AI coding
team (OpenCode + Ollama/APIs) — it is the thin deterministic layer around the agents,
not an agent framework itself.

> **Meta note:** this repository is itself being developed by an AI coding agent
> (Kimi Code CLI running K3). Layer map and rules for that agent: see `AGENTS.md`.
> The confusingly-similar files under `template/` are *product data* servan ships to
> end-user projects — not this repo's own configuration.

## What it does

| Command | Purpose |
|---|---|
| `servan new` | Scaffold a project from `template/` (wiki + OKF frontmatter, role agents, hooks, ledger) |
| `servan sync` | Render layered TOML config → `opencode.json` + per-role `model:` lines |
| `servan status` | Task ledger (`bd`) → browsable `wiki/status.md` |
| `servan lint` | Validate OKF frontmatter + wiki link graph (orphans, broken `supersedes`, …) |
| `servan council` | Deterministic Delphi consensus loop over a spec; minutes → `wiki/meetings/` |
| `servan canary` | Golden-bead regression check before swapping a role's model |

## Config layers (`~/.config/servan/`)

identity `secrets.env` · transport `providers.toml` · inventory `models.toml` ·
policy `profiles.toml` · instance `<repo>/.servan.toml` — split by *why it changes*.
Examples in `examples/config/`.

## Quickstart

```bash
uv sync && uv run servan --help
uv run pytest -q
```

## Status

v0.1 in development. Roadmap in `dev/BACKLOG.md`; architecture in `dev/DESIGN.md`;
background research in `docs/` (report + setup manual). MIT.
