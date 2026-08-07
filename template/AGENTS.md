# AGENTS.md — project protocol (read before any task)

You are one role in a multi-agent coding team orchestrated by OpenCode. Roles, models,
and permissions come from `.opencode/agent/`; this file is the shared law.

## Wiki protocol (memory)
- Before any task: read `wiki/index.md`, then only the pages it points you to.
- Never re-derive what the wiki already knows; if the wiki is wrong, say so in your report.
- Only the **librarian** writes `wiki/` (this binds agents — human commits are ground
  truth and override everyone). Ingest ≤15 files per pass; append one line to `wiki/log.md`.
- Every wiki page carries OKF v0.1 frontmatter: required `type` (+ title/tags/timestamp)
  plus the servan extension (`status`, typed `links`). Cross-reference pages with standard
  markdown links. `servan lint` validates all of it. Tracked spec: OKF v0.1 (Draft).
- `wiki/status.md` is hook-generated from the ledger — nobody edits it.

## Communication protocol
1. No agent talks to another agent. Orchestrator → subagent → one distilled result.
2. Your entire input is your bead (goal, acceptance criteria, files-in-scope, wiki links).
   If it is insufficient, fail fast with a question in your report — do not improvise.
3. Your entire output is: commit(s)/diff + a closing report ≤150 tokens
   (done · verified · proposed wiki updates · surprises) via `bd close <id> --reason`.
4. Serialize writes: stay inside your bead's files-in-scope. Parallel reads are free.
5. Would-be questions to other agents = wiki gaps; note them for the librarian.

## Backlog & tasks (Beads)
- Session start: run `bd prime` (canonical, self-updating CLI guidance); prefer `--json` output.
- Backlog = priority 4 by convention (`bd create "idea: …" -t task -p 4`). Types are
  bug|feature|task|epic|chore; priorities 0 (critical) → 4 (backlog).
- Anyone (including the human, any session) may create backlog beads.
- Only the architect promotes backlog → ready (triage: dedupe vs wiki, re-prioritize,
  split, `bd dep add` links). `bd ready` is the authoritative execution order.
- Claim before working: `bd update <id> --claim`. Close: `bd close <id> --reason "…"`.
- Durable knowledge goes to the wiki via the librarian — not `bd remember` — so the
  semantic store stays single.

## Git & delivery
- Feature branch per initiative `feat/<name>`; `main` is human-only.
- Commits: `[<bead-id>] summary` (ids look like `bd-a1b2`), only after tests pass.
  The pre-commit hook runs `bd sync` and refreshes `wiki/status.md`. **No agent ever pushes.**
- Librarian commits wiki separately: `[wiki] ingest <bead-id>`.

## Council (contested designs)
- Architect tags specs `decision_class: irreversible|contested` → orchestrator runs
  `servan council specs/<topic>.md`. Minutes land in `wiki/meetings/`. Work by default,
  meet by exception.

## Design inputs
- `raw/design/<feature>/v1,v2/…` is append-only — never overwrite a version.
- Designer output: `specs/design/<feature>-vN.md` with an OKF `supersedes` link;
  architect emits delta beads only.
