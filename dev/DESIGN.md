# servan — design

## Purpose & non-goals
servan is the deterministic shell around a multi-agent coding setup: scaffolding,
config rendering, memory hygiene, consensus, model regression. **Non-goals:** being an
agent framework, wrapping/forking OpenCode or Beads (both remain external dependencies
invoked as CLIs), any long-running daemon.

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
| standards | `standards/<name>.toml` (optional) | merged house rules -> generated `STANDARDS.md`; machine-checkable half feeds `servan check` (§B) |

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
  `src/servan/template/`, shipped as wheel package data, resolved via
  importlib.resources — S-11.)
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
  API (sessions, per-message token usage, agent+model) and `bd --json`; serves Prometheus
  `/metrics` (servan_tokens_total{kind}, servan_cost_usd_total (server-reported;
  prices.toml accounting = S-14), servan_context_fill_ratio using models.toml `ctx`,
  servan_beads{status}, servan_sessions_active — all {project,role,model,provider};
  servan_escalations_open + servan_bead_cycle_seconds deferred) and
  enforces the **context warden**: at `[warden].soft` fill (default 0.7) request an
  agent checkpoint (≤200-token progress note via `bd update <id> --notes`, `wip:`
  commit); at `[warden].hard` (0.85) kill + respawn the role with bead + note + linked
  wiki pages only; recycle orchestrator sessions every `[warden].recycle_beads` (10).
  Thresholds in profiles.toml `[warden]`. models.toml entries gain optional `ctx`.

  Verified OpenCode server shapes (v1.18.15, probed live 2026-08-07; fixtures in
  `tests/fixtures/opencode/`): `GET /session` → list of `{id, agent, directory, cost,
  model: {id, providerID}, tokens: {input, output, reasoning, cache: {read, write}}}`;
  `GET /session/{id}/message` → list of `{info: {role, modelID, providerID, cost,
  tokens: {total, ...}}, parts}`. tokens_in_context = last assistant message's
  `tokens.total`. Session-control: `POST`/`DELETE /session` live-verified 2026-08-07;
  `POST /session/{id}/abort` + `/prompt_async` per opencode.ai/docs/server.
- **canary ROLE CANDIDATE_ALIAS** — run beads in `tasks/golden/` on incumbent vs
  candidate in scratch worktrees; compare test pass-rate; exit 5 + table on regression.
- **cost [--server URL]** — one poll of the OpenCode server; pure cached-aware
  accounting (usage × prices.toml, cached tokens at `cached_per_m` else input rate);
  deterministic table per project/role/model; unpriced models show `n/a` (never a
  silent zero); server unreachable → exit 2.

## Code architecture
Layered, constructor-injected, composition-rooted — Pythonic surface throughout
(PEP 8, dataclasses, Protocols; no interface prefixes, no property ceremony):

| Layer | Modules | Rule |
|---|---|---|
| Values / options | `settings` (frozen dataclasses; pure resolution), `errors` (exit codes on the type) | no I/O |
| Seams | `abstractions` (Protocols: ProcessRunner, Clock) + package-local ABCs next to their service (`ledger.TaskLedger`, `observability.SessionSource`/`SessionControl`, …) | services depend only on these |
| Adapters | `infrastructure` (SubprocessRunner, SystemClock), `config` repositories, `status.BeadsCliLedger`, `scaffold.PackagedTemplateSource` | one external system per class |
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

## Architecture (binding for all new code)
Interface-first with constructor injection, composed at a single root (`cli/`). Rules:
new feature = seam (shared Protocol in `abstractions.py`, or package-local ABC beside its
service) + service + adapter if I/O (one external system per class, `infrastructure.py` or
package-local) + wiring in the composition root + tests against the seam with fakes of our
own abstractions. Services never `import` from `infrastructure` or `cli`; nothing imports
`cli`. Python conventions stay PEP 8 (snake_case members).

Packages (one specialty each; one public class per file): `config/` pydantic layer
models + ConfigLoader + StandardsLoader (standards/ dir, extends merge) · `library/`
LibraryLoader + LibraryLock (.servan/library.lock.json) + LibraryService (add/remove/new) ·
`survey/` SurveyReport + SurveyCollector (deterministic inventory) · `check/` CheckService
(forbidden literals + tooling presence) · `team/`
TeamResolver -> {role: ResolvedModel} · `rendering/`
Renderer ABC + OpencodeJson/AgentFrontmatter/Standards/Library renderers + SyncService · `ledger/`
TaskLedger ABC + BeadsLedger (bd --json) · `lint/` Finding/WikiPage + LintRule ABC +
rules/ (one per file) + LintEngine · `council/` Vote/Minutes models + VoterBackend ABC
+ ollama/openai backends + CouncilEngine ·
`scaffold/` ScaffoldService (`new`) + InitService (`init`) + PackagedTemplateSource ·
`status/` StatusService + snapshot models · `canary/` CanaryRunner + OpenCodeTrial ·
`observability/` AgentSession + ContextWarden + WatchDaemon + MetricsRegistry/Server ·
`cli/` typer app (sole stdout).
The council `Vote` model doubles as the structured-output JSON schema
(`Vote.json_schema()`). Logging: file-only via `logging_setup` (no console handlers).

## A. File ownership (resolves the "only librarian writes wiki/" rule)

| Path | Owner | Notes |
|---|---|---|
| `wiki/vision.md`, `wiki/roadmap.md` | **product** | milestone = "sprint" |
| `wiki/status.md` | **pre-commit hook / `servan status`** | never hand-edited |
| `wiki/meetings/*` | **`servan council`** | minutes, dissent preserved |
| everything else under `wiki/` | **librarian** | ingest + lint |
| `specs/**` | **architect** (design specs: **designer**; math notes: SME agents) | |
| `raw/**` | **human** (designs) + **`servan survey`** + **surveyor** | append-only source layer |
| `STANDARDS.md`, `opencode.json`, `.opencode/agent/*`, `.opencode/skills/*` | **`servan sync`** | generated; edit the TOML instead |

Human commits always outrank agent ownership.

## B. Standards layer (6th config layer)

Location `~/.config/servan/standards/<name>.toml`; opt-in per project via `.servan.toml`:
`standards = ["base", "python"]`.

```toml
schema = 1
name = "python"
extends = ["base"]          # depth-first; cycles are a ConfigError

[principles]   rules = [...]          # list[str] -> concatenated, deduped, order preserved
[layout]       rules = [...]
[testing]      style = "tests-first"  required_before_commit = true  rules = [...]
[tooling]      package_manager = "uv" linter = "ruff"
[dependencies] policy = "..."
[review]       must_check = [...]
[forbidden]    literals = ["print("]  include = ["*.py"]  rules = [...]  exclude_paths = ["src/*/cli/*"]
[git]          commit_prefix = "[<task-id>]"  push_by = "human"  rules = [...]
```

Merge: `extends` depth-first, then the project's list left->right; **scalars: later wins; string
lists: concatenate + dedupe preserving first occurrence.** `StandardsRenderer` projects the merged
result into generated `STANDARDS.md` at the project root (do-not-edit header, deterministic order).
TOML is source of truth; markdown is what agents read; `[forbidden]`/`[tooling]` are the
machine-checkable subset consumed by `servan check` (S-22). `[forbidden].include` (optional,
fnmatch globs) scopes the literal grep to matching files — absent means all text files.

## C. Library — agents and skills

```
~/.config/servan/library/          (override: SERVAN_LIBRARY_DIR)
├── agents/<name>.md               OpenCode agent files (same frontmatter as template roles)
└── skills/<name>/SKILL.md         Agent Skills open standard, verbatim (+ optional scripts/refs)
```

```toml
[team]
extra_agents = ["math-sme"]        # needs a model: [roles] math-sme = "local/reasoner"
skills       = ["react-quality"]
```

`LibraryRenderer` (a `Renderer`, runs inside `servan sync`) **copies** — never symlinks — so
everything stays visible in git and locally editable: agents -> `.opencode/agent/<name>.md` with a
provenance comment and the profile-assigned `model:` line; skills -> `.opencode/skills/<name>/`
byte-identical (no header injection). Installs recorded in `.servan/library.lock.json` (name, kind,
source, date, content hash); locally modified installs are preserved unless `--force`.

Skills compatibility (verified against opencode.ai/docs/skills): OpenCode reads
`.opencode/skills/`, `~/.config/opencode/skills/`, `.claude/skills/`, `~/.claude/skills/`,
`.agents/skills/` — third-party Claude Code skills work unmodified. `servan library import
--claude <path>` copies such a folder into the library as-is.

## D. `servan survey` (deterministic) and `servan init` (brownfield)

**survey** — pure Python, no LLM, no network. gitignore-aware file tree (depth ≤3), LOC by
extension, dependency manifests + top-level deps, entry points, test layout, git stats (commits,
top-20 most-changed files = hot spots, contributors), TODO/FIXME counts, 10 largest files. Writes
`raw/survey/inventory.md` + `inventory.json`. Deterministic except one timestamp line.

**init** — non-destructive scaffold of an existing repo: copies only missing template files; an
existing `AGENTS.md` is never touched (writes `AGENTS.servan.md` + reports); `.gitignore` gets
missing lines appended under a `# --- servan ---` marker; `bd init` when `.beads/` is absent;
`core.hooksPath`; writes `.servan.toml`. `--dry-run` changes nothing; `--scan` also runs survey.
Refuses when not a git repo. Idempotent: a second run is a no-op.

**Onboarding chain (why it is split this way):** `servan init --scan` (machine facts) -> `@surveyor`
reads the inventory + ≤25 targeted files -> `raw/survey/analysis.md` (hypotheses, conventions,
risks, unknowns — each labeled hypothesis vs verified) -> `@product` interviews the human with that
context -> `wiki/vision.md` + `wiki/roadmap.md` + backlog -> `@librarian` ingests `raw/survey/*` into
`wiki/overview.md`, `wiki/modules/*`, `wiki/gotchas.md`. Machine facts and model hypotheses stay in
the raw layer; only curated knowledge reaches the wiki.

## E. Command contracts (additions)

- **`standards list | show <name>`** — enumerate / merge-preview; exit 2 on unknown or cyclic.
- **`library list | add <name> | remove <name> | new agent <name> | new skill <name> | import --claude <path>`** — `add` writes the `.servan.toml` entry and installs on the next `sync`; `list` shows agents and skills separately with installed/available state.
- **`survey [--out raw/survey]`** — as above; exit 0 unless the path is unwritable.
- **`init [--scan] [--dry-run]`** — as above; exit 2 on "not a git repo" or unresolvable conflict.
- **`check`** — machine-checkable standards; findings -> exit 3.

## Decisions log (append-only, one line each)
- 2026-08-07 v0.5 scope: standards layer (6th config layer, TOML source -> generated STANDARDS.md); library of reusable agents+skills (copy-not-symlink, lockfile provenance); brownfield `init`/`survey` (deterministic facts into raw/, LLM judgment on top, librarian still sole wiki writer).
- 2026-08-07 product role is `mode: primary` because subagents cannot interview the human; it owns vision.md+roadmap.md (ownership table §A) while the architect keeps per-feature technical decomposition — no separate PM role (same working set, same failure mode).
- 2026-08-07 skills need no format invention: verified OpenCode reads `.opencode/skills`, `.claude/skills`, `.agents/skills` per opencode.ai/docs/skills, so Agent Skills folders are stored and copied verbatim.
- 2026-08-08 S-21: template ships product.md (mode: primary — subagents cannot interview) + surveyor.md + vision/roadmap OKF stubs; template AGENTS.md gains the §A ownership table (the librarian-only rule now points at it); index.md links vision/roadmap/overview so stubs lint warning-free; sync assigns their models via ordinary project `[roles]` overrides (TeamResolver needed no change). Docs unified: v0.5 addendum merged into DESIGN.md §A–§E + decisions log, addendum file deleted, v0.5 session prompts moved into dev/PROMPTS.md.
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
- 2026-08-07 S-09: backlog section already shipped with S-04 (backlog = p4); added StatusService.collect() -> StatusSnapshot (Section/StatusSnapshot value objects in status/snapshot.py) with deterministic to_json() (stable keys, id-sorted records); `status --json` prints the snapshot to stdout and writes nothing (side-effect-free dashboard polling); markdown output unchanged.
- 2026-08-07 S-10 `servan canary`: BeadTrial ABC + OpenCodeTrial adapter (golden bead = tasks/golden/*.md, optional frontmatter `check:` defaulting to `uv run pytest -q`; `opencode run --model` flag shape UNVERIFIED — same verify-before-rely class as bd); CanaryRunner does one `git worktree add --detach` scratch per side with finally-cleanup; pass-rate table always printed, exit 5 only on regression; unknown role/alias, missing golden dir -> ConfigError exit 2.
- 2026-08-07 S-11 packaging: template/ moved to src/servan/template/ (git mv, history kept) so hatchling ships it as wheel data with zero build config; RepoTemplateSource -> PackagedTemplateSource resolving via importlib.resources.files + as_file — one lookup path for dev checkout and installed wheel, no fallback (fail-loud rule); smoke-verified `uvx --from dist/*.whl servan new demo --no-bd` (24/24 files, hooksPath, init commit); L3 path references updated in AGENTS.md/README/PROMPTS.
- 2026-08-07 S-12 dogfood: repo adopted wiki/ (index/overview/log, `servan lint` clean, guard tests/test_dogfood.py) + bd 1.1.2 ledger (`bd init --skip-agents`; it auto-commits .beads/, sets core.hooksPath itself, appends .gitignore); remaining backlog lives as p4 beads, BACKLOG.md stays milestone checklist; experience in docs/dogfood.md. Dogfood caught a real bug: StatusService emitted status.md with NO OKF frontmatter so `servan lint` rejected servan's own output — fixed, status.md now carries `type: status` frontmatter in BOTH generators (StatusService + template/tools/wiki-status.sh — the same latent bug shipped to end-user projects); Clock-injected timestamps stay deterministic. bd 1.1.2 vs ~0.60: flag probe + TaskRecord parse passed unchanged.
- 2026-08-07 S-13 `servan watch` warden half: WatchDaemon (poll_once atomic+testable; serve_forever thin loop) around the pure ContextWarden; seams package-local in observability/base.py (SessionSource/SessionControl/WatchError exit 2), matching the scaffold/ledger/council convention — superseded draft src/servan/watch.py DELETED along with its now-dead abstractions (Ledger/SessionSample/SessionSource/MetricsSink); AgentSession gains bead_id; TaskLedger gains annotate -> BeadsLedger `bd update --append-notes` (non-clobbering); OpenCodeSessionSource expects AgentSession-shaped JSON (extra keys tolerated) — ENDPOINTS STILL UNVERIFIED, S-15; OpenCodeSessionControl.respawn fails loud until then; `watch --once` CLI (exit 2 unreachable server); orchestrator recycle_beads from the DESIGN contract NOT in S-13's backlog line — deferred with the exporter half.
- 2026-08-07 S-15 exporter half: OpenCode server shapes VERIFIED by probing a live v1.18.15 server (read-only GETs), recorded in DESIGN.md watch contract + fixtures tests/fixtures/opencode/{sessions,messages}.json (fake-server double replays them; tests never touch a live server); OpenCodeSessionSource rewritten to map the real shape (tokens_in_context = last assistant tokens.total; alias/ctx resolved via models.toml, unknown model -> abstain); AgentSession gains provider_id/directory/cost/tokens_in/out/cached; dependency-free Prometheus text exposition (MetricsRegistry deterministic render + MetricsServer stdlib http.server) — no prometheus_client dep (justification: 60 lines of stdlib beat a new dependency); daemon emits sessions_active/tokens_total/cost_usd_total/context_fill_ratio/beads{status} per poll; servan_cost_usd_total uses server-reported session.cost (prices.toml accounting stays S-14); escalations_open + bead_cycle_seconds deferred (need council/bd history seams); Grafana dashboard at examples/grafana/dashboard.json; `watch` CLI now starts MetricsServer on --port.
- 2026-08-07 S-13 side effects completed: OpenCodeSessionControl.respawn = abort -> DELETE /session/:id -> POST /session -> prompt_async(agent=role, note); create/delete LIVE-verified against the user's v1.18.15 server (self-cleaning probe session), abort/prompt_async per opencode.ai/docs/server (not live-tested); fake-server test asserts the exact 4-call sequence + payloads; mid-sequence failure -> WatchError exit 2 with the session state spelled out.
- 2026-08-07 S-14 `servan cost`: pure session_cost (cached tokens bill at cached_per_m else input rate; uncached input = max(in-cached, 0)) + summarize -> CostLine per (project, role, model), sorted, cost=None for unpriced models (CLI prints n/a — no silent zero); missing prices.toml -> warning line + all n/a (layer is optional by design); daemon's servan_cost_usd_total stays server-reported (cheaper per poll), `servan cost` is the prices.toml accounting; smoke test cross-validated: computed 0.0033 == server-reported 0.003263 for the live deepseek session.
- 2026-08-07 e2e shakedown (full workflow against live ollama+opencode): two real portability bugs found and fixed — (1) canary cleanup used `git worktree remove` (git >=2.17); this machine has git 2.14 -> switched to rmtree + `git worktree prune --expire now`, and rmtree now runs BEFORE the raising call so cleanup can't be skipped; (2) SubprocessRunner now resolves executables via shutil.which (Windows npm shims are .cmd — CreateProcess can't find them) and maps FileNotFoundError/OSError to a fail-loud ProcessError instead of an uncaught WinError 2. NOTE: uv tool install caches wheel builds by version — use --refresh when reinstalling same-version local changes.
- 2026-07-29 OOP refactor: pydantic v2 at all boundaries, frozen dataclasses internally, ABC extension points (Renderer/TaskLedger/LintRule/VoterBackend), one-class-per-file packages, file-only logging (typer.echo only in cli/); CouncilEngine + warden policy implemented and unit-tested (14 passed / 9 skipped).
- 2026-08-08 S-16 standards layer: StandardsSet models sections openly (dict of str|bool|list[str]) — fixed per-section models rejected as too rigid for user-defined house rules; StandardsLoader resolves extends depth-first (cycle -> ConfigError naming the chain; unknown names the available set); Renderer ABC gains a ProjectConfig parameter — S-17's LibraryRenderer needs [team] too, so the seam is added once for both; StandardsRenderer joins SyncService's defaults (no-op when standards empty) and shares its pure render_standards_md with `servan standards show` so preview == generated file.
- 2026-08-08 S-17 agent library: lockfile (sha256 per install) is the local-edit detector — introduced NOW for agents, S-18 reuses it for skills; foreign .opencode/agent files (no lock entry) are never adopted without --force; Renderer ABC gains force kwarg + shared MODEL_LINE regex (was duplicated in two renderers); extra-agent model check lives in TeamResolver (validation before any command acts) naming the `[roles]` fix; SyncService's default graph now imports SystemClock from infrastructure — documented bend of the services-never-import-infrastructure rule, same pragmatism as its existing ConfigLoader/StandardsLoader self-composition (cli stays the only stdout).
- 2026-08-08 S-18 skill library: skills copy VERBATIM (no provenance injection — SKILL.md must stay spec-clean), so local-edit detection uses a composite folder_hash (sorted relpaths + bytes, in lockfile.py beside content_hash); updates mirror the library folder (stale files removed via rmtree+copytree) but only when the install is unmodified; add/remove route by kind (agents -> extra_agents, skills -> [team] skills, both accepted by `library add <name>`); `import --claude` = bare copytree, fail-loud without SKILL.md; `library new skill` scaffolds the Agent-Skills-spec frontmatter (name+description).
- 2026-08-08 S-20 `servan survey`: file list via `git ls-files -co --exclude-standard` (gitignore-awareness for free, no matcher to maintain) with a junk-dir-skipping rglob fallback for non-git dirs; git stats optional (ProcessError -> git=None — zero-commit repos are an expected case, not an error); the contract's single timestamp lives ONLY in inventory.md (Clock-injected) so inventory.json is byte-identical across runs; <5s acceptance enforced by a test that surveys the servan checkout itself; go.mod parser handles single-line + block require (caught by review smoke).
- 2026-08-08 S-19 `servan init`: InitService(templates, runner, survey) with side-effect-free plan() / executing apply() returning the same InitAction list (dry-run == real report by construction); TemplateSource ABC gains read_files() (packaged impl via as_file + rglob); LIVE SMOKE CAUGHT: `bd init` appends managed Beads blocks to an existing AGENTS.md -> init runs `bd init --skip-agents` (same flag the servan repo used in S-12) to honor never-touch-existing-files; core.hooksPath is only SET when unset — an existing custom value is kept and reported (non-destructive over contract-literal); _EXECUTABLE_DIRS promoted to public EXECUTABLE_DIRS (shared by new + init).
- 2026-08-08 S-22 `servan check`: CheckService reuses lint's Finding/Severity (identical report shape) and survey's SKIP_DIRS (no second junk-list); `[forbidden]` gained an optional `include` glob list — WITHOUT it the acceptance is impossible, since prose docs legitimately mention `print(` (literals are code rules; absent include = all text files, contract default); globs use fnmatch semantics (* crosses separators — "tests/*" covers nested); linter evidence accepts [tool.<linter>*] subsections (servan has [tool.ruff.lint.*] but no bare [tool.ruff]); servan's own repo dogfoods via a new root .servan.toml with standards = ["base", "python"].
- 2026-08-08 S-23 template wiring: template AGENTS.md gains a "Standards & skills" section (STANDARDS.md is generated/read-only, `servan check` enforces it; .opencode/skills + .claude/skills compatibility note); template .servan.toml carries COMMENTED standards/[team] examples (commented so the default scaffold stays opt-in and ProjectConfig still validates — guarded by test); examples/ standards+library now have loadability guard tests (they are the shipped starting points users copy to ~/.config/servan).
- 2026-08-08 S-24 README: commands table completed (init/survey/standards/check/library; sync row now lists STANDARDS.md + library installs), config-layers line gained standards + library, condensed greenfield/brownfield walkthroughs point at docs/IMPLEMENTATION-MANUAL-v05.md §5 for the long form (single source, no duplication), skills compatibility note inline under the table; v0.1->v0.5 status bump. BACKLOG COMPLETE S-01..S-24.
- 2026-08-08 v0.5 close-out: user config seeded at ~/.config/servan (now its own git repo): missing layers copied from examples/config, standards refreshed to the S-22 include-field versions, library seeds in place; product/surveyor mapped to each profile's architect alias (local/reasoner = deepseek-r1:32b). E2E brownfield proof on a synthetic legacy repo (TEMP/notes-legacy, kept for inspection): init --scan dry-run == real run, existing AGENTS.md untouched, survey named the real hot spot, sync resolved all 12 roles + generated STANDARDS.md, check flagged the missing uv.lock/ruff config (fixed by genuinely uv-ifying the repo), surveyor/product/librarian chain executed (Kimi playing the roles — no live LLM this run), first bead claimed/tested/closed (4/4). Two by-design behaviors surfaced: keys appended after [council] in .servan.toml fail loud as council keys (the S-23 commented template shows the right spot), and lint rejects ../ links escaping wiki/+specs/ (cite outside files as code spans).
- 2026-08-08 audit reconciliation (external review found doc drift, blamed it backwards): AGENTS.md rule 6 was a FOSSIL of the initial OOP draft (unchanged since the init commit; composition.py has never existed) — rewrote it to the real architecture; DESIGN.md's stale "Architecture style" section deleted, merged into the renamed "Architecture (binding for all new code)" section (also de-staled: check/ added, scaffold/status/canary/observability no longer "stubs/S-13"); base.toml layout rule 3 widened (companion value types may live beside ANY public class, not only abstractions — matches project_config/lockfile/report practice); repo is intentionally PUBLIC — the binding rule is index-non-publication, not privacy (AGENTS.md reworded); README config-layers line gained the prices.toml economics layer, status -> v0.5.0 released.
