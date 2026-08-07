# Dogfooding servan on servan (S-12)

Date: 2026-08-07 · Scope: migrate this repo's dev flow onto servan (wiki/ + bd)

This repo now runs on the product it ships: an OKF wiki (`wiki/`, validated by
`servan lint`) and a Beads task ledger (`.beads/`, rendered by `servan status`).
This is the honest record of what that took and what broke.

## What was done

1. **Installed bd 1.1.2** (Windows) via the official PowerShell installer —
   prebuilt release, checksum verified. The installer does not touch PATH; added
   `…\AppData\Local\Programs\bd` to the user PATH manually.
2. **`bd init --skip-agents`** in the repo root (skip-agents: our AGENTS.md is
   harness-facing and must not be rewritten by a tool).
3. **Adopted the wiki skeleton manually** (`wiki/index.md`, `overview.md`,
   `log.md` with real content) — `servan new` is forbidden inside this repo by
   the layer rules, so the template was used as a reference, not executed.
4. **Migrated the remaining backlog** (S-13, S-14, S-15) into p4 task beads.
   `dev/BACKLOG.md` stays the milestone checklist; bd is the live ledger.
5. **`servan status`** now generates `wiki/status.md` from bd; **`servan lint`
   is clean** (exit 0) and a guard test (`tests/test_dogfood.py`) keeps it so.

## What dogfooding caught

- **servan's own commands disagreed.** `servan status` generated `status.md`
  with no OKF frontmatter, so `servan lint` (exit 3) rejected the file servan
  itself had just written. Fixed in both generators: `StatusService` and the
  shipped `template/tools/wiki-status.sh` (same latent bug in every end-user
  project) now emit `type: status` frontmatter (deterministic timestamps).
  This is exactly the class of bug dogfooding exists to find.
- **Version skew, no breakage.** BeadsLedger was written against bd ~0.60; the
  installed 1.1.2 passed the flag-compat probe (`--status in_progress|closed`)
  and its JSON still parses into TaskRecord. The probe earned its keep.

## Surprises worth knowing

- `bd init` **commits on its own** (`.beads/` config/hooks/metadata) and **sets
  `core.hooksPath` to `.beads/hooks` itself** — the template's warning that a
  custom hooksPath disables bd's hooks cuts the other way here: bd wins by
  default. It also appends beads/Dolt entries to the project `.gitignore`.
- bd shows a first-run **anonymous usage metrics** notice. Left enabled;
  `bd metrics off` opts out.
- Fresh shells don't see the new PATH entry until re-login — every script in
  this session prepended the install dir explicitly.
- bd's git hooks are POSIX sh; on Windows they run through Git for Windows'
  shim, which worked unmodified.
