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
- [ ] S-13 `servan watch` warden half: session polling + side effects (checkpoint request via bd notes, kill+respawn protocol) around the already-shipped pure `ContextWarden` policy; acceptance incl. a fake-server test double
- [ ] S-14 prices layer + cost accounting: optional prices.toml loading (shipped in config.py), pure cost function (usage × prices, cached-aware), `servan cost` CLI summary per project/role/model
- [ ] S-15 `servan watch` exporter half: Prometheus /metrics with {project,role,model,provider} labels; VERIFY OpenCode server API usage-endpoint shapes (blocker for S-13/S-15); Grafana dashboard JSON provisioned under examples/grafana/
