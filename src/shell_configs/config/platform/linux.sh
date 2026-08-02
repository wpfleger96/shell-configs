#!/usr/bin/env bash

# Linux-specific configuration (shared by native Linux and WSL)
# Automatically included on Linux-based systems

nosleep() {
    local seconds
    seconds=$(_parse_duration_seconds "${1:-24h}") || return 1
    systemd-inhibit --what=idle --who=nosleep --why="Preventing sleep" sleep "$seconds"
}
