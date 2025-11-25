# Shared Shell Configuration
# This file contains configurations that work across bash, zsh, and other POSIX-compatible shells

alias ll='ls -la'
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git log --oneline --graph --decorate'

export EDITOR=vim
export VISUAL=vim
export PAGER=less

extract() {
    if [ -f "$1" ]; then
        case "$1" in
            *.tar.bz2)   tar xjf "$1"     ;;
            *.tar.gz)    tar xzf "$1"     ;;
            *.bz2)       bunzip2 "$1"     ;;
            *.gz)        gunzip "$1"      ;;
            *.tar)       tar xf "$1"      ;;
            *.zip)       unzip "$1"       ;;
            *.Z)         uncompress "$1"  ;;
            *)           echo "'$1' cannot be extracted" ;;
        esac
    else
        echo "'$1' is not a valid file"
    fi
}

export GIT_PS1_SHOWDIRTYSTATE=true
export GIT_PS1_SHOWSTASHSTATE=true       # Show $ if something is stashed
export GIT_PS1_SHOWUNTRACKEDFILES=true   # Show % if there are untracked files
export GIT_PS1_SHOWUPSTREAM="auto"       # Show <>=  for upstream status

GPG_TTY=$(tty)
export GPG_TTY

git() {
    if [[ "$1" == "checkout" && "$2" == "$master" ]]; then
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

pytest_coverage() {
    uv run pytest --cov=src --cov-report=term-missing "$@"
}

python_package_versions() {
    uvx pip index versions "$@"
}

npm_package_versions() {
    npm view "@block/$@" versions --json
}

alias recent_commits="git for-each-ref --sort=-committerdate refs/heads/ --format='%(HEAD) %(color:yellow)%(refname:short)%(color:reset) - %(color:red)%(objectname:short)%(color:reset) - %(contents:subject) - %(authorname) (%(color:green)%(committerdate:relative)%(color:reset))'"
alias safepull='git fetch origin $(git rev-parse --abbrev-ref HEAD) && git merge FETCH_HEAD'

alias yeet="git commit -a --amend --no-edit"
alias yeet_to_github="git commit -a --amend --no-edit && git push --force-with-lease"


export GOOSE_ALLOWLIST_BYPASS=true
export GOOSE_AUTO_COMPACT_THRESHOLD=0.0


run_goose_recipe() {
    goose run --recipe "$@" --interactive
}

mcp_inspector() {
    npx -y @modelcontextprotocol/inspector "$@"
}

alias ccusage="npx -y ccusage@latest"
alias ccviewer="uvx --from claude-code-viewer claude-viewer"

export CLAUDE_CODE_STATUSLINE_DEBUG=1

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

[ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env"
