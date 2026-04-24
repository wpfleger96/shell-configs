"""SSH key lifecycle: generation, authentication, and signing."""

from __future__ import annotations

import getpass
import os
import shutil
import socket
import stat
import subprocess

from dataclasses import dataclass
from pathlib import Path

from shell_configs.platform import detect_platform

DEFAULT_GENERATION_PATH = Path.home() / ".ssh" / "id_ed25519"


@dataclass
class StepResult:
    step: str
    success: bool
    message: str
    skipped: bool = False


def generate_ssh_key(
    key_path: Path = DEFAULT_GENERATION_PATH,
    key_type: str = "ed25519",
) -> tuple[bool, str]:
    """Generate SSH keypair if missing. Idempotent."""
    if key_path.exists():
        return True, f"SSH key already exists: {key_path}"

    ssh_dir = key_path.parent
    ssh_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(ssh_dir, stat.S_IRWXU)

    comment = f"{getpass.getuser()}@{socket.gethostname()}"
    cmd = [
        "ssh-keygen",
        "-t",
        key_type,
        "-C",
        comment,
        "-f",
        str(key_path),
        "-N",
        "",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return False, f"ssh-keygen failed: {result.stderr.strip()}"

    os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
    pub_path = key_path.with_suffix(".pub")
    if pub_path.exists():
        os.chmod(pub_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

    return True, f"Generated SSH key: {key_path}"


def ensure_ssh_agent(key_path: Path) -> tuple[bool, str, str | None]:
    """Ensure ssh-agent is running and key is loaded.

    Returns (success, message, public_key_string).
    Exit code 2 from ssh-add means the agent is not running.
    """
    pub_path = key_path.with_suffix(".pub")
    if not pub_path.exists():
        return False, f"Public key not found: {pub_path}", None

    pub_key = pub_path.read_text().strip()
    key_data = pub_key.split()[1] if len(pub_key.split()) >= 2 else ""

    result = subprocess.run(
        ["ssh-add", "-L"], capture_output=True, text=True, timeout=10
    )

    if result.returncode == 2:
        return (
            False,
            "ssh-agent is not running. Start it with: eval $(ssh-agent -s)",
            None,
        )

    if result.returncode == 0 and key_data and key_data in result.stdout:
        return True, "SSH key is loaded in ssh-agent", pub_key

    add_result = subprocess.run(
        ["ssh-add", str(key_path)], capture_output=True, text=True, timeout=10
    )
    if add_result.returncode != 0:
        return (
            False,
            f"Failed to add key to ssh-agent: {add_result.stderr.strip()}",
            None,
        )

    return True, "Added SSH key to ssh-agent", pub_key


def ensure_gh_auth(interactive: bool = True) -> tuple[bool, str]:
    """Ensure GitHub CLI is authenticated."""
    if not shutil.which("gh"):
        return (
            False,
            "GitHub CLI (gh) not installed - run 'shell-configs packages install'",
        )

    auth_check = subprocess.run(
        ["gh", "auth", "status"], capture_output=True, timeout=10
    )
    if auth_check.returncode == 0:
        return True, "GitHub CLI is authenticated"

    if not interactive:
        return (
            False,
            "GitHub CLI not authenticated. Run 'shell-configs signing --fix' in an interactive terminal",
        )

    login_result = subprocess.run(["gh", "auth", "login"], timeout=120)
    if login_result.returncode == 0:
        return True, "GitHub CLI authenticated successfully"
    return False, "GitHub CLI authentication failed"


def ensure_gh_scopes(
    scopes: list[str] | None = None, interactive: bool = True
) -> tuple[bool, str]:
    """Ensure required OAuth scopes for key management."""
    if scopes is None:
        scopes = ["admin:public_key", "admin:ssh_signing_key"]

    test_result = subprocess.run(
        ["gh", "ssh-key", "list"], capture_output=True, text=True, timeout=30
    )
    if test_result.returncode == 0:
        return True, "Required OAuth scopes are present"

    if not interactive:
        return (
            False,
            f"Missing OAuth scopes ({', '.join(scopes)}). Run 'shell-configs signing --fix' interactively",
        )

    scopes_arg = ",".join(scopes)
    refresh_result = subprocess.run(
        ["gh", "auth", "refresh", "-h", "github.com", "-s", scopes_arg],
        timeout=120,
    )
    if refresh_result.returncode == 0:
        return True, "OAuth scopes granted"
    return False, "Failed to refresh OAuth scopes"


def upload_auth_key(key_path: Path) -> tuple[bool, str]:
    """Upload public key as a GitHub authentication key. Always reads .pub."""
    pub_path = key_path.with_suffix(".pub")
    if not pub_path.exists():
        return False, f"Public key not found: {pub_path}"

    pub_parts = pub_path.read_text().strip().split()
    pub_key_data = pub_parts[1] if len(pub_parts) >= 2 else ""

    existing = subprocess.run(
        ["gh", "ssh-key", "list"], capture_output=True, text=True, timeout=30
    )
    if existing.returncode == 0 and pub_key_data and pub_key_data in existing.stdout:
        return True, "SSH auth key already uploaded to GitHub"

    title = socket.gethostname()
    add_result = subprocess.run(
        ["gh", "ssh-key", "add", str(pub_path), "--title", title],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if add_result.returncode == 0:
        return True, f"Uploaded SSH auth key to GitHub (title: {title})"
    return False, f"Failed to upload auth key: {add_result.stderr.strip()}"


@dataclass
class StaleKeyInfo:
    title: str
    key_type: str
    fingerprint: str


def find_stale_github_keys(
    key_path: Path,
) -> tuple[list[StaleKeyInfo], str | None]:
    """Find GitHub SSH keys that don't match the current machine's key.

    Returns (stale_keys, current_fingerprint). Compares fingerprints of all
    GitHub SSH keys against the local key at key_path.pub.
    """
    pub_path = key_path.with_suffix(".pub")
    if not pub_path.exists():
        return [], None

    current_fp = get_key_fingerprint(pub_path.read_text().strip())
    if not current_fp:
        return [], None

    result = subprocess.run(
        ["gh", "ssh-key", "list"], capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return [], current_fp

    stale: list[StaleKeyInfo] = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        title, gh_key_id, key_type_field, fingerprint = (
            parts[0],
            parts[1],
            parts[2],
            parts[3] if len(parts) > 3 else "",
        )
        _ = gh_key_id
        if fingerprint and fingerprint != current_fp:
            stale.append(
                StaleKeyInfo(
                    title=title,
                    key_type=key_type_field,
                    fingerprint=fingerprint,
                )
            )

    return stale, current_fp


def delete_github_key_by_fingerprint(fingerprint: str) -> tuple[bool, str]:
    """Delete a GitHub SSH key by its fingerprint.

    Uses `gh api` to find the key ID by fingerprint, then deletes it.
    """
    for endpoint in ["/user/keys", "/user/ssh_signing_keys"]:
        list_result = subprocess.run(
            ["gh", "api", endpoint, "--paginate"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if list_result.returncode != 0:
            continue

        import json

        try:
            keys = json.loads(list_result.stdout)
        except json.JSONDecodeError:
            continue

        for key_obj in keys:
            key_str = key_obj.get("key", "")
            key_fp = get_key_fingerprint(key_str)
            if key_fp == fingerprint:
                key_id = key_obj.get("id")
                delete_result = subprocess.run(
                    ["gh", "api", "-X", "DELETE", f"{endpoint}/{key_id}"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if delete_result.returncode == 0:
                    return True, f"Deleted key {fingerprint} (id: {key_id})"
                return False, f"Failed to delete key: {delete_result.stderr.strip()}"

    return False, f"Key with fingerprint {fingerprint} not found via API"


def find_local_ssh_keys() -> list[Path]:
    """Find all SSH private keys in ~/.ssh/ that have a matching .pub file."""
    ssh_dir = Path.home() / ".ssh"
    if not ssh_dir.is_dir():
        return []
    keys = []
    for pub_file in sorted(ssh_dir.glob("id_*.pub")):
        private = pub_file.with_suffix("")
        if private.exists():
            keys.append(private)
    return keys


def get_key_fingerprint_from_pub(pub_path: Path) -> str | None:
    """Get SHA256 fingerprint of a .pub key file."""
    result = subprocess.run(
        ["ssh-keygen", "-lf", str(pub_path)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return None
    parts = result.stdout.strip().split()
    return parts[1] if len(parts) >= 2 else None


def get_github_key_fingerprints() -> set[str]:
    """Get fingerprints of all SSH keys registered on the user's GitHub account.

    Computes fingerprints from key data in `gh ssh-key list` output.
    Column format: title \\t key_data \\t date \\t id \\t type
    """
    if not shutil.which("gh"):
        return set()
    result = subprocess.run(
        ["gh", "ssh-key", "list"], capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return set()
    fingerprints: set[str] = set()
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            key_data = parts[1].strip()
            fp = get_key_fingerprint(key_data)
            if fp:
                fingerprints.add(fp)
    return fingerprints


def discover_managed_key(
    local_keys: list[Path], github_fingerprints: set[str]
) -> Path | None:
    """Match a local key against GitHub-registered keys by fingerprint."""
    for key_path in local_keys:
        fp = get_key_fingerprint_from_pub(key_path.with_suffix(".pub"))
        if fp and fp in github_fingerprints:
            return key_path
    return None


def _resolve_key_path(
    key_path: Path | None,
    auto_fix: bool,
    interactive: bool,
    results: list[StepResult],
) -> Path | None:
    """Resolve which SSH key to manage.

    Discovery flow:
    1. Enumerate local keys
    2. If gh is authed, match against GitHub by fingerprint
    3. Decision matrix: 0 keys→generate, 1 key→use it, match→use match, 2+→prompt
    """
    if key_path is not None:
        return key_path

    local_keys = find_local_ssh_keys()
    github_fps = get_github_key_fingerprints()

    if github_fps:
        matched = discover_managed_key(local_keys, github_fps)
        if matched:
            results.append(
                StepResult("discover_key", True, f"SSH key matched GitHub: {matched}")
            )
            return matched

    if not local_keys:
        if auto_fix:
            results.append(
                StepResult(
                    "discover_key",
                    True,
                    f"No SSH keys found, will generate: {DEFAULT_GENERATION_PATH}",
                )
            )
            return DEFAULT_GENERATION_PATH
        results.append(
            StepResult(
                "discover_key",
                False,
                "No SSH keys found. Run 'shell-configs signing --fix' to generate one",
            )
        )
        return None

    if len(local_keys) == 1:
        results.append(
            StepResult("discover_key", True, f"SSH key found: {local_keys[0]}")
        )
        return local_keys[0]

    if not auto_fix:
        key_list = ", ".join(str(k) for k in local_keys)
        results.append(
            StepResult(
                "discover_key",
                False,
                f"{len(local_keys)} SSH keys found, none registered on GitHub ({key_list}). "
                "Run 'shell-configs signing --fix' to select one",
            )
        )
        return None

    if not interactive:
        results.append(
            StepResult(
                "discover_key",
                False,
                f"{len(local_keys)} SSH keys found, none match GitHub. "
                "Run 'shell-configs signing --fix' interactively to select",
                skipped=True,
            )
        )
        return None

    from rich.prompt import IntPrompt

    from shell_configs.display import console

    console.print(
        "\n[yellow]Multiple SSH keys found, none registered on your GitHub account:[/yellow]\n"
    )
    for i, kp in enumerate(local_keys, 1):
        fp = get_key_fingerprint_from_pub(kp.with_suffix(".pub")) or "unknown"
        key_type = kp.name.split("_", 1)[1] if "_" in kp.name else "unknown"
        console.print(f"  {i}. {kp} ({key_type.upper()}, {fp})")

    console.print()
    choice = IntPrompt.ask(
        "Which key should shell-configs manage?",
        choices=[str(i) for i in range(1, len(local_keys) + 1)],
    )
    selected = local_keys[choice - 1]
    results.append(StepResult("discover_key", True, f"Selected SSH key: {selected}"))
    return selected


def setup_signing(
    key_path: Path | None = None,
    auto_fix: bool = False,
    interactive: bool = True,
    dry_run: bool = False,
) -> list[StepResult]:
    """Full SSH key lifecycle. Discovers and threads key_path through every step.

    Step order: enumerate → gh auth → scopes → discover match → resolve key →
    agent → upload auth → register signing → allowed_signers
    """
    results: list[StepResult] = []

    if not auto_fix:
        return _validate_all_steps(key_path)

    if dry_run:
        results.append(
            StepResult("gh_auth", True, "Would ensure GitHub CLI is authenticated")
        )
    else:
        ok, msg = ensure_gh_auth(interactive=interactive)
        results.append(
            StepResult("gh_auth", ok, msg, skipped=not ok and not interactive)
        )
        if not ok and interactive:
            return results

    if dry_run:
        results.append(StepResult("gh_scopes", True, "Would ensure OAuth scopes"))
    else:
        ok, msg = ensure_gh_scopes(interactive=interactive)
        results.append(
            StepResult("gh_scopes", ok, msg, skipped=not ok and not interactive)
        )
        if not ok and interactive:
            return results

    if dry_run:
        local_keys = find_local_ssh_keys()
        if key_path:
            results.append(
                StepResult("discover_key", True, f"Using specified key: {key_path}")
            )
        elif local_keys:
            results.append(
                StepResult(
                    "discover_key",
                    True,
                    f"Would discover key from {len(local_keys)} local key(s)",
                )
            )
            key_path = local_keys[0]
        else:
            results.append(
                StepResult(
                    "discover_key",
                    True,
                    f"No local keys, would generate: {DEFAULT_GENERATION_PATH}",
                )
            )
            key_path = DEFAULT_GENERATION_PATH
    else:
        key_path = _resolve_key_path(key_path, auto_fix, interactive, results)
        if key_path is None:
            return results

    if not key_path.exists():
        if dry_run:
            results.append(
                StepResult("generate_key", True, f"Would generate SSH key: {key_path}")
            )
        else:
            ok, msg = generate_ssh_key(key_path)
            results.append(StepResult("generate_key", ok, msg))
            if not ok:
                return results
    else:
        results.append(
            StepResult(
                "generate_key", True, f"SSH key exists: {key_path}", skipped=True
            )
        )

    if dry_run:
        results.append(
            StepResult("ssh_agent", True, "Would ensure key is in ssh-agent")
        )
    else:
        ok, msg, pub_key = ensure_ssh_agent(key_path)
        results.append(StepResult("ssh_agent", ok, msg))
        if not ok:
            return results

    if dry_run:
        results.append(
            StepResult("upload_auth", True, "Would upload SSH auth key to GitHub")
        )
    else:
        ok, msg = upload_auth_key(key_path)
        results.append(StepResult("upload_auth", ok, msg))

    if dry_run:
        results.append(
            StepResult("register_signing", True, "Would register SSH signing key")
        )
    else:
        pub_key_str = _read_pub_key(key_path)
        if pub_key_str:
            ok, msg = register_signing_key(pub_key_str, auto_refresh_scope=False)
            results.append(StepResult("register_signing", ok, msg))
        else:
            results.append(
                StepResult("register_signing", False, "Could not read public key")
            )

    allowed_signers = Path.home() / ".config" / "git" / "allowed_signers"
    if dry_run:
        results.append(
            StepResult("allowed_signers", True, "Would generate allowed_signers")
        )
    else:
        ok, msg = generate_allowed_signers_file(allowed_signers)
        results.append(StepResult("allowed_signers", ok, msg))

    return results


def _read_pub_key(key_path: Path) -> str | None:
    """Read the public key string from key_path.pub."""
    pub_path = key_path.with_suffix(".pub")
    if not pub_path.exists():
        return None
    return pub_path.read_text().strip()


def _validate_all_steps(key_path: Path | None) -> list[StepResult]:
    """Validate all SSH lifecycle steps without fixing.

    Uses GitHub-as-source-of-truth discovery to find the managed key.
    """
    results: list[StepResult] = []

    ok, msg = ensure_gh_auth(interactive=False)
    results.append(StepResult("gh_auth", ok, msg))

    gh_authed = ok
    if gh_authed:
        ok, msg = ensure_gh_scopes(interactive=False)
        results.append(StepResult("gh_scopes", ok, msg))
        gh_has_scopes = ok
    else:
        gh_has_scopes = False

    key_path = _resolve_key_path(
        key_path, auto_fix=False, interactive=False, results=results
    )
    if key_path is None:
        return results

    if not key_path.exists():
        results.append(
            StepResult("generate_key", False, f"SSH key missing: {key_path}")
        )
        return results
    results.append(StepResult("generate_key", True, f"SSH key exists: {key_path}"))

    ok, msg, _ = ensure_ssh_agent(key_path)
    results.append(StepResult("ssh_agent", ok, msg))

    if gh_authed and gh_has_scopes:
        pub_key_data = ""
        pub_path = key_path.with_suffix(".pub")
        if pub_path.exists():
            parts = pub_path.read_text().strip().split()
            if len(parts) >= 2:
                pub_key_data = parts[1]

        existing = subprocess.run(
            ["gh", "ssh-key", "list"], capture_output=True, text=True, timeout=30
        )
        has_auth_key = False
        has_signing_key = False
        if existing.returncode == 0 and pub_key_data:
            for line in existing.stdout.strip().split("\n"):
                if not line.strip() or pub_key_data not in line:
                    continue
                cols = line.split("\t")
                key_type = cols[4].strip().lower() if len(cols) >= 5 else ""
                if key_type == "authentication":
                    has_auth_key = True
                elif key_type == "signing":
                    has_signing_key = True

        if has_auth_key:
            results.append(StepResult("upload_auth", True, "SSH auth key is on GitHub"))
        else:
            results.append(
                StepResult("upload_auth", False, "SSH auth key not found on GitHub")
            )

        if has_signing_key:
            results.append(
                StepResult(
                    "register_signing",
                    True,
                    "SSH signing key is registered with GitHub",
                )
            )
        else:
            results.append(
                StepResult(
                    "register_signing",
                    False,
                    "SSH key not registered for signing. Run 'shell-configs signing --fix'",
                )
            )

    return results


def get_signing_key_title() -> str:
    """Generate a unique title for the SSH signing key."""
    user = getpass.getuser()
    hostname = socket.gethostname()
    platform = detect_platform().display_name
    return f"shell-configs signing key ({user}@{hostname}, {platform})"


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
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 5 and parts[4].strip().lower() == "signing":
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
    key_parts = key.strip().split()
    key_data = key_parts[1] if len(key_parts) >= 2 else ""
    if key_data:
        for signing_line in get_github_signing_keys():
            parts = signing_line.split("\t")
            if len(parts) >= 2 and key_data in parts[1]:
                return True, "SSH signing key already registered with GitHub"

    result = subprocess.run(
        [
            "gh",
            "api",
            "/user/ssh_signing_keys",
            "-f",
            f"key={key}",
            "-f",
            f"title={get_signing_key_title()}",
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
                    f"title={get_signing_key_title()}",
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
