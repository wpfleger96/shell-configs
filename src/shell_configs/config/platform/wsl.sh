#!/usr/bin/env bash

# WSL-specific configuration
# Automatically included on WSL systems

export BROWSER=wslview

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
        if ! ssh-add -l >/dev/null 2>&1 && [ "$?" -ne 1 ]; then
            _start_ssh_agent
        fi
    else
        _start_ssh_agent
    fi
fi

if ! ssh-add -l >/dev/null 2>&1; then
    ssh-add 2>/dev/null
fi

unset _ssh_agent_env
unset -f _start_ssh_agent

export ENPASS_VAULT_PATH="/mnt/c/Users/Will Pfleger/Documents/Enpass/Vaults/primary"
