# servan — design

## Purpose & non-goals
servan is the deterministic shell around a multi-agent coding setup: scaffolding,
config rendering, memory hygiene, consensus, model regression. **Non-goals:** being an
agent framework, wrapping/forking OpenCode or Beads (both remain external dependencies
invoked as CLIs), any long-running daemon.

## Architecture style (binding for all new code)
Interface-first with constructor injection, composed at a single root:

| Module | Responsibility |
|---|---|
| `domain.py` | Immutable records, enums, exception hierarchy (`ServanError.exit_code`). No I/O. |
| `abstractions.py` | I-prefixed ABCs — the only types services may depend on |
| `configuration.py` | `Configuration` aggregate + TOML-backed providers (global + instance layers) |
| `services.py` | Stateless use-case services; collaborators via constructor injection only |
| `infrastructure.py` | Edge adapters (filesystem, JSON serialization, subprocess when it arrives) |
| `composition.py` | Composition root — the ONLY module that instantiates concrete types |
| `cli.py` | Presentation: thin typer mapping; `ServanError.exit_code` → process exit |

Rules: new feature = interface in abstractions + service + adapter (if I/O) + wiring in
the composition root + tests against the interface. Services never `import` from
`infrastructure` or `composition`; nothing imports `cli`. Python conventions stay PEP 8
(snake_case members) — the architecture is .NET-shaped, the syntax is not.

## Config layers
Global dir: `~/.config/servan/` (override: env `SERVAN_CONFIG_DIR`, used by tests).

| Layer | File | Content |
|---|---|---|
| identity | `secrets.env` | shell exports; never read by servan (env only) |
| transport | `providers.toml` | `[providers.<name>]` kind, base_url, api_key_env |
| inventory | `models.toml` | `[models]` alias → { provider, id } |
| policy | `profiles.toml` | `[profiles.<name>]` role → alias; `[council]` defaults |
| instance | `<repo>/.servan.toml` | profile + `[roles]` overrides + `[council].enabled` |
| economics | `prices.toml` (optional) | `[prices.<alias>]` input_per_m / output_per_m / cached_per_m; shadow prices for local models |

Merge: three global files (disjoint top-level keys; each asserts `schema = 1`) then
project overrides roles. Validation (always, before any command acts): every role alias
exists in models; every model's provider exists in providers; unknown profile → error.

## Exit codes
0 ok · 1 unexpected error · 2 config/validation error · 3 lint findings · 4 council
escalated to human · 5 canary regression.

## Command contracts
- **new NAME [--no-bd]** — copy `template/` → `./NAME`, `git init`, set
  `core.hooksPath .githooks`, chmod hooks/tools, `bd init` unless `--no-bd`, initial
  commit `[init] servan scaffold`. Refuses non-empty target. (Template location:
  repo-relative for now; packaging into wheel data = S-11.)
- **sync** — read layers + `.servan.toml`; write `opencode.json` (providers used, `{env:VAR}`
  key refs, default model = orchestrator) and rewrite `model:` frontmatter line in
  `.opencode/agent/*.md`. Print role→model table.
- **status** — run `bd` (ready / in-progress / closed / backlog views), write
  `wiki/status.md` with fenced sections; the only command allowed a timestamp.
- **lint** — parse YAML frontmatter of every `wiki/**/*.md` + `specs/**/*.md`:
  require `okf: "0.1"`, valid `type`/`status` enums, ISO `updated`; resolve `links[].target`
  (exit 3 on broken); report orphan pages (no inbound links, excluding index/log/status)
  and `superseded` pages still linked as `current`. `--fix` deferred (S-13, maybe never).
- **council SPEC.md** — Delphi loop per docs/report §5.5: round-1 independent votes
  (JSON-schema-forced) from `[council].voters` using their profile models; consensus =
  no unanswered must-block in-lane objections; ≤ max_cycles; architect-model revision
  between rounds; deadlock → boss model → exit 4 with the unresolved question. Minutes →
  `wiki/meetings/<date>-<slug>.md` (proposal hashes, vote tables, dissent preserved).
- **watch [--port 9105] [--project DIR ...]** — long-running: polls the OpenCode server
  API (sessions, per-message token usage, agent+model — VERIFY endpoint shapes against
  opencode.ai server docs, part of S-15 acceptance) and `bd --json`; serves Prometheus
  `/metrics` (servan_tokens_total{dir}, servan_cost_usd_total via prices.toml,
  servan_context_fill_ratio using models.toml `ctx`, servan_beads{status},
  servan_sessions_active, servan_escalations_open, servan_bead_cycle_seconds) and
  enforces the **context warden**: at `[warden].soft` fill (default 0.7) request an
  agent checkpoint (≤200-token progress note via `bd update <id> --notes`, `wip:`
  commit); at `[warden].hard` (0.85) kill + respawn the role with bead + note + linked
  wiki pages only; recycle orchestrator sessions every `[warden].recycle_beads` (10).
  Thresholds in profiles.toml `[warden]`. models.toml entries gain optional `ctx`.
- **canary ROLE CANDIDATE_ALIAS** — run beads in `tasks/golden/` on incumbent vs
  candidate in scratch worktrees; compare test pass-rate; exit 5 + table on regression.

## Code architecture
Layered, constructor-injected, composition-rooted — Pythonic surface throughout
(PEP 8, dataclasses, Protocols; no interface prefixes, no property ceremony):

| Layer | Modules | Rule |
|---|---|---|
| Values / options | `settings` (frozen dataclasses; pure resolution), `errors` (exit codes on the type) | no I/O |
| Seams | `abstractions` (Protocols: SettingsSource, ProjectSource, ProcessRunner, Clock, Ledger, ModelBackend, SessionSource, MetricsSink) | services depend only on these |
| Adapters | `infrastructure` (SubprocessRunner, SystemClock), `config` repositories, `status.BeadsCliLedger`, `scaffold.RepoTemplateSource` | one external system per class |
| Services | `sync.SyncService`, `scaffold.ScaffoldService`, `status.StatusService`, `lint.LintService` (+ LintRule pipeline), `council.CouncilService`, `canary.CanaryService`, `watch.WatchService` (+ pure `WardenPolicy`) | stateless; collaborators via __init__; return report/outcome values |
| Composition root | `cli` — the only module that instantiates concrete graphs; `_guarded` maps ServanError.exit_code centrally | nothing else news up adapters |

Extension conventions: new lint check = new LintRule class (never a branch in the
service) · new model backend / session source = new adapter behind the existing
Protocol · new command = value-returning service + a thin cli binding. Determinism
and fail-loud rules from above apply to every service.

## OKF v0.1 conformance + servan extension (lint contract)
OKF v0.1 (Google, Jun 2026; Apache-2.0 spec) requires exactly ONE frontmatter field —
`type` — recommends `title`, `description`, `resource`, `tags`, `timestamp`, reserves
`index.md` (catalog) and `log.md` (ISO-8601 change history), and cross-links via
STANDARD MARKDOWN LINKS (concept id = path minus .md). Consumers must tolerate unknown
keys, which is what makes the servan extension legal:

```yaml
type: module            # OKF required. servan vocab: module|decision|gotcha|handoff|meeting|overview|design-spec
title: Rate limiter     # OKF recommended
tags: [ratelimit]       # OKF recommended
timestamp: 2026-07-29   # OKF recommended (ISO 8601)
status: current         # servan extension: current|draft|superseded
links:                  # servan extension: TYPED edges (supersedes|extends|contradicts|relates)
  - { rel: supersedes, target: specs/design/checkout-v1 }
```

Lint checks, in order: (1) OKF conformance — frontmatter exists, non-empty `type`;
(2) markdown-link resolution across wiki/ + specs/ (exit 3 on broken); (3) servan
extension validity WHEN present (enum values, resolvable link targets, superseded pages
still linked as current); (4) orphans (no inbound links; index/log/status exempt).
Spec is v0.1 Draft — record the tracked version in AGENTS.md; migrate via lint on bumps.

## Architecture (post-refactor)
Packages (one specialty each; one public class per file): `config/` pydantic layer
models + ConfigLoader · `team/` TeamResolver -> {role: ResolvedModel} · `rendering/`
Renderer ABC + OpencodeJson/AgentFrontmatter renderers + SyncService · `ledger/`
TaskLedger ABC + BeadsLedger (bd --json) · `lint/` Finding/WikiPage + LintRule ABC +
rules/ (one per file) + LintEngine · `council/` Vote/Minutes models + VoterBackend ABC
+ ollama/openai backends + CouncilEngine (implemented, fake-backend tested) ·
`scaffold/` `status/` `canary/` typed stubs · `observability/` AgentSession +
ContextWarden (policy implemented; daemon = S-13) · `cli/` typer app (sole stdout).
The council `Vote` model doubles as the structured-output JSON schema
(`Vote.json_schema()`). Logging: file-only via `logging_setup` (no console handlers).

## Decisions log (append-only, one line each)
- 2026-07-29 name "servan" (Swiss house spirit); typer + stdlib only; layered TOML split by change-reason; template/** declared inert data (L3) to prevent harness self-confusion.
- 2026-07-29 doc-check: agent dir is .opencode/agent (singular; legacy plural tolerated in sync); ollama provider needs a literal apiKey; Beads is Dolt-backed w/ JSONL export (hook chains bd sync; backlog = p4, types bug|feature|task|epic|chore, ids bd-xxxx); OKF v0.1 requires only `type` — our status/typed-links are a documented extension; cross-links are plain markdown links.
- 2026-07-29 refactor to interface-first / DI architecture (domain, abstractions, configuration, services, infrastructure, composition root, thin CLI); command contracts unchanged; 8 tests green, 14 TDD skips.
- 2026-07-29 OOP restructure: options-pattern dataclasses, Protocol seams, service classes with constructor injection, cli as composition root with a central exit-code guard; .NET-conceptual only — removed a stray parallel draft that used literal <summary> XML doc tags (surface mimicry is out of scope).
- 2026-08-07 S-03 `servan new`: TemplateSource ABC + RepoTemplateSource adapter (repo-relative until S-11), ScaffoldService via injected ProcessRunner; ScaffoldError (package-local, like LedgerError) mapped to exit 2 in cli; bd init failure hints --no-bd; tests use a FakeRunner double (git/bd not required).
- 2026-08-07 S-04 `servan status`: StatusService(ledger, clock) renders 4 fenced sections (id-sorted, capped at 20 — "Recently closed" keeps the id tail since TaskRecord has no closed-at field; probe covers status names only, not --priority/`ready`); `probe()` added to TaskLedger ABC — BeadsLedger verifies --status flag compat (in_progress/closed) and raises "flag drift" LedgerError; missing bd -> exit 2 with install hint; timestamp injected via Clock so tests stay deterministic.
- 2026-08-07 S-05 CLI polish: central `_guarded` in cli (ConfigError/LedgerError/ScaffoldError -> 2, ServanError -> its exit_code, unexpected -> 1 + logfile trace); `--config-dir` threaded via typer ctx.obj into ConfigLoader; `sync --check` = check kwarg through SyncService -> Renderer ABC (RenderResult.changed, write skipped), drift -> exit 3; `--version` needed invoke_without_command=True (was previously unreachable, now tested).
- 2026-08-07 S-06 CI: .github/workflows/ci.yml (setup-uv, `uv sync --locked`, ruff check, pytest) + README badge; new dev dependency `ruff` — justification: backlog S-06 mandates ruff in CI, dev group keeps it out of the runtime closure; B008 silenced via extend-immutable-calls (typer.Option defaults are the idiomatic typer pattern), PLW1510 satisfied with explicit check=False, UP031 -> f-strings, `_guarded` -> PEP 695 type param.
- 2026-08-07 S-07 `servan lint`: new dependency `pyyaml` — justification: OKF frontmatter is YAML and stdlib has no parser (pre-planned in engine docstring); WikiPage gains `page_id` (concept id) so rules stay fs-pure; link targets resolve root- then page-relative via posixpath; ERROR -> exit 3 (conformance, broken markdown+typed links), WARNING non-fatal (orphans, non-ISO timestamp, superseded-linked-as-current); template/ lints clean (exit 0, one benign orphan warning).
- 2026-08-07 S-08 `servan council`: OllamaVoterBackend (native format=json_schema) + OpenAICompatibleVoterBackend (response_format json_schema, Bearer from api_key_env) behind shared `http.post_json` seam (stdlib urllib, monkeypatched in tests); agent/lane forced server-side (model self-report distrusted); DispatchVoterBackend routes per-provider (ollama = port 11434); boss_question added to VoterBackend ABC (deadlock -> orchestrator formulates the human question -> exit 4); MinutesWriter(clock) -> wiki/meetings/<date>-<slug>.md with vote tables + preserved dissent; [council].enabled=false -> exit 2.
- 2026-07-29 OOP refactor: pydantic v2 at all boundaries, frozen dataclasses internally, ABC extension points (Renderer/TaskLedger/LintRule/VoterBackend), one-class-per-file packages, file-only logging (typer.echo only in cli/); CouncilEngine + warden policy implemented and unit-tested (14 passed / 9 skipped).
