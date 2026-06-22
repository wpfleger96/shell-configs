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

    # Homelab / Proxmox (5)
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive -field "Proxmox API Key ID" env TF_VAR_proxmox_api_key_id="Homelab Consoles")"
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive -field "Proxmox01 API Key Secret" env TF_VAR_proxmox01_api_key_secret="Homelab Consoles")"
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive -field "Proxmox02 API Key Secret" env TF_VAR_proxmox02_api_key_secret="Homelab Consoles")"
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive -field "Container User Password" env TF_VAR_container_user_password="Homelab Consoles")"
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive -field "SSH Public Key" env TF_VAR_ssh_public_key="Homelab Consoles")"

    # AWS (1)
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive -field "Email Address" env TF_VAR_alert_email="AWS")"

    # GCP (4)
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive -field "GCP Project ID" env TF_VAR_gcp_project_id="Gmail Main/GCP Homelab")"
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive -field "GCP Project Number" env TF_VAR_gcp_project_number="Gmail Main/GCP Homelab")"
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive -field "GCP Billing Account ID" env TF_VAR_gcp_billing_account_id="Gmail Main/GCP Homelab")"
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive -field "E-mail" env TF_VAR_gcp_alert_email="Gmail Main/GCP Homelab")"

    # Cloudflare (1)
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive -field "Account Number" env TF_VAR_cloudflare_account_id="Cloudflare")"

    unset MASTERPW
}
