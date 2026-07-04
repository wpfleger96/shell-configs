#!/usr/bin/env bash

# Linux-specific configuration (shared by native Linux and WSL)
# Automatically included on Linux-based systems

export ENPASS_VAULT_PATH="$HOME/Documents/Enpass/Vaults/primary"

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
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive -field "Email" env TF_VAR_gcp_alert_email="Gmail Main/GCP Homelab")"

    # Cloudflare (1)
    eval "$(enpass-cli -vault "$ENPASS_VAULT_PATH" -nonInteractive -field "Account Number" env TF_VAR_cloudflare_account_id="Cloudflare")"

    unset MASTERPW
}

nosleep() {
    local seconds
    seconds=$(_parse_duration_seconds "${1:-24h}") || return 1
    systemd-inhibit --what=idle --who=nosleep --why="Preventing sleep" sleep "$seconds"
}
