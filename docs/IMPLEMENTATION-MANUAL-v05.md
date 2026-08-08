# servan v0.5 — implementation manual

Three new capabilities: **product interview → PBIs**, **standards + library (agents & skills)**,
**brownfield onboarding**. This file tells you what to copy where, what Kimi implements in which
order, and how to verify each step. Everything here is additive — no existing behaviour changes.

---

## 0. What is in this bundle

| Path in bundle | Goes to | What it is |
|---|---|---|
| `dev/BACKLOG-v05.md` | **append** to `dev/BACKLOG.md` | S-16…S-24 |
| `dev/DESIGN-v05-addendum.md` | **append** to `dev/DESIGN.md` (before the decisions log) | contracts §A–§E + decision lines |
| `src/servan/template/.opencode/agent/{product,surveyor}.md` | same path in repo | new roles (no code needed) |
| `src/servan/template/wiki/{vision,roadmap}.md` | same path in repo | OKF stubs owned by @product |
| `config/standards/{base,python,react-typescript}.toml` | `~/.config/servan/standards/` (Mac **and** PC) and `examples/standards/` in repo | the standards layer |
| `library/agents/math-sme.md`, `library/skills/react-quality/SKILL.md` | `~/.config/servan/library/` and `examples/library/` in repo | mother library seeds |

The backlog is an **append block, not a replacement**: only your repo knows the true checkbox
state of S-01…S-15.

Tip: make `~/.config/servan/` its own git repo — standards and library then version and travel
between PC and Mac like everything else.

---

## 1. Answers to the three questions this bundle implements

**Interview → PBIs → start.** Yes, with two roles rather than three. `product` runs the interview
*and* writes vision/roadmap/PBIs, because a separate "PM" agent would have the same working set
and the same failure mode — that is org-chart role-play, which the architecture avoids. It must be
`mode: primary`: subagents cannot talk to you. `architect` stays as the technical decomposer, one
feature at a time, just-in-time. A "sprint" is a **milestone** in `roadmap.md`; the sprint backlog
is the ready queue.

**Brownfield.** Deterministic first, judgment second: `servan survey` (pure Python) writes machine
facts into `raw/survey/`; `@surveyor` interprets them into `raw/survey/analysis.md` labelled
hypothesis-vs-verified; `@product` interviews you with that context; `@librarian` — still the only
wiki writer — ingests both into `wiki/`. The raw layer is exactly where machine output and
model hypotheses belong.

**Skills.** Verified against opencode.ai/docs/skills: OpenCode reads `.opencode/skills/`,
`~/.config/opencode/skills/`, **`.claude/skills/`**, `~/.claude/skills/`, and `.agents/skills/`,
loading each `SKILL.md` on demand through a native skill tool. So a Claude Code skill works
unmodified, servan invents no format, and the library just stores and copies standard folders.
Two ways in: `servan library add react-quality` (from your library, tracked in
`.servan.toml`), or drop any downloaded skill straight into a project's `.claude/skills/` and
OpenCode finds it.

---

## 2. Order of work (and why)

```
S-21 product+surveyor agents ── no Python; usable the moment you copy the files
S-16 standards layer ───────── pure rendering, no unknowns, unblocks house rules everywhere
S-17 agent library ─────────── reuses Renderer + ProjectConfig work from S-16
S-18 skill library ─────────── same loader; verbatim copy + lockfile
S-20 servan survey ─────────── deterministic; no dependency on init
S-19 servan init ───────────── consumes survey via --scan
S-22 servan check ──────────── consumes standards' machine-checkable half
S-23/24 template + docs wiring
```

Two config-model facts to expect: `ProjectConfig` uses `extra="forbid"`, so `standards = [...]`
and `[team]` are **rejected until S-16/S-17 extend the model** — that is validation working, not a
bug. And extra agents need a model mapping (`[roles] math-sme = "local/reasoner"`), which the
existing `TeamResolver` already supports because project `[roles]` merge over the profile.

---

## 3. Kimi Code prompts (add these to `dev/PROMPTS.md`)

**Session A — S-21, no code:**
> Read AGENTS.md, then dev/DESIGN.md §A (file ownership) and dev/BACKLOG.md S-21. Add the
> provided `product.md` and `surveyor.md` to `src/servan/template/.opencode/agent/`, add the
> `vision.md` and `roadmap.md` stubs to `src/servan/template/wiki/`, and patch the template's
> AGENTS.md with the ownership table. No Python changes. Verify with `uv run pytest -q`, commit
> `[S-21]`, tick the box, do not push. Summarize in ≤150 tokens.

**Session B — S-16 standards layer:**
> Implement S-16 per dev/DESIGN.md §B. Tests first: merge order (base→python), list
> concatenation with dedupe, scalar override, cycle detection → ConfigError, unknown standard →
> exit 2, and deterministic STANDARDS.md rendering. Follow the code standards in AGENTS.md: one
> public class per file, pydantic at boundaries, StandardsRenderer implements the existing
> Renderer ABC. Commit `[S-16]`, no push.

**Session C — S-17, Session D — S-18:**
> Implement S-17 (then S-18) per dev/DESIGN.md §C. LibraryLoader honours SERVAN_LIBRARY_DIR so
> tests use tmp_path. Agents get a provenance comment and the profile model; skill folders are
> copied byte-identical with no header injection, and installs are recorded in
> .servan/library.lock.json. Locally modified installs are preserved unless --force. Tests
> first, single commit, no push.

**Session E — S-20, Session F — S-19:**
> Implement S-20 (then S-19) per dev/DESIGN.md §D. Survey is pure Python: no LLM, no network,
> deterministic except one timestamp line, gitignore-aware, must work in a repo with no git
> history. Init never overwrites an existing file, is idempotent, and --dry-run changes nothing.
> Test both against a synthetic repo built in tmp_path. Tests first, single commit, no push.

**Session G — S-22/23/24:** same protocol, one task per session.

---

## 4. Manual steps (yours, not Kimi's)

```bash
mkdir -p ~/.config/servan/standards ~/.config/servan/library/agents ~/.config/servan/library/skills
cp config/standards/*.toml            ~/.config/servan/standards/
cp library/agents/math-sme.md         ~/.config/servan/library/agents/
cp -r library/skills/react-quality    ~/.config/servan/library/skills/
# optional but recommended:
cd ~/.config/servan && git init && git add -A && git commit -m "servan config: standards + library"
```

Import a downloaded Claude Code skill into the library (after S-18):

```bash
servan library import --claude ~/Downloads/some-skill      # copies the folder unchanged
servan library list
```

---

## 5. The two new workflows

### Greenfield with interview

```bash
servan new myapp && cd myapp
mkdir -p raw/design/checkout/v1 && cp ~/figma/*.png raw/design/checkout/v1/
$EDITOR .servan.toml     # standards = ["base","python"];  [team] skills = ["react-quality"]
servan sync              # renders STANDARDS.md + installs library items
opencode
```

1. `@designer: read raw/design/checkout/v1 and write specs/design/checkout-v1.md` → answer its
   questions.
2. Switch to `@product`, paste your project brief (long is fine) → answer round 1 (skip what you
   do not care about; defaults get recorded as `assumed:`) → it writes `wiki/vision.md`,
   `wiki/roadmap.md`, and the epic/feature backlog.
3. Review `wiki/roadmap.md` and `bd list` — this is your planning gate.
4. Give the orchestrator the standing order (autonomous loop; when `bd ready` empties, ask
   @architect to plan the next feature; when the backlog empties, ask @product to re-prioritize
   or declare the milestone done).

### Brownfield adoption of an existing repo

```bash
cd ~/code/legacy-app
git status                       # must be a git repo, clean enough to review a diff
servan init --scan --dry-run     # read the plan; nothing is written
servan init --scan               # non-destructive scaffold + raw/survey/inventory.md
servan sync
opencode
```

1. `@surveyor: analyse this codebase from raw/survey/` → `raw/survey/analysis.md`.
2. `@product` (interview, now grounded in the survey) → vision, roadmap, backlog.
3. `@librarian: ingest raw/survey/* and wiki/vision.md into the wiki` → `overview.md`,
   `modules/*`, `gotchas.md`, `index.md`, `log.md`.
4. `servan lint` → expect orphan warnings early; they resolve as `index.md` fills in.
5. First real bead. Suggested first one: add a characterization test to a hot-spot file — it
   proves the loop works and buys safety before any refactor.

---

## 6. Verification checklist

- **S-21:** `servan new demo` shows `product.md` + `surveyor.md`; `servan sync` gives both a real
  model; `servan lint` passes on the vision/roadmap stubs.
- **S-16:** `servan standards show python` prints base rules first, then python's, no duplicates;
  a deliberate `extends` cycle exits 2; `STANDARDS.md` identical on a second `sync`.
- **S-17/18:** `servan library list` shows agents and skills separately; after `add` +`sync`, the
  agent file has the provenance line and a real model, and the skill folder diffs clean against
  the library copy; edit an installed skill, re-`sync`, confirm your edit survives.
- **S-20:** run in servan itself — inventory names the real hot spots; second run differs only in
  the timestamp line.
- **S-19:** run twice in a scratch clone of a real project — second run is a no-op; an existing
  `AGENTS.md` is untouched and `AGENTS.servan.md` exists instead.
- **S-22:** `servan check` passes on servan; planted `print(` fails in `src/servan/config/` and
  passes in `src/servan/cli/`.
- **End to end:** brownfield-adopt one small real repo and let the team close one bead.

---

## 7. Risks worth watching

- **Interview fatigue** — if @product asks more than 7 questions or asks things the survey
  answered, tighten the prompt; the bounded-rounds rule is load-bearing.
- **Standards bloat** — rules that agents cannot act on are noise. Keep `base` under ~20 rules;
  move long-form guidance into a skill (that is exactly what `react-quality` is for).
- **Library drift** — a project's installed copy diverging from the library is fine and
  intentional; the lockfile hash tells you when it happened. Promote good local edits back with
  `servan library new agent <name>` rather than editing in place from a project.
- **Brownfield overreach** — the surveyor's analysis is hypotheses. Do not let the librarian
  promote unverified claims into the wiki; that rule is in the surveyor prompt for a reason.
