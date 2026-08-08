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
policy `profiles.toml` · instance `<repo>/.servan.toml` · economics `prices.toml` (optional)
· standards `standards/<name>.toml`
(opt-in per project) · library `library/` (reusable agents + skills) — split by *why it changes*.
Examples in `examples/config/`, `examples/standards/`, `examples/library/`.

## Scenarios

**"I have an idea" (greenfield)** — scaffold, get interviewed, approve the plan, click go:

```bash
servan new myapp && cd myapp
# edit .servan.toml: standards = ["base", "python"], maybe [team] skills = ["react-quality"]
servan sync          # generates STANDARDS.md + installs library items
opencode             # 1. @product interviews you (≤2 bounded rounds, defaults recorded
                     #    as `assumed:`) and writes wiki/vision.md + wiki/roadmap.md +
                     #    the epic/feature backlog in bd
                     # 2. you review wiki/roadmap.md — the planning gate
                     # 3. give the orchestrator the standing order; the team runs the
                     #    backlog bead by bead
```

**"Extend my existing repo — and leave no trace" (brownfield, reversible)** — adoption is
non-destructive (existing files are never overwritten) and fully removable:

```bash
cd existing-repo
servan init --scan --dry-run   # read the plan; nothing is written
servan init --scan             # only-missing template files + raw/survey/inventory.md
servan sync && opencode        # @surveyor analyses the inventory, @product interviews, ...
```

Everything servan adds lives in well-known paths: `AGENTS.servan.md`, `.servan.toml`,
`.githooks/`, `.opencode/`, `tools/`, `wiki/`, `specs/`, `raw/`, `STANDARDS.md`,
`opencode.json`, `.servan/`, `.beads/`, plus one marked block in `.gitignore`
(`# --- servan ---`). To remove every trace: delete those paths, delete the marked block,
`git config --unset core.hooksPath`. Your original files were never touched.

Full walkthroughs: `docs/IMPLEMENTATION-MANUAL-v05.md` §5.

## How it works

You talk to **one** agent; the team never talks to itself — every exchange is
orchestrator → subagent → one distilled result.

| Role | Job |
|---|---|
| **orchestrator** | The primary agent you drive; dispatches one bead at a time |
| **product** | Interviews you, owns `wiki/vision.md` + `wiki/roadmap.md` + the backlog |
| **architect** | Technical decomposition, one feature at a time, just-in-time |
| **engineer / tester / reviewer / data** | Implement · test-first · review · data work |
| **designer / researcher** | Design specs from `raw/design/` · web/document research |
| **librarian** | The only wiki writer: ingests results into OKF-linted pages |
| **surveyor** | Read-only brownfield analyst (`raw/survey/analysis.md`) |

The loop around them is deterministic and file-backed: tasks live in **bd** (ready queue =
execution order), durable knowledge lives in the **wiki** (OKF frontmatter, `servan lint`),
house rules in generated **STANDARDS.md** (`servan check` enforces the machine half),
contested designs go to a **council** vote with preserved dissent, model swaps must pass a
golden-bead **canary**, and `servan watch`/`cost` observe it all.

## Where you interact

| Moment | What happens |
|---|---|
| Planning interview | `@product` asks only decision-changing questions (≤7, then ≤4) |
| Planning gate | You review `wiki/roadmap.md` + `bd list`, then say go |
| Standing order | You hand the orchestrator the autonomous-loop rules once |
| Council escalation | A deadlocked contested spec exits 4 with one question for you |
| Canary verdict | You approve or reject a model swap from the pass-rate table |
| Quality gates | `lint`/`check`/`sync --check` exit 3 — you fix and re-run |
| Git | Agents commit on feature branches; **only you ever push** |

## Quickstart

```bash
uv sync && uv run servan --help
uv run pytest -q
```

## Status

v0.5.0 released (backlog S-01…S-24 complete). Roadmap in `dev/BACKLOG.md`; architecture in
`dev/DESIGN.md`; background research in `docs/` (report + setup manual). MIT.
