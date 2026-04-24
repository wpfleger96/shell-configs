# shellcheck shell=bash
# Shared Shell Configuration
# This file contains configurations that work across bash, zsh, and other POSIX-compatible shells

### Environment ###
export EDITOR=vim
export VISUAL=vim
export PAGER=less
export PATH="$PATH:$HOME/.local/bin"
export PATH="$PATH:$HOME/.rvm/bin"
export PYPI="https://pypi.org/simple"

### Git - Aliases ###
alias ga='git add'
alias gaa="git add ."
alias gc='git commit'
alias gd='git diff'
alias gds='git diff --staged'
alias gdu='git -c delta.side-by-side=false diff'
alias gdsu='git -c delta.side-by-side=false diff --staged'
alias gl='git log --graph --decorate --max-count 15 --pretty=format:"%C(yellow)%h%Creset %C(green)%ad%Creset [%C(bold blue)%an%Creset] | %s%C(bold red)%d%Creset" --date=short'
alias gla='git log --graph --decorate --pretty=format:"%C(yellow)%h%Creset %C(green)%ad%Creset [%C(bold blue)%an%Creset] | %s%C(bold red)%d%Creset" --date=short'
alias gf='git fetch'
alias gp='git pull'
alias gpu='git push'
alias gpuf='git push --force-with-lease'
alias gs='git status'
alias gst='git stash'
alias gstu='git stash -u'
alias gstp='git stash pop'
alias gwt='git worktree'
alias gch='git checkout'
alias gchb='git checkout -b'
alias gchp='git checkout && git pull'
alias grl='git reflog'
alias gundo='git reset --soft HEAD~1'
alias gunstage='git reset HEAD'
alias grecover='git reset --hard ORIG_HEAD'
alias gwhatchanged='git log ORIG_HEAD.. --stat --no-merges'
alias wtl='wt list'
alias wta='wt add'
alias wtr='wt rm'
alias recent_commits="git for-each-ref --sort=-committerdate refs/heads/ --format='%(HEAD) %(color:yellow)%(refname:short)%(color:reset) - %(color:red)%(objectname:short)%(color:reset) - %(contents:subject) - %(authorname) (%(color:green)%(committerdate:relative)%(color:reset))'"
alias safepull='git fetch origin $(git rev-parse --abbrev-ref HEAD) && git merge FETCH_HEAD'
gpm() {
    _git_smart_pull merge
}

gpr() {
    _git_smart_pull rebase
}
alias yeet="git commit -a --amend --no-edit"
alias yeet_to_github="git commit -a --amend --no-edit && git push --force-with-lease"

### Difit - Aliases ###
alias gdif='npx -y difit'
alias gdifw='npx -y difit working'
alias gdifs='npx -y difit staged'
alias gdifa='npx -y difit .'
alias gdift='npx -y difit --tui'
alias gdifn='npx -y difit --no-open'
alias gdifu='npx -y difit . --include-untracked'

gdifm() {
    local default_branch
    default_branch=$(_git_default_branch)
    if [[ -z "$default_branch" ]]; then
        echo "Error: Could not determine default branch."
        return 1
    fi
    npx -y difit @ "$default_branch"
}

### Git - Configuration ###
# Index files over 5 MB indicate repos large enough to make __git_ps1 painfully slow
_GIT_LARGE_REPO_INDEX_THRESHOLD=5242880

_tune_git_prompt() {
    local git_dir index_size
    git_dir=$(command git rev-parse --git-dir 2>/dev/null) || {
        # Not in a git repo — enable defaults for when we enter one
        export GIT_PS1_SHOWDIRTYSTATE=true
        export GIT_PS1_SHOWSTASHSTATE=true
        export GIT_PS1_SHOWUNTRACKEDFILES=true
        export GIT_PS1_SHOWUPSTREAM="auto"
        return
    }
    index_size=$(wc -c <"$git_dir/index" 2>/dev/null) || index_size=0
    if [[ $index_size -gt $_GIT_LARGE_REPO_INDEX_THRESHOLD ]]; then
        export GIT_PS1_SHOWDIRTYSTATE=
        export GIT_PS1_SHOWSTASHSTATE=
        export GIT_PS1_SHOWUNTRACKEDFILES=
        export GIT_PS1_SHOWUPSTREAM=
    else
        export GIT_PS1_SHOWDIRTYSTATE=true
        export GIT_PS1_SHOWSTASHSTATE=true
        export GIT_PS1_SHOWUNTRACKEDFILES=true
        export GIT_PS1_SHOWUPSTREAM="auto"
    fi
}

_tune_git_prompt
GPG_TTY=$(tty)
export GPG_TTY

_reset_terminal_title() {
    local name="${ZSH_NAME:-${BASH##*/}}"
    [[ -n "$TERM_PROGRAM" ]] && printf '\033]0;%s\007' "${name:-shell}"
}

### Git - Functions ###
_git_default_branch() {
    local remote="${1:-origin}"
    command git symbolic-ref "refs/remotes/$remote/HEAD" 2>/dev/null | sed "s@^refs/remotes/$remote/@@"
}

_git_smart_pull() {
    local mode="$1" # "rebase" or "merge"
    local default_branch
    default_branch=$(_git_default_branch)
    if [[ -z "$default_branch" ]]; then
        echo "Error: Could not determine default branch."
        return 1
    fi

    command git fetch origin "$default_branch" || return 1

    local current_branch
    current_branch=$(command git symbolic-ref --short HEAD 2>/dev/null)
    if [[ -n "$current_branch" && "$current_branch" != "$default_branch" ]]; then
        command git fetch origin "$current_branch" 2>/dev/null || true
    fi

    local git_dir
    git_dir=$(command git rev-parse --git-dir 2>/dev/null)
    if [[ -d "$git_dir/rebase-merge" ]] || [[ -d "$git_dir/rebase-apply" ]]; then
        command git rebase --abort
    elif [[ -f "$git_dir/MERGE_HEAD" ]]; then
        command git merge --abort
    fi

    local diverged_commits
    diverged_commits=$(command git rev-list --count HEAD "^origin/$default_branch" 2>/dev/null || echo "0")
    if [[ "$diverged_commits" -gt 0 ]] && command git diff "origin/$default_branch" --quiet 2>/dev/null; then
        echo "Branch has $diverged_commits commit(s) already on $default_branch — resetting"
        command git reset --hard "origin/$default_branch"
        return 0
    fi

    if [[ "$mode" == "rebase" ]]; then
        command git rebase "origin/$default_branch"
    else
        command git merge "origin/$default_branch"
    fi
}

git() {
    if [[ "$1" == "checkout" && -z "$2" ]]; then
        local default_branch
        default_branch=$(_git_default_branch)
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

grename() {
    local new_repo="$1"
    if [[ -z "$new_repo" ]]; then
        echo "Usage: grename <new-repo-name>"
        return 1
    fi

    local current_url
    current_url=$(command git remote get-url origin 2>/dev/null)
    if [[ -z "$current_url" ]]; then
        echo "Error: No origin remote found"
        return 1
    fi

    local username new_url
    if [[ "$current_url" == git@github.com:* ]]; then
        # SSH format: git@github.com:user/repo.git
        username="${current_url#git@github.com:}"
        username="${username%%/*}"
        new_url="git@github.com:${username}/${new_repo}.git"
    elif [[ "$current_url" == https://github.com/* ]]; then
        # HTTPS format: https://github.com/user/repo.git
        username="${current_url#https://github.com/}"
        username="${username%%/*}"
        new_url="https://github.com/${username}/${new_repo}.git"
    else
        echo "Error: Unsupported remote URL format: $current_url"
        return 1
    fi

    echo "Updating origin: $current_url -> $new_url"
    command git remote set-url origin "$new_url"
}

sync-fork() {
    local default_branch
    default_branch=$(_git_default_branch upstream)

    if [[ -z "$default_branch" ]]; then
        # Fallback: check if upstream/main or upstream/master exists
        if command git show-ref --verify --quiet refs/remotes/upstream/main 2>/dev/null; then
            default_branch="main"
        elif command git show-ref --verify --quiet refs/remotes/upstream/master 2>/dev/null; then
            default_branch="master"
        else
            echo "Error: Could not determine upstream default branch"
            return 1
        fi
    fi

    git checkout && git fetch upstream && git merge "upstream/$default_branch"
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

_wt_branch_status() {
    local branch="$1"
    local default=$(_git_default_branch)
    local main_branch="origin/${default:-main}"
    local branch_head merge_base

    command git rev-parse "refs/heads/$branch" &>/dev/null || return 1
    command git rev-parse "$main_branch" &>/dev/null || return 1

    branch_head=$(command git rev-parse "$branch" 2>/dev/null)
    merge_base=$(command git merge-base "$branch" "$main_branch" 2>/dev/null)

    local has_remote=false
    if command git show-ref --verify --quiet "refs/remotes/origin/$branch" 2>/dev/null; then
        has_remote=true
    fi

    if [[ "$branch_head" == "$merge_base" ]]; then
        if [[ "$has_remote" == true ]] && command git merge-base --is-ancestor "$branch" "$main_branch" 2>/dev/null; then
            echo "MERGED"
            return 0
        fi
        echo "NEW"
        return 0
    fi

    if [[ "$has_remote" == true ]]; then
        if command git merge-base --is-ancestor "$branch" "$main_branch" 2>/dev/null; then
            echo "MERGED"
            return 0
        fi

        local unmerged_patches
        unmerged_patches=$(command git cherry "$main_branch" "$branch" 2>/dev/null | grep -c '^+' || echo "0")
        if [[ "$unmerged_patches" == "0" ]]; then
            echo "MERGED"
            return 0
        fi
    fi

    return 1
}

_wt_is_orphan() {
    local branch="$1"
    local wt_path="$2"

    if ! command git show-ref --verify --quiet "refs/heads/$branch" 2>/dev/null; then
        echo "branch deleted"
        return 0
    fi
    if [[ -n "$(find "$wt_path" -maxdepth 0 -mtime +30 2>/dev/null)" ]]; then
        echo "stale 30+ days"
        return 0
    fi
    return 1
}

_wt_repo_root() {
    local git_common_dir
    git_common_dir=$(command git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)
    if [[ -z "$git_common_dir" ]]; then
        echo "Error: Not in a git repository" >&2
        return 1
    fi
    echo "${git_common_dir%/.git}"
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
        if [[ -z "$base_branch" ]]; then
            local default=$(_git_default_branch)
            base_branch="origin/${default:-main}"
        fi
        if ! command git worktree add -b "$branch" "$worktree_path" "$base_branch"; then
            echo "Error: Failed to create worktree and branch '$branch' from '$base_branch'"
            return 1
        fi
        git -C "$worktree_path" branch --set-upstream-to="origin/$branch" 2>/dev/null
        echo "Created worktree with new branch '$branch' (based on $base_branch) at $worktree_path"
    fi

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
    local repo_root wt_path wt_branch status_markers orphan_reason branch_status
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
            status_markers=""
            branch_status=$(_wt_branch_status "$wt_branch")
            if [[ -n "$branch_status" ]]; then
                status_markers=" [$branch_status]"
            fi
            orphan_reason=$(_wt_is_orphan "$wt_branch" "$wt_path")
            if [[ -n "$orphan_reason" ]]; then
                status_markers="$status_markers [ORPHAN: $orphan_reason]"
            fi
            echo "  - $wt_branch$status_markers"
        fi
    done
}

_wt_cd() {
    local branch="$1"
    local repo_root
    repo_root=$(_wt_repo_root) || return 1

    if [[ -z "$branch" ]]; then
        cd "$repo_root" || return 1
        return 0
    fi

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
    local repo_root wt_path wt_branch orphan_reason branch_status
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

    local default_branch
    default_branch=$(_git_default_branch)
    if [[ -n "$default_branch" ]]; then
        command git fetch origin "$default_branch" --quiet 2>/dev/null
    fi

    while IFS= read -r line; do
        wt_path="${line%% *}"
        wt_branch="${line##* }"
        wt_branch="${wt_branch#\[}"
        wt_branch="${wt_branch%\]}"

        if [[ "$wt_path" != "$repo_root" ]] && [[ "$wt_path" == "$repo_root/$WT_DIR/"* ]]; then
            branch_status=$(_wt_branch_status "$wt_branch")
            if [[ "$branch_status" == "MERGED" ]]; then
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
                orphan_reason=$(_wt_is_orphan "$wt_branch" "$wt_path")
                if [[ -n "$orphan_reason" ]]; then
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
    local repo_root wt_path wt_branch orphan_reason
    local found=0
    repo_root=$(_wt_repo_root) || return 1

    echo "Checking for orphaned worktrees..."

    while IFS= read -r line; do
        wt_path="${line%% *}"
        wt_branch="${line##* }"
        wt_branch="${wt_branch#\[}"
        wt_branch="${wt_branch%\]}"

        if [[ "$wt_path" != "$repo_root" ]] && [[ "$wt_path" == "$repo_root/$WT_DIR/"* ]]; then
            orphan_reason=$(_wt_is_orphan "$wt_branch" "$wt_path")
            if [[ -n "$orphan_reason" ]]; then
                echo "  - $wt_branch ($orphan_reason)"
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
  cd [branch]                               Navigate to a worktree (or repo root if no branch)
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
  wt cd                         # Return to repo root
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
alias uvr="uv run"
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

### Ruby ###
# Ruby/bundle with corporate SSL fix (bypasses CRL checking issues)
rubyssl() {
    if [[ -z "$SHELL_CONFIGS_DIR" ]]; then
        echo "Error: SHELL_CONFIGS_DIR not set. Run 'shell-configs install'." >&2
        return 1
    fi
    RUBYOPT="-r $SHELL_CONFIGS_DIR/lib/ssl_fix.rb" ruby "$@"
}

bundlessl() {
    if [[ -z "$SHELL_CONFIGS_DIR" ]]; then
        echo "Error: SHELL_CONFIGS_DIR not set. Run 'shell-configs install'." >&2
        return 1
    fi
    RUBYOPT="-r $SHELL_CONFIGS_DIR/lib/ssl_fix.rb" bundle "$@"
}

### Docker ###
alias docker_cleanup="docker builder prune -af && docker system prune -af"

### AI Tools - Aliases ###
alias ccc="claude --continue"
alias cccf="claude --continue --fork-session"
alias ccr="claude --resume"
alias ccy="claude --dangerously-skip-permissions"
alias cccy="claude --continue --dangerously-skip-permissions"
alias ccry="claude --resume --dangerously-skip-permissions"
alias cxc="codex resume --last"
alias cxr="codex resume"
alias cxf="codex fork --last"
alias cxy="codex --dangerously-bypass-approvals-and-sandbox"
alias cxcy="codex resume --last --dangerously-bypass-approvals-and-sandbox"
alias cxry="codex resume --dangerously-bypass-approvals-and-sandbox"
alias cxfy="codex fork --last --dangerously-bypass-approvals-and-sandbox"
alias gmc="gemini --resume latest"
alias gmy="gemini --yolo"
alias gmcy="gemini --resume latest --yolo"
alias amc="amp threads continue"
alias amr="amp threads continue --pick"
alias amf="amp threads fork"
alias amy="amp --dangerously-allow-all"
alias amcy="amp threads continue --dangerously-allow-all"
alias amry="amp threads continue --pick --dangerously-allow-all"
alias amfy="amp threads fork --dangerously-allow-all"
alias ccusage="npx -y ccusage@latest"
alias ccviewer="uvx --from claude-code-viewer claude-viewer"
alias run_claude_code_logger="unbuffer npx -y claude-code-logger@latest start -v"
alias claude_with_logger="ANTHROPIC_BASE_URL=http://localhost:8000 claude"

### AI Tools - Configuration ###
export GOOSE_ALLOWLIST_BYPASS=true
export GOOSE_AUTO_COMPACT_THRESHOLD=0.0
export CLAUDE_CODE_STATUSLINE_DEBUG=1
export ENABLE_EXPERIMENTAL_MCP_CLI=true
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
export CLAUDE_CODE_NO_FLICKER=1

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

runlog() {
    local outfile="$1"
    shift
    (
        set -x
        "$@"
    ) 2>&1 | tee "$outfile"
}

[ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env"
