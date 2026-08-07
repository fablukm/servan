# servan — setup from zero (the SPOT walkthrough)

**This is the single entry-point document.** It walks you from a blank machine to a working multi-agent coding setup, step by step, no prior assumptions. The other two documents are *reference*, not required reading: `multi-agent-coding-sota-2026-07.md` (why the system is designed this way) and `setup-manual.md` (deep operations detail). When this walkthrough says "see manual §X", that's where it points.

**What you're building, in one paragraph:** a team of AI coding agents (architect, engineer, reviewer, tester, …) that runs on your own hardware. **OpenCode** is the harness the agents live in, **Ollama** serves the local AI models, **Beads** (`bd`) is the task ledger the agents work from, and **servan** — your own tool — wires it all together from a few TOML config files and keeps the project wiki honest. Everything is plain files in git, so you can always see what happened.

**You need:** your MacBook (Terminal + VS Code, both of which you have), ~80 GB free disk for models, a GitHub account, and about an hour. No Homebrew anywhere in this guide. Your shell is zsh — all snippets assume it.

---

## Part I — macOS setup

### Step 1 · Install uv (Python manager)

Open **Terminal** (or VS Code's integrated terminal — identical) and run:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

The installer puts `uv` in `~/.local/bin` and offers to update your shell config. Then reload and verify:

```bash
source ~/.zshrc
uv --version
```

✅ **Checkpoint:** you see a version number like `uv 0.x.y`. If you see `command not found`, run `echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc` and try again. You will never touch `pip` in this guide — `uv` does everything.

### Step 2 · Install Ollama (local model server)

1. Browser → **ollama.com/download** → Download for macOS
2. Open the downloaded file, drag **Ollama** into **Applications**, launch it once (it lives in the menu bar and serves models at `http://localhost:11434`)
3. Verify in Terminal:

```bash
ollama --version
```

✅ **Checkpoint:** version prints. The app starts automatically on login from now on.

### Step 3 · Pull the models (36 GB tier)

This downloads ~75 GB total — start it and get coffee:

```bash
ollama pull qwen3.6:27b          # engineer / orchestrator — current best local coder (77.2% SWE-bench Verified)
ollama pull deepseek-r1:32b      # architect — still the local reasoning/debugging specialist
ollama pull glm-4.7-flash        # reviewer / librarian — different model family, best local tool-caller
ollama pull qwen2.5-coder:7b     # tester — small & fast
ollama pull gemma3:27b           # design-image reader (vision)
```

> **Model notes (Aug 2026):** tags on ollama.com move fast — if a pull 404s, check the model's page on **ollama.com/library** for the exact current tag. If the engineer feels *slow* on your machine, swap it for `qwen3-coder:30b` (a sparse-MoE model, roughly 3× faster per token at slightly lower quality); if your projects are heavy multi-file agentic edits, `devstral:24b` is the purpose-built alternative. Swapping later takes one line: edit the id in `~/.config/servan/models.toml`, then run `servan sync` in each project — the doc you're reading never has to be right forever, the catalog does.

Then add the tuning settings to your shell config:

```bash
cat >> ~/.zshrc << 'EOF'
# --- Ollama tuning (servan) ---
export OLLAMA_FLASH_ATTENTION=1
export OLLAMA_KV_CACHE_TYPE=q8_0
export OLLAMA_MAX_LOADED_MODELS=2
export OLLAMA_KEEP_ALIVE=30m
export OLLAMA_CONTEXT_LENGTH=32768
EOF
source ~/.zshrc
```

Quit and reopen the Ollama menu-bar app so it picks these up. Quick test:

```bash
ollama run qwen2.5-coder:7b "say hi in one word"
```

✅ **Checkpoint:** you get a reply. Type `/bye` to exit.

### Step 4 · Install OpenCode (the agent harness)

```bash
curl -fsSL https://opencode.ai/install | bash
source ~/.zshrc
opencode --version
```

✅ **Checkpoint:** version prints. (If not: the installer tells you which directory it used — add it to PATH the same way as in Step 1.)

### Step 5 · Install Beads (`bd`, the task ledger)

No Homebrew, so grab the release binary directly. Browser → **github.com/gastownhall/beads/releases** → under the latest release's *Assets*, copy the link of the **darwin-arm64** file, then (replace the URL with the one you copied):

```bash
mkdir -p ~/.local/bin
curl -L -o /tmp/bd.tar.gz "PASTE-THE-DARWIN-ARM64-ASSET-URL-HERE"
tar -xzf /tmp/bd.tar.gz -C /tmp && mv /tmp/bd ~/.local/bin/bd && chmod +x ~/.local/bin/bd
bd --version
```

✅ **Checkpoint:** version prints. (Asset naming varies by release — if the archive layout differs, `tar -tzf /tmp/bd.tar.gz` shows what's inside; you want the `bd` executable in `~/.local/bin`.) If macOS blocks it as unverified: System Settings → Privacy & Security → *Allow Anyway*, run once more.

### Step 6 · Get servan itself

First time (from the scaffold zip you have; after Part II exists, you'll `git clone` instead):

```bash
mkdir -p ~/code && cd ~/code
unzip ~/Downloads/servan-scaffold.zip -d ~/code   # → ~/code/servan
cd ~/code/servan
uv sync                        # creates .venv, installs typer + dev deps
uv run pytest -q               # expect: 11 passed, 14 skipped
uv tool install --editable .   # gives you a global `servan` command
servan --version
```

✅ **Checkpoint:** tests green, `servan 0.1.0` prints. (`uv tool install` also lives in `~/.local/bin` — already on PATH from Step 1.)

### Step 7 · Global configuration

One folder holds all machine-level config; projects only pick profiles from it.

```bash
mkdir -p ~/.config/servan && chmod 700 ~/.config/servan
cp ~/code/servan/examples/config/*.toml ~/.config/servan/
```

Create your secrets file (keys only — this file never goes near git):

```bash
cat > ~/.config/servan/secrets.env << 'EOF'
export ANTHROPIC_API_KEY=""
export OPENAI_API_KEY=""
export DEEPSEEK_API_KEY=""
export MOONSHOT_API_KEY=""
export DASHSCOPE_API_KEY=""
export ZAI_API_KEY=""
EOF
chmod 600 ~/.config/servan/secrets.env
echo 'source ~/.config/servan/secrets.env' >> ~/.zshrc
source ~/.zshrc
```

Paste in whichever keys you have (empty is fine — the `local-36gb` profile needs none). Open the folder in VS Code to look around: `code ~/.config/servan` — `providers.toml` (where models are served), `models.toml` (which models exist), `profiles.toml` (which role gets which model), `prices.toml` (what tokens cost, for the dashboard later). Full semantics: manual §3.

### Step 8 · Your first project

```bash
cd ~/code
servan new demo && cd demo
```

> **If you see "not implemented yet — S-03":** that command is one of the tasks your AI team will build. Until then, the manual fallback does the same thing:
> ```bash
> cp -R ~/code/servan/template ~/code/demo && cd ~/code/demo
> git init && git config core.hooksPath .githooks
> chmod +x .githooks/* tools/*
> bd init
> servan sync
> git add -A && git commit -m "[init] servan scaffold"
> ```

Then:

```bash
servan sync     # prints the role → model table
bd prime        # the ledger introduces itself
```

✅ **Checkpoint:** `servan sync` lists roles like `engineer -> ollama/qwen3-coder:30b`.

### Step 9 · VS Code workflow

```bash
code ~/code/demo
```

- Everything happens in the **integrated terminal** (same zsh, same PATH): run `opencode` there and the agent TUI appears next to your editor
- Recommended extension: **Even Better TOML** (config editing); markdown preview is built in (`⌘⇧V`) — that's your wiki reader until you set up anything fancier
- The loop in one breath: describe a goal → architect proposes spec + beads → you skim and approve → say "go" → review the PR at the end. Cheatsheet: manual §7.4. Your first prompt inside `opencode`:
  > @architect: bootstrap wiki/overview.md from this repo, then propose 3 starter beads

---

## Part II — put it on GitHub (the showcase)

The point: a public repo where companies can see the tool, the architecture docs, and the AI-team workflow that built it.

### Step 1 · SSH key (once per machine)

```bash
ssh-keygen -t ed25519 -C "your@email"        # Enter three times is fine
pbcopy < ~/.ssh/id_ed25519.pub               # copies the public key
```

Browser → **github.com/settings/keys** → *New SSH key* → paste → save. Verify:

```bash
ssh -T git@github.com
```

✅ **Checkpoint:** "Hi USERNAME! You've successfully authenticated…"

### Step 2 · Create the repo and push

Browser → **github.com/new** → name `servan`, **Public**, no README/license/gitignore (you have them) → *Create repository*. Then:

```bash
cd ~/code/servan
git init 2>/dev/null; git add -A
git commit -m "[init] servan: scaffold, docs, and AI-team dev setup"
git branch -M main
git remote add origin git@github.com:YOUR-USERNAME/servan.git
git push -u origin main
```

**Before pushing, sanity-check what's public:** `git status` must never show `secrets.env` (it lives in `~/.config/servan/`, outside the repo — by design). The repo's `.gitignore` already excludes `.venv/` and caches.

### Step 3 · Make it presentable + reusable

- **Docs in the repo:** copy this walkthrough and the two reference docs into `docs/` and push — the research trail *is* part of the showcase
- **Template switch:** repo → *Settings* → tick **Template repository**. New projects then come from *Use this template* (or later `gh repo create --template`), with clean history
- **Recruiter polish:** pin the repo on your profile, add topics (`ai-agents`, `llm`, `developer-tools`, `python`), and make the README's first screen count — it already opens with the layer map and the "AI tool built by an AI team" hook
- Dev flow from now on: Kimi Code commits locally per the `[S-xx]` protocol, **you** review and `git push` — pushes stay human, which is itself a nice line in the README

### Step 4 · Loading it on any machine

```bash
git clone git@github.com:YOUR-USERNAME/servan.git ~/code/servan
cd ~/code/servan && uv sync && uv run pytest -q && uv tool install --editable .
```

Plus Step 7 from Part I (config folder + secrets — those are per-machine, never in git).

---

## Part III — Windows 10 PC

The reliable path on Windows 10 is **WSL2** (a real Ubuntu inside Windows): every command becomes identical to the Mac, and VS Code connects into it natively. Native-Windows variant at the end.

### Step 1 · WSL2 + Ubuntu

PowerShell **as Administrator** (Start → type `powershell` → *Run as administrator*):

```powershell
wsl --install
```

Reboot when asked; Ubuntu opens on first login and asks you to create a Linux username/password. (Requires a fully updated Windows 10 — if the command isn't recognized, run Windows Update first; fallback instructions: **aka.ms/wslinstall**.)

✅ **Checkpoint:** you have an Ubuntu terminal prompt.

### Step 2 · Tools inside Ubuntu (same as Mac, Linux flavor)

```bash
# uv
curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.bashrc
# Ollama (Linux install script; installs a background service)
curl -fsSL https://ollama.com/install.sh | sh
# OpenCode
curl -fsSL https://opencode.ai/install | bash && source ~/.bashrc
# Beads: releases page → linux-amd64 asset → same dance as Mac Step 5, into ~/.local/bin
```

**Models on this PC — decide once:** if it has an NVIDIA GPU, the Ollama installer wires it up through WSL2 automatically (just update the Windows NVIDIA driver) and you can `ollama pull` a tier that fits its VRAM/RAM (manual §6.1 of the report has the tiers). If it's a modest machine, **skip local models entirely** and run this PC on the `online-mixed` profile — that's a one-line difference in Step 4.

### Step 3 · Clone + install servan

New machine → new SSH key (Part II Step 1, but use `cat ~/.ssh/id_ed25519.pub` instead of `pbcopy`, and copy it manually). Then:

```bash
git clone git@github.com:YOUR-USERNAME/servan.git ~/code/servan
cd ~/code/servan && uv sync && uv run pytest -q && uv tool install --editable .
```

### Step 4 · Config on this machine

```bash
mkdir -p ~/.config/servan && chmod 700 ~/.config/servan
cp ~/code/servan/examples/config/*.toml ~/.config/servan/
# secrets: same block as Mac Step 7 (echo into ~/.bashrc instead of ~/.zshrc)
```

If this PC runs without local models: open `~/.config/servan/…` and set each project's `.servan.toml` to `profile = "online-mixed"` — done.

### Step 5 · VS Code into WSL

Install the **WSL** extension (by Microsoft) in your Windows VS Code → `Ctrl⇧P` → *WSL: Connect to WSL* → open `~/code/...`. The integrated terminal is now Ubuntu; everything from Part I Step 9 applies unchanged.

> **Variant — Ollama as a native Windows app instead:** install from ollama.com/download (Windows), then tell the WSL side where to find it. On Windows 10, WSL reaches the Windows host at the gateway IP:
> ```bash
> WIN_IP=$(ip route show default | awk '{print $3}')
> sed -i "s#http://localhost:11434#http://$WIN_IP:11434#" ~/.config/servan/providers.toml
> ```
> (And in Windows, set the Ollama app to listen on all interfaces via its settings / `OLLAMA_HOST=0.0.0.0`.) Use this if you want the models managed from the Windows side.

---

## Part IV — keeping it fresh (2 minutes, weekly-ish)

| What | How |
|---|---|
| servan itself | `cd ~/code/servan && git pull && uv sync` (editable install picks changes up automatically) |
| uv | `uv self update` |
| OpenCode | `opencode upgrade` |
| Ollama app | macOS/Windows app auto-updates; WSL: re-run the install script |
| Models | `ollama pull <tag>` refreshes; **never swap the engineer without `servan canary`** (manual §9) |
| bd | re-download the release binary (same as install) |
| Config | after any TOML edit: `servan sync` in each project |

## Troubleshooting, dummies edition

- **`command not found`** → new terminal, or `source ~/.zshrc` (Mac) / `source ~/.bashrc` (WSL); check `echo $PATH` contains `~/.local/bin`
- **`connection refused` on 11434** → Ollama app isn't running (Mac: menu bar; WSL: `ollama serve` in a spare terminal)
- **`servan: missing …/providers.toml`** → Part I Step 7 wasn't done on this machine
- **`not implemented yet — S-xx`** → that feature is on your AI team's backlog; use the boxed fallback or build it next
- **Hook says `permission denied`** → `chmod +x .githooks/* tools/*` in the project
- **Push rejected / auth failed** → `ssh -T git@github.com`; remote must be the `git@github.com:` form, not `https://`
- **Model replies are garbage/slow** → `ollama ps` (is the right model loaded? 100% GPU?); close RAM-hungry apps; smaller ctx before smaller model

*Deferred by decision (unchanged): the sensitive-data scrubbing pipeline for sending council records to frontier APIs from private repos.*
