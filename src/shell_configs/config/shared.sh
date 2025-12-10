# shellcheck shell=bash
# Shared Shell Configuration
# This file contains configurations that work across bash, zsh, and other POSIX-compatible shells

### Environment ###
export EDITOR=vim
export VISUAL=vim
export PAGER=less
export PATH="$PATH:$HOME/.local/bin"
export PATH="$PATH:$HOME/.rvm/bin"

### Git - Aliases ###
alias ga='git add'
alias gaa="git add ."
alias gc='git commit'
alias gd='git diff'
alias gds='git diff --staged'
alias gl='git log --oneline --graph --decorate --max-count 15'
alias gla='git log --oneline --graph --decorate'
alias gp='git pull'
alias gpu='git push'
alias gs='git status'
alias gwt='git worktree'
alias gch='git checkout'
alias gchb='git checkout -b'
alias grl='git reflog'
alias gundo='git reset --soft HEAD~1'
alias gunstage='git reset HEAD'
alias grecover='git reset --hard ORIG_HEAD'
alias gwhatchanged='git log ORIG_HEAD.. --stat --no-merges'
alias wtl='wt list'
alias wta='wt add'
alias wtr='wt rm'
alias sync-fork="git checkout && git fetch upstream && git merge upstream/main"
alias recent_commits="git for-each-ref --sort=-committerdate refs/heads/ --format='%(HEAD) %(color:yellow)%(refname:short)%(color:reset) - %(color:red)%(objectname:short)%(color:reset) - %(contents:subject) - %(authorname) (%(color:green)%(committerdate:relative)%(color:reset))'"
alias safepull='git fetch origin $(git rev-parse --abbrev-ref HEAD) && git merge FETCH_HEAD'
alias yeet="git commit -a --amend --no-edit"
alias yeet_to_github="git commit -a --amend --no-edit && git push --force-with-lease"

### Git - Configuration ###
export GIT_PS1_SHOWDIRTYSTATE=true
export GIT_PS1_SHOWSTASHSTATE=true
export GIT_PS1_SHOWUNTRACKEDFILES=true
export GIT_PS1_SHOWUPSTREAM="auto"
GPG_TTY=$(tty)
export GPG_TTY

### Git - Functions ###
git() {
    if [[ "$1" == "checkout" && -z "$2" ]]; then
        local default_branch
        default_branch=$(command git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
        if [[ -n "$default_branch" ]]; then
            command git checkout "$default_branch"
        else
            echo "Error: Could not determine default branch."
            return 1
        fi
    else
        command git "$@"
    fi
}

### Git - Auto Fetch ###
_git_auto_fetch() {
    local git_dir fetch_head cooldown_seconds=300

    git_dir=$(command git rev-parse --git-dir 2>/dev/null) || return
    fetch_head="$git_dir/FETCH_HEAD"

    if [[ -f "$fetch_head" ]]; then
        local last_fetch
        last_fetch=$(stat -f %m "$fetch_head" 2>/dev/null || stat -c %Y "$fetch_head" 2>/dev/null)
        local now=$(date +%s)
        if ((now - last_fetch < cooldown_seconds)); then
            return
        fi
    fi

    command git fetch --quiet &>/dev/null &
}

### Git Worktree Management ###
export WT_DIR=".worktrees"
export WT_EDITOR="cursor"

__wt_ps1() {
    local git_dir=$(command git rev-parse --git-dir 2>/dev/null)
    if [[ "$git_dir" == *".git/worktrees/"* ]]; then
        echo " [wt]"
    fi
}

_wt_main_branch() {
    command git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/@@' || echo "origin/main"
}

_wt_is_merged() {
    local branch="$1"
    local main_branch=$(_wt_main_branch)
    command git branch --merged "$main_branch" 2>/dev/null | grep -q "^[*+ ]*${branch}$"
}

_wt_repo_root() {
    local root
    root=$(command git rev-parse --show-toplevel 2>/dev/null)
    if [[ -z "$root" ]]; then
        echo "Error: Not in a git repository" >&2
        return 1
    fi
    echo "$root"
}

_wt_remove() {
    local wt_path="$1" force="${2:-false}"
    local error_output

    if [[ "$force" == true ]]; then
        error_output=$(command git worktree remove --force "$wt_path" 2>&1) && return 0
    else
        error_output=$(command git worktree remove "$wt_path" 2>&1) && return 0
    fi

    if [[ "$error_output" == *"uncommitted changes"* ]] || [[ "$error_output" == *"untracked files"* ]]; then
        return 1
    fi

    echo "$error_output" >&2
    return 2
}

_wt_sanitize_dirname() {
    local name="$1"
    name="${name//\//-}"
    name="${name//\\/-}"
    name="${name//:/-}"
    echo "$name"
}

_wt_add() {
    local branch=""
    local base_branch=""
    local open_editor=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --open | -o)
                open_editor=true
                shift
                ;;
            --base | -b)
                base_branch="$2"
                shift 2
                ;;
            *)
                branch="$1"
                shift
                ;;
        esac
    done

    if [[ -z "$branch" ]]; then
        echo "Usage: wt add <branch> [--open] [--base <branch>]"
        return 1
    fi

    local repo_root
    repo_root=$(_wt_repo_root) || return 1

    local dir_name
    dir_name=$(_wt_sanitize_dirname "$branch")
    local worktree_path="$repo_root/$WT_DIR/$dir_name"

    if [[ -d "$worktree_path" ]]; then
        echo "Error: Worktree for '$branch' already exists at $worktree_path"
        return 1
    fi

    mkdir -p "$repo_root/$WT_DIR"

    if command git show-ref --verify --quiet "refs/heads/$branch" ||
        command git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
        if ! command git worktree add "$worktree_path" "$branch"; then
            echo "Error: Failed to create worktree for '$branch'"
            return 1
        fi
        echo "Created worktree for '$branch' at $worktree_path"
    else
        [[ -z "$base_branch" ]] && base_branch=$(_wt_main_branch)
        if ! command git worktree add -b "$branch" "$worktree_path" "$base_branch"; then
            echo "Error: Failed to create worktree and branch '$branch' from '$base_branch'"
            return 1
        fi
        echo "Created worktree with new branch '$branch' (based on $base_branch) at $worktree_path"
    fi

    _wt_prune

    if [[ "$open_editor" == true ]]; then
        $WT_EDITOR "$worktree_path"
    fi
}

_wt_rm() {
    local branch="" force=false
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --force | -f) force=true ;;
            *) branch="$1" ;;
        esac
        shift
    done

    if [[ -z "$branch" ]]; then
        echo "Usage: wt rm <branch> [--force]"
        return 1
    fi

    local repo_root
    repo_root=$(_wt_repo_root) || return 1
    local dir_name
    dir_name=$(_wt_sanitize_dirname "$branch")
    local worktree_path="$repo_root/$WT_DIR/$dir_name"

    if [[ ! -d "$worktree_path" ]]; then
        echo "Error: Worktree for '$branch' does not exist"
        return 1
    fi

    _wt_remove "$worktree_path" "$force"
    case $? in
        0) echo "Removed worktree for '$branch'" ;;
        1)
            echo "Error: Worktree '$branch' has uncommitted changes or untracked files"
            echo "Use 'wt rm $branch --force' to remove anyway"
            return 1
            ;;
        2)
            echo "Error: Failed to remove worktree for '$branch'"
            return 1
            ;;
    esac
}

_wt_ls() {
    local repo_root wt_path wt_branch merged_marker
    repo_root=$(_wt_repo_root) || return 1

    echo "Worktrees:"
    command git worktree list | while IFS= read -r line; do
        wt_path="${line%% *}"
        wt_branch="${line##* }"
        wt_branch="${wt_branch#\[}"
        wt_branch="${wt_branch%\]}"

        if [[ "$wt_path" == "$repo_root" ]]; then
            echo "  * $wt_branch (main worktree)"
        else
            merged_marker=""
            if _wt_is_merged "$wt_branch"; then
                merged_marker=" [MERGED]"
            fi
            echo "  - $wt_branch$merged_marker"
        fi
    done
}

_wt_cd() {
    local branch="$1"

    if [[ -z "$branch" ]]; then
        echo "Usage: wt cd <branch>"
        return 1
    fi

    local repo_root
    repo_root=$(_wt_repo_root) || return 1

    local dir_name
    dir_name=$(_wt_sanitize_dirname "$branch")
    local worktree_path="$repo_root/$WT_DIR/$dir_name"

    if [[ ! -d "$worktree_path" ]]; then
        echo "Error: Worktree for '$branch' does not exist"
        return 1
    fi

    cd "$worktree_path" || return 1
}

_wt_prune() {
    local force=false orphans=false
    local repo_root wt_path wt_branch is_orphan orphan_reason
    local pruned=0 skipped=0

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --force | -f)
                force=true
                shift
                ;;
            --orphans | -o)
                orphans=true
                shift
                ;;
            *)
                shift
                ;;
        esac
    done

    repo_root=$(_wt_repo_root) || return 0

    while IFS= read -r line; do
        wt_path="${line%% *}"
        wt_branch="${line##* }"
        wt_branch="${wt_branch#\[}"
        wt_branch="${wt_branch%\]}"

        if [[ "$wt_path" != "$repo_root" ]] && [[ "$wt_path" == "$repo_root/$WT_DIR/"* ]]; then
            if _wt_is_merged "$wt_branch"; then
                _wt_remove "$wt_path" "$force"
                case $? in
                    0)
                        echo "Pruned merged worktree: $wt_branch"
                        pruned=$((pruned + 1))
                        ;;
                    1)
                        echo "Skipped '$wt_branch' (has uncommitted changes, use --force)"
                        skipped=$((skipped + 1))
                        ;;
                esac
            fi
        fi
    done < <(command git worktree list)

    if [[ "$orphans" == true ]]; then
        while IFS= read -r line; do
            wt_path="${line%% *}"
            wt_branch="${line##* }"
            wt_branch="${wt_branch#\[}"
            wt_branch="${wt_branch%\]}"

            if [[ "$wt_path" != "$repo_root" ]] && [[ "$wt_path" == "$repo_root/$WT_DIR/"* ]]; then
                is_orphan=false
                orphan_reason=""

                if ! command git show-ref --verify --quiet "refs/heads/$wt_branch" 2>/dev/null; then
                    is_orphan=true
                    orphan_reason="branch no longer exists"
                elif [[ -n "$(find "$wt_path" -maxdepth 0 -mtime +30 2>/dev/null)" ]]; then
                    is_orphan=true
                    orphan_reason="not accessed in 30+ days"
                fi

                if [[ "$is_orphan" == true ]]; then
                    _wt_remove "$wt_path" "$force"
                    case $? in
                        0)
                            echo "Pruned orphaned worktree: $wt_branch ($orphan_reason)"
                            pruned=$((pruned + 1))
                            ;;
                        1)
                            echo "Skipped '$wt_branch' (has uncommitted changes, use --force)"
                            skipped=$((skipped + 1))
                            ;;
                    esac
                fi
            fi
        done < <(command git worktree list)
    fi

    if [[ $pruned -eq 0 ]] && [[ $skipped -eq 0 ]]; then
        [[ "$orphans" == true ]] && echo "No merged or orphaned worktrees to prune" || echo "No merged worktrees to prune"
    fi
}

_wt_orphans() {
    local repo_root wt_path wt_branch
    local found=0
    repo_root=$(_wt_repo_root) || return 1

    echo "Checking for orphaned worktrees..."

    while IFS= read -r line; do
        wt_path="${line%% *}"
        wt_branch="${line##* }"
        wt_branch="${wt_branch#\[}"
        wt_branch="${wt_branch%\]}"

        if [[ "$wt_path" != "$repo_root" ]] && [[ "$wt_path" == "$repo_root/$WT_DIR/"* ]]; then
            if ! command git show-ref --verify --quiet "refs/heads/$wt_branch" 2>/dev/null; then
                echo "  - $wt_branch (branch no longer exists)"
                found=$((found + 1))
            elif [[ -n "$(find "$wt_path" -maxdepth 0 -mtime +30 2>/dev/null)" ]]; then
                echo "  - $wt_branch (not accessed in 30+ days)"
                found=$((found + 1))
            fi
        fi
    done < <(command git worktree list)

    if [[ $found -eq 0 ]]; then
        echo "No orphaned worktrees found"
    fi
}

_wt_help() {
    cat <<EOF
Git Worktree Management Tool

Usage: wt <command> [options]

Commands:
  add <branch> [--open] [--base <branch>]  Create a new worktree for the branch
  rm <branch> [--force]                     Remove a worktree (--force if uncommitted changes)
  list                                      List all worktrees with status
  cd <branch>                               Navigate to a worktree
  prune [--force] [--orphans]               Remove merged worktrees (--orphans includes stale)
  orphans                                   List stale/orphaned worktrees
  help                                      Show this help message

Environment Variables:
  WT_DIR                 Directory name for worktrees (default: .worktrees)
  WT_EDITOR              Editor to open worktrees (default: cursor)

Examples:
  wt add feature-auth --open    # Create worktree and open in editor
  wt list                       # List all worktrees
  wt cd feature-auth            # Navigate to worktree
  wt prune                      # Clean up merged worktrees
  wt rm feature-auth            # Remove a worktree
EOF
}

wt() {
    local cmd="${1:-list}"
    shift 2>/dev/null

    case "$cmd" in
        add) _wt_add "$@" ;;
        rm | remove) _wt_rm "$@" ;;
        list | ls) _wt_ls "$@" ;;
        cd) _wt_cd "$@" ;;
        prune) _wt_prune "$@" ;;
        orphans) _wt_orphans "$@" ;;
        help | --help | -h) _wt_help ;;
        *) echo "Unknown command: $cmd. Run 'wt help' for usage." ;;
    esac
}

### Python ###
pytest_coverage() {
    uv run pytest --cov=src --cov-report=term-missing "$@"
}

python_package_versions() {
    uvx pip index versions "$@"
}

### Node/NPM ###
npm_package_versions() {
    npm view "@block/$1" versions --json
}

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

### Rust ###
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"

### Docker ###
alias docker_cleanup="docker builder prune -af && docker system prune -af"

### AI Tools - Aliases ###
alias ccusage="npx -y ccusage@latest"
alias ccviewer="uvx --from claude-code-viewer claude-viewer"
alias run_claude_code_logger="npx -y claude-code-logger@latest start -v"
alias claude_with_logger="ANTHROPIC_BASE_URL=http://localhost:8000 claude"

### AI Tools - Configuration ###
export GOOSE_ALLOWLIST_BYPASS=true
export GOOSE_AUTO_COMPACT_THRESHOLD=0.0
export CLAUDE_CODE_STATUSLINE_DEBUG=1

### AI Tools - Functions ###
run_goose_recipe() {
    goose run --recipe "$@" --interactive
}

query_goose_database() {
    sqlite3 ~/.local/share/goose/sessions/sessions.db "$@"
}

mcp_inspector() {
    npx -y @modelcontextprotocol/inspector "$@"
}

### Shell Completions ###
_pipenv_run_complete() {
    _arguments '1: :_files' '*:: :_default'
}

### Utilities ###
alias ll='ls -la'

extract() {
    if [ -f "$1" ]; then
        case "$1" in
            *.tar.bz2) tar xjf "$1" ;;
            *.tar.gz) tar xzf "$1" ;;
            *.bz2) bunzip2 "$1" ;;
            *.gz) gunzip "$1" ;;
            *.tar) tar xf "$1" ;;
            *.zip) unzip "$1" ;;
            *.Z) uncompress "$1" ;;
            *) echo "'$1' cannot be extracted" ;;
        esac
    else
        echo "'$1' is not a valid file"
    fi
}

[ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env"
