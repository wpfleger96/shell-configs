#!/usr/bin/env bash
#
# cloud-setup.sh — make a Claude Code on the web container resemble Will's local dev env.
#
# WHY this exists: web/cloud sessions start from a stock Ubuntu container that is missing the
# tools, git ergonomics, and AI-agent rules that shell-configs + ai-agent-rules give a local
# machine. This script closes that gap with zero dependency on any repo being cloned.
#
# HOW it's meant to be used: it lives here for version control, but its real home is the Claude
# iOS app's SessionStart hook (paste the contents there). It therefore must be non-interactive,
# best-effort, idempotent, and never block the session from starting.
#
# SAFETY: the cloud harness owns the git identity ("Claude") + SSH commit signing (/tmp/code-sign)
# and the Claude hooks/settings under ~/.claude. This script installs Python/tools, sets ONLY
# core.hooksPath in git config (never identity or commit signing), and delegates ALL agent config
# to `ai-agent-rules` (which backs up ~/.claude before symlinking). It never edits git identity,
# signing, or the harness hook scripts directly.
#
# Re-run safe. After a fresh web session, re-running re-applies everything (the harness may
# regenerate ~/.gitconfig and ~/.claude on session start).

# shellcheck disable=SC2317  # callback functions invoked indirectly via install_or_fallback "$@"
set -uo pipefail

log() { printf '  %s\n' "$*"; }
ok() { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m✗\033[0m %s\n' "$*"; }
hdr() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

fetch() {
    if have curl; then
        curl -fsSL "$1" -o "$2"
    elif have wget; then
        wget -qO "$2" "$1"
    else
        return 1
    fi
}

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if have sudo; then SUDO="sudo"; else warn "not root and no sudo — apt steps may fail"; fi
fi

LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"
case ":$PATH:" in *":$LOCAL_BIN:"*) : ;; *) export PATH="$LOCAL_BIN:$PATH" ;; esac

INSTALLED=()
SKIPPED=()
FAILED=()
record() { case "$1" in ok) INSTALLED+=("$2") ;; skip) SKIPPED+=("$2") ;; fail) FAILED+=("$2") ;; esac }

APT_UPDATED=0
apt_update_once() {
    [ "$APT_UPDATED" -eq 1 ] && return 0
    if $SUDO apt-get update -y >/dev/null 2>&1; then
        APT_UPDATED=1
        return 0
    fi
    return 1
}
apt_install() { apt_update_once && $SUDO apt-get install -y "$@" >/dev/null 2>&1; }

# Try apt first, then an optional fallback command (passed as remaining args).
install_or_fallback() {
    local tool="$1"
    shift
    if have "$tool"; then
        ok "$tool already present"
        record skip "$tool"
        return
    fi
    if apt_install "$tool" && have "$tool"; then
        ok "installed $tool"
        record ok "$tool"
        return
    fi
    if [ $# -gt 0 ] && "$@" && have "$tool"; then
        ok "installed $tool (fallback)"
        record ok "$tool"
        return
    fi
    warn "failed to install $tool"
    record fail "$tool"
}

_shfmt_go() { have go && GOBIN="$LOCAL_BIN" go install mvdan.cc/sh/v3/cmd/shfmt@latest >/dev/null 2>&1; }
_just_prebuilt() { fetch https://just.systems/install.sh /tmp/just-install.sh && bash /tmp/just-install.sh --to "$LOCAL_BIN" >/dev/null 2>&1; }
_eza_prebuilt() {
    fetch https://github.com/eza-community/eza/releases/latest/download/eza_x86_64-unknown-linux-gnu.tar.gz /tmp/eza.tgz || return 1
    local tmp
    tmp="$(mktemp -d)"
    local bin
    tar -xzf /tmp/eza.tgz -C "$tmp" >/dev/null 2>&1
    bin="$(find "$tmp" -type f -name eza | head -1)"
    local rc=1
    [ -n "$bin" ] && install -m 0755 "$bin" "$LOCAL_BIN/eza" && rc=0
    rm -rf "$tmp"
    return "$rc"
}

printf '\033[1mcloud-setup.sh\033[0m — aligning this container with Will'\''s local dev env\n'

# === 1. Bootstrap prerequisites (curl, uv) ====================================================
# Everything below depends on these; a generic web session may not have them.
hdr "Bootstrap prerequisites"

if have curl || have wget; then
    ok "downloader present"
    record skip "curl"
elif apt_install curl ca-certificates && have curl; then
    ok "installed curl + ca-certificates"
    record ok "curl"
else
    warn "no curl/wget — download steps will fail"
    record fail "curl"
fi

if have uv; then
    ok "uv already present"
    record skip "uv"
elif fetch https://astral.sh/uv/install.sh /tmp/uv-install.sh &&
    env UV_INSTALL_DIR="$LOCAL_BIN" INSTALLER_NO_MODIFY_PATH=1 sh /tmp/uv-install.sh >/dev/null 2>&1 &&
    {
        hash -r
        have uv
    }; then
    ok "installed uv (uvx ships with it)"
    record ok "uv"
elif have pip && pip install --user uv >/dev/null 2>&1 && {
    hash -r
    have uv
}; then
    ok "installed uv (pip --user)"
    record ok "uv"
else
    warn "could not install uv — Python 3.14 & ai-agent-rules steps may be skipped"
    record fail "uv"
fi

# === 2. Python 3.14 ===========================================================================
hdr "Python 3.14 (both repos pin .python-version = 3.14)"
if have uv && uv python find 3.14 >/dev/null 2>&1; then
    ok "Python 3.14 already available via uv"
    record skip "python3.14"
elif have python3.14; then
    ok "python3.14 already on PATH"
    record skip "python3.14"
elif have uv && uv python install 3.14 >/dev/null 2>&1; then
    ok "installed Python 3.14 via uv"
    record ok "python3.14"
else
    log "uv route unavailable — trying deadsnakes apt PPA"
    if apt_install software-properties-common &&
        $SUDO add-apt-repository -y ppa:deadsnakes/ppa >/dev/null 2>&1 &&
        {
            APT_UPDATED=1
            apt_install python3.14
        }; then
        ok "installed python3.14 via deadsnakes"
        record ok "python3.14"
    else
        warn "could not install Python 3.14"
        record fail "python3.14"
    fi
fi

# === 3. CLI tools =============================================================================
hdr "CLI tools"

for tool in shellcheck sqlite3 direnv fzf; do
    install_or_fallback "$tool"
done

if have bat; then
    ok "bat already present"
    record skip "bat"
elif apt_install bat && { have bat || { have batcat && ln -sf "$(command -v batcat)" "$LOCAL_BIN/bat"; }; } && have bat; then
    ok "installed bat"
    record ok "bat"
else
    warn "failed to install bat"
    record fail "bat"
fi

if have gh; then
    ok "gh already present"
    record skip "gh"
elif apt_install gh ||
    {
        fetch https://cli.github.com/packages/githubcli-archive-keyring.gpg /tmp/gh.gpg &&
            $SUDO install -m 0644 /tmp/gh.gpg /usr/share/keyrings/githubcli-archive-keyring.gpg &&
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" |
            $SUDO tee /etc/apt/sources.list.d/github-cli.list >/dev/null &&
            {
                APT_UPDATED=0
                apt_install gh
            }
    }; then
    ok "installed gh"
    record ok "gh"
else
    warn "failed to install gh"
    record fail "gh"
fi

install_or_fallback shfmt _shfmt_go
install_or_fallback just _just_prebuilt
install_or_fallback eza _eza_prebuilt

# === 4. Git pre-commit hooks path =============================================================
# Mirror shell-configs' global core.hooksPath so cloud agents run each repo's .hooks/pre-commit.
# A relative path resolves to <repo-root>/.hooks at hook-run time; repos without .hooks/ run no
# hooks. Identity and commit signing are untouched.
hdr "Git pre-commit hooks path"
if [ "$(git config --global --get core.hooksPath 2>/dev/null)" = ".hooks" ]; then
    ok "core.hooksPath already set to .hooks"
    record skip "hooksPath"
elif git config --global core.hooksPath .hooks; then
    ok "set git core.hooksPath = .hooks"
    record ok "hooksPath"
else
    warn "failed to set core.hooksPath"
    record fail "hooksPath"
fi

# === 5. AI agent rules, skills & config =======================================================
# Delegate to the ai-agent-rules CLI (single source of truth): it symlinks ~/AGENTS.md,
# ~/.claude/CLAUDE.md, the shared skills, and per-agent configs, backing up ~/.claude first.
hdr "Agent rules, skills & config (via ai-agent-rules)"
if have uv; then
    if uvx ai-agent-rules setup -y --skip-completions; then
        ok "ai-agent-rules setup complete"
        record ok "ai-agent-rules"
    else
        warn "ai-agent-rules setup failed (continuing)"
        record fail "ai-agent-rules"
    fi
else
    warn "uv unavailable — cannot run ai-agent-rules setup"
    record fail "ai-agent-rules"
fi

# === 6. Summary ===============================================================================
hdr "Summary"
[ ${#INSTALLED[@]} -gt 0 ] && ok "applied:  ${INSTALLED[*]}"
[ ${#SKIPPED[@]} -gt 0 ] && log "✓ already: ${SKIPPED[*]}"
[ ${#FAILED[@]} -gt 0 ] && warn "failed:   ${FAILED[*]}"
log "note: difit is available on demand via 'npx -y difit' if node is present."
log "re-run after a fresh web session to re-apply tools, hooksPath, and agent config."
exit 0
