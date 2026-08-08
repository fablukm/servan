# servan

[![CI](https://github.com/fablukm/servan/actions/workflows/ci.yml/badge.svg)](https://github.com/fablukm/servan/actions/workflows/ci.yml)

*A house spirit for multi-agent coding.* In Swiss folklore, the servan quietly keeps the
household running. This servan scaffolds, configures, and audits a role-split AI coding
team (OpenCode + Ollama/APIs) — it is the thin deterministic layer around the agents,
not an agent framework itself.

> **Meta note:** this repository is itself being developed by an AI coding agent
> (Kimi Code CLI running K3). Layer map and rules for that agent: see `AGENTS.md`.
> The confusingly-similar files under `src/servan/template/` are *product data* servan ships to
> end-user projects — not this repo's own configuration.

## What it does

| Command | Purpose |
|---|---|
| `servan new` | Scaffold a project from the packaged template (wiki + OKF frontmatter, role agents, hooks, ledger) |
| `servan init` | Non-destructive brownfield scaffold of an existing repo (`--dry-run` prints the plan, `--scan` adds a survey) |
| `servan survey` | Deterministic repo inventory → `raw/survey/inventory.{md,json}` — no LLM, no network |
| `servan sync` | Render layered TOML config → `opencode.json`, per-role `model:` lines, `STANDARDS.md`, library installs |
| `servan standards` | List/preview house-rule stacks (`standards/<name>.toml`, `extends` merge) |
| `servan check` | Enforce the machine-checkable standards half (forbidden literals, tooling presence) → exit 3 on findings |
| `servan library` | Mother library of reusable agents + skills: `list · add · remove · new · import --claude` |
| `servan status` | Task ledger (`bd`) → browsable `wiki/status.md` |
| `servan lint` | Validate OKF frontmatter + wiki link graph (orphans, broken `supersedes`, …) |
| `servan council` | Deterministic Delphi consensus loop over a spec; minutes → `wiki/meetings/` |
| `servan canary` | Golden-bead regression check before swapping a role's model |
| `servan watch` | Context-warden daemon + Prometheus `/metrics` exporter |
| `servan cost` | Usage × prices.toml accounting, per project/role/model |

Skills need no new format: OpenCode reads `.opencode/skills/`, `.claude/skills/`,
`~/.claude/skills/` (and more), so third-party Claude Code skills work unmodified —
`servan library import --claude <path>` copies one into your library as-is.

## Config layers (`~/.config/servan/`)

identity `secrets.env` · transport `providers.toml` · inventory `models.toml` ·
policy `profiles.toml` · instance `<repo>/.servan.toml` · standards `standards/<name>.toml`
(opt-in per project) · library `library/` (reusable agents + skills) — split by *why it changes*.
Examples in `examples/config/`, `examples/standards/`, `examples/library/`.

## Two ways in

**Greenfield** — scaffold, then let `@product` interview you (max 2 bounded rounds) into a
vision, a milestone roadmap, and a prioritized backlog:

```bash
servan new myapp && cd myapp
# edit .servan.toml: standards = ["base", "python"], maybe [team] skills = ["react-quality"]
servan sync          # generates STANDARDS.md + installs library items
opencode             # talk to @product, review wiki/roadmap.md, then let the team run
```

**Brownfield** — adopt an existing repo without overwriting anything; machine facts first,
model judgment second:

```bash
cd existing-repo
servan init --scan --dry-run   # read the plan; nothing is written
servan init --scan             # only-missing template files + raw/survey/inventory.md
servan sync && opencode        # @surveyor analyses the inventory, @product interviews, ...
```

Full walkthroughs: `docs/IMPLEMENTATION-MANUAL-v05.md` §5.

## Quickstart

```bash
uv sync && uv run servan --help
uv run pytest -q
```

## Status

v0.5 in development. Roadmap in `dev/BACKLOG.md`; architecture in `dev/DESIGN.md`;
background research in `docs/` (report + setup manual). MIT.
