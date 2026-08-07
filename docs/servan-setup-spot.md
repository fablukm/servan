# servan — Setup from scratch (Single Point of Truth)

**Follow this document top to bottom. Every other doc is reference.**
Assumptions: MacBook Pro (Apple Silicon, 36 GB), macOS, **zsh** (the default), **VS Code**, **no Homebrew**, **uv instead of pip**. Time: ~1h active + ~1h model downloads. Where this doc ends, the deep references begin: `multi-agent-coding-sota-2026-07.md` (why everything is the way it is) and `setup-manual.md` (operations reference — note: some of its listings show brew; the brew-free way is always the one here).

**What you're building, in one breath:** a team of AI coding agents (architect, engineer, reviewer, tester, …), each running on its own local model via **Ollama**, orchestrated by **OpenCode**, remembering things in a **wiki** in git, tracking work in a **Beads** task ledger — all configured through **servan**, your own small CLI, which is itself being built by **Kimi Code (K3)**.

---

## Step 0 — Terminal & VS Code basics (5 min)

1. Open **Terminal** (⌘-Space → "Terminal"). Confirm zsh:
   ```zsh
   echo $SHELL
   ```
   ✓ Check: ends in `/zsh`. (If not, all commands still work; config lines go into your shell's rc file instead of `~/.zshrc`.)
2. Install Apple's command-line tools (gives you `git` — no Homebrew needed):
   ```zsh
   xcode-select --install
   ```
   A dialog appears; click Install. If it says "already installed", perfect.
   ✓ Check: `git --version` prints a version.
3. VS Code: install from code.visualstudio.com if you haven't. Then in VS Code press ⌘⇧P → type **"Shell Command: Install 'code' command in PATH"** → Enter.
   ✓ Check: in Terminal, `code --version` prints a version.
4. Recommended VS Code extensions (⌘⇧X): **Python** (Microsoft), **Ruff**, **Even Better TOML**. Optional: any Markdown-preview extension — that's your wiki reader before Wiki.js exists.

## Step 1 — uv (Python, without pip or Homebrew) (3 min)

```zsh
curl -LsSf https://astral.sh/uv/install.sh | sh
```
The installer adds `~/.local/bin` to your PATH (it edits `~/.zshrc` or tells you the line to add). Reload:
```zsh
source ~/.zshrc
uv --version
```
✓ Check: a version prints. Now let uv manage Python itself — no system Python involved:
```zsh
uv python install 3.12
```

## Step 2 — Ollama (the local model server) (5 min + downloads)

1. Download the macOS app from **ollama.com** → open the `.dmg` → drag to Applications → launch it once (menu-bar icon appears; the server now starts on login).
   ✓ Check: `ollama --version` in Terminal.
2. Tune the server. The menu-bar app reads settings via `launchctl` (per Ollama's FAQ — verify there if anything misbehaves):
   ```zsh
   launchctl setenv OLLAMA_FLASH_ATTENTION 1
   launchctl setenv OLLAMA_KV_CACHE_TYPE q8_0
   launchctl setenv OLLAMA_MAX_LOADED_MODELS 2
   launchctl setenv OLLAMA_KEEP_ALIVE 30m
   launchctl setenv OLLAMA_CONTEXT_LENGTH 32768
   ```
   Then quit the Ollama menu-bar app and reopen it.
3. Pull the 36 GB-tier models (☕ ~75 GB total — start it and walk away):
   ```zsh
   ollama pull qwen3-coder:30b      # engineer + orchestrator
   ollama pull deepseek-r1:32b      # architect (loaded alone while planning)
   ollama pull gpt-oss:20b          # reviewer + librarian
   ollama pull qwen2.5-coder:7b     # tester
   ollama pull gemma3:27b           # designer (vision)
   ```
   ✓ Check: `ollama run qwen3-coder:30b "say hi"` answers, and `ollama ps` shows it on GPU.

## Step 3 — OpenCode (the agent harness) (2 min)

```zsh
curl -fsSL https://opencode.ai/install | bash
source ~/.zshrc
opencode --version
```
✓ Check: version prints. No account or sign-in needed for local models.

## Step 4 — Beads / `bd` (the task ledger) (5 min)

No Homebrew, so grab the binary from GitHub Releases:

1. Browser → **github.com/gastownhall/beads/releases** → latest release → download the **darwin-arm64** asset (exact filename per the page; the README may also offer a curl one-liner — that's fine too).
2. ```zsh
   mkdir -p ~/.local/bin
   mv ~/Downloads/bd-darwin-arm64 ~/.local/bin/bd     # adjust filename
   chmod +x ~/.local/bin/bd
   xattr -d com.apple.quarantine ~/.local/bin/bd 2>/dev/null || true   # macOS Gatekeeper
   ```
   (`~/.local/bin` is already on your PATH from Step 1.)
   ✓ Check: `bd --version` prints; `bd prime` prints its self-guidance.

## Step 5 — Get servan and make it a real command (5 min)

1. Unzip `servan-scaffold.zip` (or clone it once it's on GitHub) into `~/code/servan`:
   ```zsh
   mkdir -p ~/code && cd ~/code
   unzip ~/Downloads/servan-scaffold.zip -d ~/code
   cd ~/code/servan
   ```
2. Install dependencies and run the test suite — all with uv:
   ```zsh
   uv sync
   uv run pytest -q
   ```
   ✓ Check: **`11 passed, 14 skipped`**. The skips are intentional (features Kimi will build).
3. Put `servan` on your PATH as a tool:
   ```zsh
   uv tool install --editable .
   servan --version
   ```
   ✓ Check: `servan 0.1.0`. (If `uv tool install` complains, fallback: `echo 'alias servan="uv run --project ~/code/servan servan"' >> ~/.zshrc && source ~/.zshrc`.)
4. Push it to GitHub (browser: github.com → New repository → `servan`, empty, no README):
   ```zsh
   git init -b main && git add -A && git commit -m "[init] servan scaffold"
   git remote add origin https://github.com/YOURNAME/servan.git
   git push -u origin main
   ```

## Step 6 — Global config (one time, all projects) (10 min)

```zsh
mkdir -p ~/.config/servan && chmod 700 ~/.config/servan
cp ~/code/servan/examples/config/*.toml ~/.config/servan/
```
That gives you the four layers: `providers.toml` (where models live) · `models.toml` (what exists) · `profiles.toml` (which role gets which model) · `prices.toml` (what tokens cost). Open them in VS Code and skim — they're pre-filled for the 36 GB local tier:
```zsh
code ~/.config/servan
```
API keys (only needed for the online profile — skip if staying local for now):
```zsh
touch ~/.config/servan/secrets.env && chmod 600 ~/.config/servan/secrets.env
code ~/.config/servan/secrets.env    # add lines like: export ANTHROPIC_API_KEY="sk-ant-..."
echo 'source ~/.config/servan/secrets.env' >> ~/.zshrc && source ~/.zshrc
```

## Step 7 — Your first project (10 min)

`servan new` is backlog task S-03 — until Kimi ships it, bootstrap manually (same result, six commands):

```zsh
cp -R ~/code/servan/template ~/code/myproject
cd ~/code/myproject
git init -b main
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit tools/wiki-status.sh
bd init
servan sync
git add -A && git commit -m "[init] servan scaffold"
```
✓ Check: `servan sync` printed a role→model table (`engineer -> ollama/qwen3-coder:30b` …) and `opencode.json` exists. *(After S-03 lands, all of this becomes: `servan new myproject`.)*

Open it properly:
```zsh
code ~/code/myproject
```
In VS Code's integrated terminal (⌃`):
```zsh
opencode
```
First conversation (type these to the agent):
- `@architect: bootstrap wiki/overview.md from this repo, then propose 3 beads`
- Review what it wrote (the spec, the `bd create` commands) — this is **Gate 1/2**: edit or approve
- `work the ready queue` — engineer→tester→reviewer run per bead; answer any permission prompts
- When done: check `git log --oneline`, read `wiki/log.md`, and review the diff — **Gate 3**

Capture ideas anytime, from any terminal, without interrupting anything:
```zsh
bd create "idea: dark mode" -t task -p 4
```

## Step 8 — Let Kimi Code (K3) build servan itself (15 min)

1. Install Kimi Code CLI per its official README (**github.com/MoonshotAI/kimi-code** — it ships as a single binary with an install one-liner; the exact command lives there). Sign in with your Moonshot/Kimi account (Kimi Code model access is a membership benefit).
2. Select **K3** as the model (the `/model` command, or per the README).
3. ```zsh
   cd ~/code/servan
   ```
   Open `dev/PROMPTS.md`, copy the **Kickoff** prompt, paste it into Kimi Code. It will read `AGENTS.md` (including the layer rules that keep it from confusing the tool it's *building* with the agents that tool *configures*), then implement S-03 test-first and commit.
4. Your loop as the human: one backlog task per session (use the **Resume** prompt), review each `[S-xx]` commit in VS Code's Source Control panel, push when satisfied. When S-03 lands, retire the manual bootstrap in Step 7.

## Step 9 — Daily rhythm (cheat sheet)

- **Capture** (anytime): `bd create "idea: …" -t task -p 4`
- **Triage** (start of a work block): `@architect: groom the backlog`
- **Plan → Gate:** architect writes spec + beads; you skim and mark ready
- **Run:** `work the ready queue` — walk away; escalations park as p0 beads
- **Ship → Gate:** review the PR/diff against the spec; merge to `main` (only you push)
- **Weekly:** `servan lint` (once S-07 lands) · re-triage backlog · skim `wiki/log.md` · `servan canary` before any model swap
- **Read the wiki:** VS Code Markdown preview on `wiki/` is your reader today; Wiki.js on a Pi and the Grafana dashboard are later chapters (`setup-manual.md` §7.1 and §11)

## If something breaks (top 5)

1. **`command not found`** → `source ~/.zshrc`; confirm `~/.local/bin` is in `echo $PATH`
2. **Agent produces malformed tool calls / stalls** → that role's model is the problem: point it at `gpt-oss:20b` in `~/.config/servan/profiles.toml`, run `servan sync`
3. **Mac swaps / everything crawls** → `ollama ps`; you loaded two big models — lower `OLLAMA_CONTEXT_LENGTH` (launchctl, Step 2) or keep the plan/build phases sequential
4. **`servan sync` says config error** → the message names the exact file and key; the layers are validated against each other on purpose
5. **`bd` blocked by macOS ("unidentified developer")** → the `xattr` line in Step 4, or right-click → Open once

*Deferred by decision (tracked, not forgotten): sensitive-data scrubbing before escalating anything to cloud frontier models from private repos.*
