"""SSH signing key validation and setup."""

import shutil
import subprocess

from pathlib import Path


def get_agent_keys() -> list[str]:
    """Get SSH public keys from ssh-agent."""
    result = subprocess.run(
        ["ssh-add", "-L"], capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]


def get_github_signing_keys() -> list[str]:
    """Get SSH signing keys registered with GitHub."""
    if not shutil.which("gh"):
        return []

    result = subprocess.run(
        ["gh", "ssh-key", "list"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return []

    signing_keys = []
    for line in result.stdout.strip().split("\n"):
        if "signing" in line.lower():
            signing_keys.append(line)
    return signing_keys


def key_is_registered(agent_key: str, github_keys: list[str]) -> bool:
    """Check if an agent key matches any GitHub signing key."""
    agent_parts = agent_key.split()
    if len(agent_parts) < 2:
        return False
    agent_key_data = agent_parts[1]

    for gh_key in github_keys:
        if agent_key_data in gh_key:
            return True
    return False


def get_key_fingerprint(key: str) -> str:
    """Get SHA256 fingerprint of an SSH key."""
    result = subprocess.run(
        ["ssh-keygen", "-lf", "-"],
        input=key,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return ""
    parts = result.stdout.strip().split()
    return parts[1] if len(parts) >= 2 else ""


def register_signing_key(key: str, auto_refresh_scope: bool = True) -> tuple[bool, str]:
    """Register an SSH key as a signing key with GitHub.

    Args:
        key: SSH public key to register
        auto_refresh_scope: If True, automatically refresh gh auth when scope is missing

    Returns:
        (success, message) tuple
    """
    result = subprocess.run(
        [
            "gh",
            "api",
            "/user/ssh_signing_keys",
            "-f",
            f"key={key}",
            "-f",
            "title=shell-configs signing key",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode == 0:
        return True, "SSH key registered for signing"

    error_msg = result.stderr.strip()

    if auto_refresh_scope and "admin:ssh_signing_key" in error_msg:
        refresh_result = subprocess.run(
            [
                "gh",
                "auth",
                "refresh",
                "-h",
                "github.com",
                "-s",
                "admin:ssh_signing_key",
            ],
            timeout=120,
        )

        if refresh_result.returncode == 0:
            retry_result = subprocess.run(
                [
                    "gh",
                    "api",
                    "/user/ssh_signing_keys",
                    "-f",
                    f"key={key}",
                    "-f",
                    "title=shell-configs signing key",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if retry_result.returncode == 0:
                return True, "SSH key registered for signing (after auth refresh)"
            return False, retry_result.stderr.strip()
        else:
            return False, "Failed to refresh GitHub authentication scope"

    return False, error_msg


def validate_signing_setup(auto_fix: bool = False) -> tuple[bool, str]:
    """Validate SSH signing key is registered with GitHub.

    Returns (success, message).
    """
    if not shutil.which("gh"):
        return (
            False,
            "GitHub CLI (gh) not installed - run 'shell-configs packages install'",
        )

    auth_check = subprocess.run(
        ["gh", "auth", "status"], capture_output=True, timeout=10
    )
    if auth_check.returncode != 0:
        return False, "GitHub CLI not authenticated - run 'gh auth login'"

    agent_keys = get_agent_keys()
    if not agent_keys:
        return False, "No SSH keys in ssh-agent - run 'ssh-add'"

    github_keys = get_github_signing_keys()

    for key in agent_keys:
        if key_is_registered(key, github_keys):
            return True, "SSH signing key is registered with GitHub"

    if not auto_fix:
        return (
            False,
            "SSH key not registered for signing. Run 'shell-configs signing --fix'",
        )

    success, msg = register_signing_key(agent_keys[0])
    if success:
        return True, "Registered SSH key for signing with GitHub"
    return False, f"Failed to register key: {msg}"


def generate_allowed_signers_file(
    allowed_signers_path: Path, emails: list[str] | None = None
) -> tuple[bool, str]:
    """Generate allowed_signers file with SSH keys from ssh-agent.

    Creates entries for all provided email addresses with all available SSH keys.

    Args:
        allowed_signers_path: Path where allowed_signers file should be created
        emails: List of email addresses to include. If None, uses default emails.

    Returns:
        (success, message) tuple
    """
    agent_keys = get_agent_keys()
    if not agent_keys:
        return False, "No SSH keys in ssh-agent - run 'ssh-add'"

    if emails is None:
        emails = [
            "pfleger.will@gmail.com",
            "wpfleger@block.xyz",
        ]

    lines = []
    for email in emails:
        for key in agent_keys:
            lines.append(f"{email} {key}")

    new_content = "\n".join(lines) + "\n"

    file_exists = allowed_signers_path.exists()
    if file_exists:
        existing_content = allowed_signers_path.read_text()
        if existing_content == new_content:
            return True, f"allowed_signers is up to date with {len(agent_keys)} key(s)"

    allowed_signers_path.parent.mkdir(parents=True, exist_ok=True)
    allowed_signers_path.write_text(new_content)

    if file_exists:
        return True, f"Updated allowed_signers with {len(agent_keys)} key(s)"
    else:
        return True, f"Generated allowed_signers with {len(agent_keys)} key(s)"


def get_signing_key_info() -> dict[str, str] | None:
    """Get detailed info about the active signing key.

    Returns dict with: key_type, fingerprint, github_title, git_name, git_email
    """
    agent_keys = get_agent_keys()
    if not agent_keys:
        return None

    github_keys = get_github_signing_keys()

    for key in agent_keys:
        if key_is_registered(key, github_keys):
            parts = key.split()
            key_type = parts[0] if parts else "unknown"
            comment = parts[2] if len(parts) >= 3 else ""

            fingerprint = get_key_fingerprint(key)

            github_title = None
            if len(parts) >= 2:
                key_data = parts[1]
                for gh_key in github_keys:
                    if key_data in gh_key:
                        github_title = gh_key.split("\t")[0]
                        break

            git_name = subprocess.run(
                ["git", "config", "user.name"],
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()

            git_email = subprocess.run(
                ["git", "config", "user.email"],
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()

            return {
                "key_type": key_type,
                "fingerprint": fingerprint,
                "comment": comment,
                "github_title": github_title or "",
                "git_name": git_name,
                "git_email": git_email,
            }

    return None
