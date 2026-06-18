#!/usr/bin/env bash
#
# cloud-setup.sh — make a Claude Code on the web container resemble Will's local dev env.
#
# WHY this exists: web/cloud sessions start from a stock Ubuntu container that is missing the
# tools, git ergonomics, and AI-agent rules that shell-configs + ai-agent-rules give a local
# machine. This script closes that gap.
#
# HOW it's meant to be used: it lives here for version control, but its real home is the Claude
# iOS app's SessionStart hook (paste the contents there). It therefore must be non-interactive,
# best-effort, idempotent, and never block the session from starting.
#
# SAFETY: the cloud harness owns the git identity ("Claude") + SSH commit signing (/tmp/code-sign)
# and the Claude hooks/settings under ~/.claude. This script NEVER touches identity, signing,
# core.hooksPath, ~/.claude/settings.json, or the harness hook scripts. Git extras are layered via
# an [include]; AGENTS.md rules + skills are added alongside (never over) the harness ones.
#
# Re-run safe. After a fresh web session, re-running re-applies the git include (the harness may
# regenerate ~/.gitconfig on session start).

set -uo pipefail

# --- tiny helpers -----------------------------------------------------------------------------
log()  { printf '  %s\n' "$*"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m✗\033[0m %s\n' "$*"; }
hdr()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# Run as root directly, else via sudo when present.
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  if have sudo; then SUDO="sudo"; else warn "not root and no sudo — apt steps may fail"; fi
fi

LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"
case ":$PATH:" in *":$LOCAL_BIN:"*) : ;; *) export PATH="$LOCAL_BIN:$PATH" ;; esac

INSTALLED=(); SKIPPED=(); FAILED=()
record() { case "$1" in ok) INSTALLED+=("$2");; skip) SKIPPED+=("$2");; fail) FAILED+=("$2");; esac; }

# apt-get update only once, and only if we end up needing apt.
APT_UPDATED=0
apt_update_once() {
  [ "$APT_UPDATED" -eq 1 ] && return 0
  if $SUDO apt-get update -y >/dev/null 2>&1; then APT_UPDATED=1; return 0; fi
  return 1
}
apt_install() { apt_update_once && $SUDO apt-get install -y "$@" >/dev/null 2>&1; }

# Locate the two source repos (web env clones in-scope repos under /home/user). Overridable.
find_repo() {
  local override="$1" name="$2" c
  if [ -n "$override" ] && [ -d "$override" ]; then printf '%s\n' "$override"; return 0; fi
  for c in "/home/user/$name" "$HOME/$name" "/home/user/Development/Personal/$name"; do
    [ -d "$c" ] && { printf '%s\n' "$c"; return 0; }
  done
  return 1
}
SHELL_CONFIGS_DIR="$(find_repo "${SHELL_CONFIGS_DIR:-}" shell-configs || true)"
AI_RULES_DIR="$(find_repo "${AI_RULES_DIR:-}" ai-agent-rules || true)"

printf '\033[1mcloud-setup.sh\033[0m — aligning this container with Will'\''s local dev env\n'

# === 1. Python 3.14 ===========================================================================
hdr "Python 3.14 (both repos pin .python-version = 3.14)"
if have uv && uv python find 3.14 >/dev/null 2>&1; then
  ok "Python 3.14 already available via uv"; record skip "python3.14"
elif have python3.14; then
  ok "python3.14 already on PATH"; record skip "python3.14"
elif have uv && uv python install 3.14 >/dev/null 2>&1; then
  ok "installed Python 3.14 via uv"; record ok "python3.14"
else
  log "uv route unavailable — trying deadsnakes apt PPA"
  if apt_install software-properties-common \
     && $SUDO add-apt-repository -y ppa:deadsnakes/ppa >/dev/null 2>&1 \
     && APT_UPDATED=0 apt_install python3.14; then
    ok "installed python3.14 via deadsnakes"; record ok "python3.14"
  else
    warn "could not install Python 3.14"; record fail "python3.14"
  fi
fi

# === 2. CLI tools =============================================================================
hdr "CLI tools"

# Download a file to a path (curl or wget). $1=url $2=dest
fetch() {
  if have curl; then curl -fsSL "$1" -o "$2"; elif have wget; then wget -qO "$2" "$1"; else return 1; fi
}

# Simple apt-only tools: name == binary == apt package
for tool in shellcheck sqlite3 direnv fzf; do
  if have "$tool"; then ok "$tool already present"; record skip "$tool"
  elif apt_install "$tool"; then ok "installed $tool"; record ok "$tool"
  else warn "failed to install $tool"; record fail "$tool"; fi
done

# bat — Ubuntu ships the binary as `batcat`; expose it as `bat`.
if have bat; then ok "bat already present"; record skip "bat"
elif have batcat || apt_install bat; then
  have batcat && ln -sf "$(command -v batcat)" "$LOCAL_BIN/bat"
  if have bat; then ok "installed bat (batcat → ~/.local/bin/bat)"; record ok "bat"
  else warn "bat installed but not resolvable"; record fail "bat"; fi
else warn "failed to install bat"; record fail "bat"; fi

# gh — try apt, then the official GitHub CLI apt repo.
if have gh; then ok "gh already present"; record skip "gh"
elif apt_install gh; then ok "installed gh"; record ok "gh"
else
  if fetch https://cli.github.com/packages/githubcli-archive-keyring.gpg /tmp/gh.gpg \
     && $SUDO install -m 0644 /tmp/gh.gpg /usr/share/keyrings/githubcli-archive-keyring.gpg; then
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      | $SUDO tee /etc/apt/sources.list.d/github-cli.list >/dev/null
    APT_UPDATED=0
    if apt_install gh; then ok "installed gh (via GitHub apt repo)"; record ok "gh"
    else warn "failed to install gh"; record fail "gh"; fi
  else warn "failed to add gh apt repo"; record fail "gh"; fi
fi

# delta — apt package is git-delta; fallback to the latest .deb from releases.
if have delta; then ok "delta already present"; record skip "delta"
elif apt_install git-delta && have delta; then ok "installed delta (git-delta)"; record ok "delta"
else
  deb_url="$(fetch https://api.github.com/repos/dandavison/delta/releases/latest /dev/stdout 2>/dev/null \
            | grep -oE '"browser_download_url": *"[^"]*_amd64\.deb"' | head -1 | cut -d'"' -f4 || true)"
  if [ -n "$deb_url" ] && fetch "$deb_url" /tmp/delta.deb && $SUDO dpkg -i /tmp/delta.deb >/dev/null 2>&1; then
    ok "installed delta (.deb from releases)"; record ok "delta"
  else warn "failed to install delta"; record fail "delta"; fi
fi

# shfmt — go is present; install and expose in ~/.local/bin.
if have shfmt; then ok "shfmt already present"; record skip "shfmt"
elif have go && GOBIN="$LOCAL_BIN" go install mvdan.cc/sh/v3/cmd/shfmt@latest >/dev/null 2>&1 && have shfmt; then
  ok "installed shfmt (go install)"; record ok "shfmt"
elif apt_install shfmt && have shfmt; then ok "installed shfmt (apt)"; record ok "shfmt"
else warn "failed to install shfmt"; record fail "shfmt"; fi

# just — official installer drops a prebuilt binary into ~/.local/bin (no compile).
if have just; then ok "just already present"; record skip "just"
elif apt_install just && have just; then ok "installed just (apt)"; record ok "just"
elif fetch https://just.systems/install.sh /tmp/just-install.sh \
     && bash /tmp/just-install.sh --to "$LOCAL_BIN" >/dev/null 2>&1 && have just; then
  ok "installed just (prebuilt)"; record ok "just"
else warn "failed to install just"; record fail "just"; fi

# eza — prebuilt tarball from releases (avoids a slow cargo compile).
if have eza; then ok "eza already present"; record skip "eza"
elif apt_install eza && have eza; then ok "installed eza (apt)"; record ok "eza"
elif fetch https://github.com/eza-community/eza/releases/latest/download/eza_x86_64-unknown-linux-gnu.tar.gz /tmp/eza.tgz \
     && tar -xzf /tmp/eza.tgz -C "$LOCAL_BIN" eza >/dev/null 2>&1 && have eza; then
  ok "installed eza (prebuilt)"; record ok "eza"
else warn "failed to install eza"; record fail "eza"; fi

# difit — no install; runs on demand via npx.
if have node || have npx; then ok "difit available on demand via: npx -y difit"; record skip "difit(npx)"
else warn "node/npx missing — difit unavailable"; record fail "difit(npx)"; fi

# === 3. Non-identity git settings =============================================================
hdr "Git settings (identity & signing preserved)"
GIT_EXTRAS="$HOME/.gitconfig.cloud-extras"
# Safe subset of shell-configs/.../shared.gitconfig. Deliberately OMITS [user], [gpg],
# commit.gpgsign, core.hooksPath, [filter "lfs"], and include of ~/.gitconfig.local so the
# harness identity/signing stay authoritative.
cat > "$GIT_EXTRAS" <<'GITEOF'
# Managed by shell-configs/cloud-setup.sh — non-identity git ergonomics for cloud sessions.
# Layered via [include] from ~/.gitconfig; harness identity & commit signing are untouched.
[alias]
	b = branch
	cp = cherry-pick
	plre = pull --rebase
	last = log -1 HEAD
	praise = blame
	lg = log --all --graph --abbrev-commit --date=relative --pretty=format:'%C(bold blue)%h - %C(reset)%C(green)(%ar)%C(reset) - %s %C(dim)- %an%C(reset)%C(yellow)%d'
	out = log origin..HEAD
	tree = log --graph --decorate --pretty=oneline --abbrev-commit
	hist = log --pretty=format:"%C(yellow)%h %ad%Creset | %s%C(bold red)%d%Creset [%C(bold blue)%an%Creset]" --graph --date=short
	whatis = show -s --pretty='tformat:%h (%s, %ad)' --date=short
	lastauthor = log -1 --format='%Cgreen%an <%ae>'
	lb = branch -v --sort=committerdate
	ch = diff --name-status -r
	ignored = "!git ls-files --others --exclude-standard"
	track = !sh -c 'git branch --track "$0" "origin/$0" && git checkout "$0"'
	cleanup-branches = !sh -c 'git branch --merged | grep -v ^* | xargs -n 1 git branch -d'
[core]
	editor = vim
	pager = delta
[interactive]
	diffFilter = delta --color-only
[delta]
	navigate = true
	line-numbers = true
	side-by-side = true
	syntax-theme = Dracula
[push]
	default = current
	autoSetupRemote = true
[pull]
	rebase = true
[rebase]
	autostash = true
	autosquash = true
[fetch]
	prune = true
[branch]
	autosetupmerge = true
[status]
	showUntrackedFiles = all
[log]
	mailmap = true
[init]
	defaultBranch = main
[rerere]
	enabled = true
[merge]
	conflictStyle = diff3
	summary = true
[diff]
	renames = true
	indentHeuristic = on
[color]
	ui = auto
GITEOF
ok "wrote $GIT_EXTRAS"

# If delta isn't installed, don't leave core.pager pointing at a missing binary.
if ! have delta; then
  sed -i '/pager = delta/d; /diffFilter = delta/d' "$GIT_EXTRAS"
  log "delta absent — left pager unset in extras"
fi

GITCONFIG="$HOME/.gitconfig"
if [ -f "$GITCONFIG" ] && grep -qF ".gitconfig.cloud-extras" "$GITCONFIG"; then
  ok "$GITCONFIG already includes cloud-extras"; record skip "git-include"
else
  printf '\n[include]\n\tpath = %s/.gitconfig.cloud-extras\n' "$HOME" >> "$GITCONFIG"
  ok "added [include] of cloud-extras to ~/.gitconfig"; record ok "git-include"
fi

# === 4. AGENTS.md behavioral rules + shared skills ============================================
hdr "Agent rules & skills (harness settings/hooks preserved)"
if [ -n "$AI_RULES_DIR" ] && [ -f "$AI_RULES_DIR/src/ai_rules/config/AGENTS.md" ]; then
  CFG="$AI_RULES_DIR/src/ai_rules/config"

  ln -sfn "$CFG/AGENTS.md" "$HOME/AGENTS.md"
  ok "linked ~/AGENTS.md → ai-agent-rules behavioral rules"; record ok "AGENTS.md"

  mkdir -p "$HOME/.claude"
  if [ -e "$HOME/.claude/CLAUDE.md" ] && [ ! -L "$HOME/.claude/CLAUDE.md" ]; then
    log "$HOME/.claude/CLAUDE.md exists (not ours) — leaving it untouched"; record skip "CLAUDE.md"
  else
    printf '@~/AGENTS.md\n' > "$HOME/.claude/CLAUDE.md"
    ok "wrote ~/.claude/CLAUDE.md → @~/AGENTS.md"; record ok "CLAUDE.md"
  fi

  if [ -d "$CFG/skills" ]; then
    mkdir -p "$HOME/.claude/skills"
    linked=0; collided=0
    for d in "$CFG/skills"/*/; do
      [ -d "$d" ] || continue
      name="$(basename "$d")"
      dest="$HOME/.claude/skills/$name"
      if [ -e "$dest" ] && [ ! -L "$dest" ]; then collided=$((collided+1)); continue; fi
      ln -sfn "$d" "$dest" && linked=$((linked+1))
    done
    ok "linked $linked shared skills into ~/.claude/skills (collisions skipped: $collided)"
    record ok "skills($linked)"
  fi
else
  warn "ai-agent-rules not found — skipped AGENTS.md & skills (set AI_RULES_DIR to enable)"
  record fail "agent-rules"
fi

# === 5. Summary ===============================================================================
hdr "Summary"
[ ${#INSTALLED[@]} -gt 0 ] && ok "applied:  ${INSTALLED[*]}"
[ ${#SKIPPED[@]}   -gt 0 ] && log "✓ already: ${SKIPPED[*]}"
[ ${#FAILED[@]}    -gt 0 ] && warn "failed:   ${FAILED[*]}"
log "re-run after a fresh web session to re-apply the git [include]."
exit 0
