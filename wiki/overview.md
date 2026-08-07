---
type: overview
title: Overview
tags: [architecture]
timestamp: 2026-08-07
status: current
---

# Overview

servan is the deterministic shell around an OpenCode + Ollama multi-agent setup.
Three layers, kept separate at all times (see [index](index.md) for navigation):

- **L1 dev harness** — the agent building servan (`dev/`, session prompts)
- **L2 product** — the servan CLI (`src/servan/`, `tests/`)
- **L3 shipped data** — the end-user template (`src/servan/template/`, inert fixtures)

## Package map (L2)

| Package | Role |
|---|---|
| `cli` | composition root; the only module wiring concrete graphs; central exit-code guard |
| `config` | layered TOML load/merge/validate (`defaults` < `models` < `teams` < project) |
| `scaffold` | `servan new` — packaged template + git/bd bootstrap |
| `rendering` | `servan sync` — opencode.json + agent frontmatter renderers |
| `ledger` | TaskLedger seam; BeadsLedger adapter over the `bd` CLI |
| `status` | `servan status` — bd views → fenced `wiki/status.md` / `--json` snapshot |
| `lint` | `servan lint` — OKF v0.1 conformance + servan extension, pure rule pipeline |
| `council` | `servan council` — Delphi consensus, ollama/openai voter backends |
| `canary` | `servan canary` — golden-bead regression trials in scratch worktrees |
| `watch` | `servan watch` — warden daemon (checkpoint/reboot) + Prometheus /metrics |
| `observability.cost` | `servan cost` — prices.toml accounting per project/role/model |

## Exit codes

0 ok · 1 unexpected · 2 config/validation · 3 lint findings · 4 council escalated · 5 canary regression.
