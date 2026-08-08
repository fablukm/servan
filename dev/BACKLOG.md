# servan backlog — v0.1 → v0.3
Tick boxes in the same commit as the work. IDs are commit prefixes: `[S-03] …`.

## v0.1 — scaffold, sync, status
- [x] S-01 config loader: layered load/merge/validate, SERVAN_CONFIG_DIR override, ConfigError messages (shipped as reference impl — treat as reviewed code, extend tests if gaps found)
- [x] S-02 sync: opencode.json render + agent frontmatter rewrite (reference impl; add edge-case tests: missing agent file, builtin-only profile, unknown alias)
- [x] S-03 `servan new`: contract in DESIGN.md; acceptance: creates tree, hooksPath set, hook executable, refuses non-empty dir, `--no-bd` skips ledger, works from any cwd
- [x] S-04 `servan status`: fenced sections, graceful "bd not installed" (exit 2 + install hint), flag-compat probe for bd status names
- [x] S-05 CLI polish: `--version`, `--config-dir`, exit-code table honored, `servan sync --check` (diff-only, no write; exit 3 if drift)
- [x] S-06 CI: GitHub Actions — uv, pytest, ruff; badge in README

## v0.2 — memory hygiene, consensus
- [x] S-07 `servan lint`: full contract; pure function core (files-in → findings-out) + thin CLI; unskip tests/test_lint.py
- [x] S-08 `servan council`: implement OllamaVoterBackend (structured outputs from `Vote.json_schema()`) then OpenAICompatibleVoterBackend; minutes writer + CLI wiring around the already-shipped CouncilEngine (fake-backend tests exist in test_council_engine.py)
- [x] S-09 status backlog section + `--json` output for dashboards

## v0.3 — regression + release
- [x] S-10 `servan canary`: contract in DESIGN.md; worktree isolation; table output
- [x] S-11 packaging: template/ as wheel data (importlib.resources) so `servan new` works without a checkout; acceptance: `uv tool install git+ssh://git@github.com/<you>/servan` installs and scaffolds correctly. PRIVATE — never publish to PyPI or any index.
- [x] S-12 dogfood: migrate THIS repo's dev flow onto servan (wiki/ + bd) and record the experience in docs/ — the showcase closer

## v0.4 — observability
- [x] S-13 `servan watch` warden half: session polling + side effects (checkpoint request via bd notes, kill+respawn protocol) around the already-shipped pure `ContextWarden` policy; acceptance incl. a fake-server test double
- [x] S-14 prices layer + cost accounting: optional prices.toml loading (shipped in config.py), pure cost function (usage × prices, cached-aware), `servan cost` CLI summary per project/role/model
- [x] S-15 `servan watch` exporter half: Prometheus /metrics with {project,role,model,provider} labels; VERIFY OpenCode server API usage-endpoint shapes (blocker for S-13/S-15); Grafana dashboard JSON provisioned under examples/grafana/
## v0.5 — standards, library, brownfield onboarding, product role

Dependency order: S-21 (no code) → S-16 → S-17 → S-18 → S-20 → S-19 → S-22 → S-23/24.

- [x] S-21 **product + surveyor agents** (no Python): add `product.md` (mode: primary, interviewer + PBIs) and `surveyor.md` (read-only brownfield analyst) to `src/servan/template/.opencode/agent/`; add `wiki/vision.md` + `wiki/roadmap.md` stubs with OKF frontmatter; patch template `AGENTS.md` with the file-ownership table (§A of the addendum). Acceptance: `servan new` produces both agents; `servan sync` assigns them models; `servan lint` passes on the new stubs.
- [x] S-16 **standards layer**: `config/standards_set.py` (`StandardsSet` pydantic model) + `config/standards_loader.py` (`StandardsLoader`: reads `~/.config/servan/standards/<name>.toml`, resolves `extends` depth-first, merges — scalars override, string lists concatenate+dedupe preserving order, cycle → `ConfigError`); `ProjectConfig` gains `standards: tuple[str, ...] = ()`; `rendering/standards_renderer.py` writes generated `STANDARDS.md`; `servan standards list|show <name>` CLI. Acceptance: merge-order test (base→python), cycle detection test, unknown standard → exit 2, `STANDARDS.md` byte-identical on re-run.
- [x] S-17 **agent library**: `library/loader.py` (`LibraryLoader`: enumerate `~/.config/servan/library/agents/*.md` and `skills/*/SKILL.md`, `SERVAN_LIBRARY_DIR` override); `rendering/library_renderer.py` copies selected agents into `.opencode/agent/` with a `<!-- installed by servan from library:<name> -->` provenance line and the profile's model; `.servan.toml` gains `[team] extra_agents`; `servan library list|add|remove|new agent <name>`. Acceptance: extra agent without a model mapping → exit 2 naming the fix (`[roles] <name> = "<alias>"`); re-running `add` is idempotent; local edits to an installed agent are NOT clobbered unless `--force`.
- [ ] S-18 **skill library**: same loader; `LibraryRenderer` copies skill folders **verbatim** (no header injection — SKILL.md must stay spec-clean) into `.opencode/skills/<name>/`; provenance recorded in `.servan/library.lock.json`; `.servan.toml` gains `[team] skills`; `servan library add <skill>` and `servan library import --claude <path>` (copy a Claude Code skill folder into the library unchanged). Acceptance: a skill folder round-trips byte-identical; lockfile lists source + install date; `servan library list` shows agents and skills in separate sections.
- [ ] S-20 **`servan survey`**: `survey/collector.py` (`SurveyCollector`) + `survey/report.py` (`SurveyReport` pydantic model). Deterministic, no LLM, no network: file tree (depth ≤3, gitignore-aware), LOC by extension, dependency manifests found + top-level deps, entry points, test layout, git stats (commits, top-20 most-changed files, contributor count), TODO/FIXME counts, 10 largest files. Writes `raw/survey/inventory.md` + `inventory.json`. Acceptance: runs on servan itself in <5s; identical output on re-run except a single timestamp line; works in a repo with no git history.
- [ ] S-19 **`servan init`** (brownfield): non-destructive scaffold of an existing repo — copy only missing template files; existing `AGENTS.md` → write `AGENTS.servan.md` and report; `.gitignore` → append missing lines under a marker; `bd init` if `.beads/` absent; set `core.hooksPath`; write `.servan.toml`; `--dry-run` prints the plan and changes nothing; `--scan` also runs S-20. Refuses if not a git repo (message: run `git init` first). Acceptance: running twice changes nothing the second time; no existing file is ever overwritten; dry-run output matches the real run's report.
- [ ] S-22 **`servan check`**: enforce the machine-checkable half of the standards — `[forbidden].literals` grep with `exclude_paths`, `[tooling]` presence (lockfile, linter config). Findings → exit 3, same reporting shape as `lint`. Acceptance: servan's own repo passes with `base+python`; a planted `print(` in `src/servan/config/` fails, the same line in `src/servan/cli/` passes.
- [ ] S-23 **template + docs wiring**: template `AGENTS.md` references `STANDARDS.md` and the skills mechanism; `.servan.toml` template gains commented `standards`/`[team]` examples; `examples/standards/` and `examples/library/` shipped as starting points.
- [ ] S-24 **README + docs**: new commands table, greenfield-interview and brownfield-init walkthroughs, skills compatibility note (`.claude/skills` works too).
