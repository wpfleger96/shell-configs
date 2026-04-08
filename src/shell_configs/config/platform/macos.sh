#!/usr/bin/env bash

# macOS-specific configuration
# Automatically included on macOS systems

# iTerm2 shell integration (prompt marks, Cmd+Shift+Up/Down navigation, etc.)
# Safe to source unconditionally — the script checks for iTerm2 and no-ops elsewhere
# shellcheck disable=SC1090
if [ -n "$ZSH_VERSION" ] && [ -f ~/.zsh/iterm2-shell-integration.zsh ]; then
    source ~/.zsh/iterm2-shell-integration.zsh
elif [ -n "$BASH_VERSION" ] && [ -f ~/.bash/iterm2-shell-integration.bash ]; then
    source ~/.bash/iterm2-shell-integration.bash
fi

# Remove macOS quarantine attribute from files
unlock_file() {
    local file=$1
    sudo xattr -r -d com.apple.quarantine "$file"
}

# Open Goose recipe in desktop app
open_goose_recipe_desktop() {
    local recipe_name=$1
    local deeplink=$(goose recipe deeplink "$recipe_name" | grep -o 'goose://recipe?config=[^ ]*')
    open "$deeplink"
}

chrome() {
    open -a "Google Chrome" "$@"
}

nosleep() {
    caffeinate -disu -t "${1:-9200}"
}
