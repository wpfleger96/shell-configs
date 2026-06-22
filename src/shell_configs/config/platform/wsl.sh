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

load-tf-secrets() {
    if ! command -v enpass-cli >/dev/null 2>&1; then
        echo "Error: enpass-cli not found. Run: shell-configs packages install" >&2
        return 1
    fi
    if [[ -z "$ENPASS_VAULT_PATH" ]]; then
        echo "Error: ENPASS_VAULT_PATH not set." >&2
        return 1
    fi

    # Prompt once — exported so all enpass-cli calls below can run non-interactively.
    read -rs -p "Enpass master password: " MASTERPW && echo
    export MASTERPW

    # Homelab / Proxmox (4) — TODO: fill in Enpass entry titles and field labels
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive env -field "FIELD_LABEL" TF_VAR_proxmox_api_key_id="ENTRY_TITLE")"
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive env -field "FIELD_LABEL" TF_VAR_proxmox02_api_key_secret="ENTRY_TITLE")"
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive env -field "FIELD_LABEL" TF_VAR_container_user_password="ENTRY_TITLE")"
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive env -field "FIELD_LABEL" TF_VAR_ssh_public_key="ENTRY_TITLE")"

    # AWS (1) — TODO: fill in Enpass entry title and field label
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive env -field "FIELD_LABEL" TF_VAR_alert_email="ENTRY_TITLE")"

    # GCP (4) — TODO: fill in Enpass entry titles and field labels
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive env -field "FIELD_LABEL" TF_VAR_gcp_project_id="ENTRY_TITLE")"
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive env -field "FIELD_LABEL" TF_VAR_gcp_project_number="ENTRY_TITLE")"
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive env -field "FIELD_LABEL" TF_VAR_gcp_billing_account_id="ENTRY_TITLE")"
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive env -field "FIELD_LABEL" TF_VAR_gcp_alert_email="ENTRY_TITLE")"

    # Cloudflare (1) — TODO: fill in Enpass entry title and field label
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive env -field "FIELD_LABEL" TF_VAR_cloudflare_account_id="ENTRY_TITLE")"

    unset MASTERPW
}
