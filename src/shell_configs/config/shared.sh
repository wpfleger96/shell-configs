# shellcheck shell=bash
# Shared Shell Configuration
# This file contains configurations that work across bash, zsh, and other POSIX-compatible shells

### Environment ###
export EDITOR=vim
export VISUAL=vim
export PAGER=less

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
alias wtl='wt ls'
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
    if [[ "$1" == "checkout" && "$2" == "master" ]]; then
        master_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
        if [[ -n "$master_branch" ]]; then
            command git checkout "$master_branch"
        else
            echo "Error: Could not determine default branch (main/master)."
            return 1
        fi
    else
        command git "$@"
    fi
}

### Git Worktree Management ###
export WT_DIR=".worktrees"
export WT_EDITOR="${WT_EDITOR:-code}"

__wt_ps1() {
    local git_dir=$(git rev-parse --git-dir 2>/dev/null)
    if [[ "$git_dir" == *".git/worktrees/"* ]]; then
        echo " [wt]"
    fi
}

_wt_ensure_gitignore() {
    local repo_root=$(git rev-parse --show-toplevel 2>/dev/null)
    if [[ -z "$repo_root" ]]; then
        return 1
    fi

    local gitignore="$repo_root/.gitignore"

    if [[ ! -f "$gitignore" ]] || ! grep -q "^${WT_DIR}/$" "$gitignore" 2>/dev/null; then
        echo "${WT_DIR}/" >>"$gitignore"
        echo "Added ${WT_DIR}/ to .gitignore"
    fi
}

_wt_main_branch() {
    git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main"
}

_wt_is_merged() {
    local branch="$1"
    local main_branch=$(_wt_main_branch)
    git branch --merged "$main_branch" 2>/dev/null | grep -q "^\s*${branch}$"
}

_wt_repo_root() {
    local root
    root=$(git rev-parse --show-toplevel 2>/dev/null)
    if [[ -z "$root" ]]; then
        echo "Error: Not in a git repository" >&2
        return 1
    fi
    echo "$root"
}

_wt_remove() {
    local path="$1" force="${2:-false}"
    git worktree remove "$path" 2>/dev/null && return 0
    [[ "$force" == true ]] && git worktree remove --force "$path" 2>/dev/null && return 0
    [[ "$force" == false ]] && return 1
    return 2
}

_wt_parse_force_args() {
    local -n _branch=$1 _force=$2
    shift 2
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --force | -f) _force=true ;;
            *) _branch="$1" ;;
        esac
        shift
    done
}

_wt_add() {
    local branch=""
    local open_editor=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --open | -o)
                open_editor=true
                shift
                ;;
            *)
                branch="$1"
                shift
                ;;
        esac
    done

    if [[ -z "$branch" ]]; then
        echo "Usage: wt add <branch> [--open]"
        return 1
    fi

    local repo_root
    repo_root=$(_wt_repo_root) || return 1

    _wt_ensure_gitignore

    local worktree_path="$repo_root/$WT_DIR/$branch"

    if [[ -d "$worktree_path" ]]; then
        echo "Error: Worktree for '$branch' already exists at $worktree_path"
        return 1
    fi

    mkdir -p "$repo_root/$WT_DIR"

    if git worktree add "$worktree_path" "$branch" 2>/dev/null; then
        echo "Created worktree for '$branch' at $worktree_path"

        if [[ "$open_editor" == true ]]; then
            $WT_EDITOR "$worktree_path"
        fi

        _wt_prune
    else
        echo "Error: Failed to create worktree for '$branch'"
        echo "Branch may not exist. Try: git fetch origin $branch"
        return 1
    fi
}

_wt_rm() {
    local branch="" force=false
    _wt_parse_force_args branch force "$@"

    if [[ -z "$branch" ]]; then
        echo "Usage: wt rm <branch> [--force]"
        return 1
    fi

    local repo_root
    repo_root=$(_wt_repo_root) || return 1
    local worktree_path="$repo_root/$WT_DIR/$branch"

    if [[ ! -d "$worktree_path" ]]; then
        echo "Error: Worktree for '$branch' does not exist"
        return 1
    fi

    _wt_remove "$worktree_path" "$force"
    case $? in
        0) echo "Removed worktree for '$branch'" ;;
        1)
            echo "Error: Worktree '$branch' has uncommitted changes"
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
    local repo_root
    repo_root=$(_wt_repo_root) || return 1

    echo "Worktrees:"
    git worktree list | while IFS= read -r line; do
        local path="${line%% *}"
        local branch="${line##* }"
        branch="${branch#\[}"
        branch="${branch%\]}"

        if [[ "$path" == "$repo_root" ]]; then
            echo "  * $branch (main worktree)"
        else
            local merged_marker=""
            if _wt_is_merged "$branch"; then
                merged_marker=" [MERGED]"
            fi
            echo "  - $branch$merged_marker"
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

    local worktree_path="$repo_root/$WT_DIR/$branch"

    if [[ ! -d "$worktree_path" ]]; then
        echo "Error: Worktree for '$branch' does not exist"
        return 1
    fi

    cd "$worktree_path" || return 1
}

_wt_prune() {
    local branch="" force=false
    _wt_parse_force_args branch force "$@"

    local repo_root
    repo_root=$(_wt_repo_root) || return 0

    local pruned=0 skipped=0

    while IFS= read -r line; do
        local path="${line%% *}"
        local branch="${line##* }"
        branch="${branch#\[}"
        branch="${branch%\]}"

        if [[ "$path" != "$repo_root" ]] && [[ "$path" == "$repo_root/$WT_DIR/"* ]]; then
            if _wt_is_merged "$branch"; then
                _wt_remove "$path" "$force"
                case $? in
                    0)
                        echo "Pruned merged worktree: $branch"
                        pruned=$((pruned + 1))
                        ;;
                    1)
                        echo "Skipped '$branch' (has uncommitted changes, use --force)"
                        skipped=$((skipped + 1))
                        ;;
                esac
            fi
        fi
    done < <(git worktree list)

    if [[ $pruned -eq 0 ]] && [[ $skipped -eq 0 ]]; then
        echo "No merged worktrees to prune"
    fi
}

_wt_orphans() {
    local repo_root
    repo_root=$(_wt_repo_root) || return 1

    echo "Checking for orphaned worktrees..."
    local found=0

    while IFS= read -r line; do
        local path="${line%% *}"
        local branch="${line##* }"
        branch="${branch#\[}"
        branch="${branch%\]}"

        if [[ "$path" != "$repo_root" ]] && [[ "$path" == "$repo_root/$WT_DIR/"* ]]; then
            if ! git show-ref --verify --quiet "refs/heads/$branch" 2>/dev/null; then
                echo "  - $branch (branch no longer exists)"
                found=$((found + 1))
            elif [[ -n "$(find "$path" -maxdepth 0 -mtime +30 2>/dev/null)" ]]; then
                echo "  - $branch (not accessed in 30+ days)"
                found=$((found + 1))
            fi
        fi
    done < <(git worktree list)

    if [[ $found -eq 0 ]]; then
        echo "No orphaned worktrees found"
    fi
}

_wt_clean() {
    echo "Interactive cleanup not yet implemented"
    echo "Use 'wt prune' to remove merged worktrees"
    echo "Use 'wt orphans' to find stale worktrees"
    echo "Use 'wt rm <branch>' to remove specific worktrees"
}

_wt_help() {
    cat <<EOF
Git Worktree Management Tool

Usage: wt <command> [options]

Commands:
  add <branch> [--open]  Create a new worktree for the branch
  rm <branch> [--force]  Remove a worktree (--force if uncommitted changes)
  ls                     List all worktrees with status
  cd <branch>            Navigate to a worktree
  prune [--force]        Remove worktrees for merged branches (--force if uncommitted changes)
  orphans                List stale/orphaned worktrees
  clean                  Interactive cleanup (coming soon)
  help                   Show this help message

Environment Variables:
  WT_DIR                 Directory name for worktrees (default: .worktrees)
  WT_EDITOR              Editor to open worktrees (default: code)

Examples:
  wt add feature-auth --open    # Create worktree and open in editor
  wt ls                         # List all worktrees
  wt cd feature-auth            # Navigate to worktree
  wt prune                      # Clean up merged worktrees
  wt rm feature-auth            # Remove a worktree
EOF
}

wt() {
    local cmd="${1:-ls}"
    shift 2>/dev/null

    case "$cmd" in
        add) _wt_add "$@" ;;
        rm) _wt_rm "$@" ;;
        ls) _wt_ls "$@" ;;
        cd) _wt_cd "$@" ;;
        prune) _wt_prune "$@" ;;
        orphans) _wt_orphans "$@" ;;
        clean) _wt_clean "$@" ;;
        help) _wt_help ;;
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
