#!/usr/bin/env bash

# macOS-specific configuration
# Automatically included on macOS systems

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
