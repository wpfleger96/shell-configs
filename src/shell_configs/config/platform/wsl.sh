#!/usr/bin/env bash

# WSL-specific configuration
# Automatically included on WSL systems

# Use wslview to open URLs in Windows default browser
export BROWSER=wslview

# SSH Agent - auto-start for WSL with socket persistence
# On macOS, ssh-agent is managed by launchd; on WSL we need to start it manually
# This reuses the same agent across shell sessions (until reboot)
_ssh_agent_env="$HOME/.ssh/agent.env"

_start_ssh_agent() {
    ssh-agent -s >"$_ssh_agent_env"
    chmod 600 "$_ssh_agent_env"
    # shellcheck source=/dev/null
    . "$_ssh_agent_env" >/dev/null
}

if [ -z "$SSH_AUTH_SOCK" ]; then
    if [ -f "$_ssh_agent_env" ]; then
        # shellcheck source=/dev/null
        . "$_ssh_agent_env" >/dev/null
        # Check if the agent is still running
        if ! ssh-add -l >/dev/null 2>&1 && [ "$?" -ne 1 ]; then
            _start_ssh_agent
        fi
    else
        _start_ssh_agent
    fi
fi

unset _ssh_agent_env
unset -f _start_ssh_agent
