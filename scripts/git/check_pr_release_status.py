#!/usr/bin/env python3
"""
Script to check if a GitHub PR has been included in a release.

Usage: python check_pr_release_status.py <PR_URL>
Example: python check_pr_release_status.py https://github.com/block/goose/pull/4020
"""

import json
import re
import subprocess
import sys

from datetime import datetime


def run_gh_command(command: list[str]) -> dict:
    """Run a GitHub CLI command and return the JSON response."""
    try:
        result = subprocess.run(
            ["gh"] + command, capture_output=True, text=True, check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running gh command: {e}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        sys.exit(1)


def parse_pr_url(pr_url: str) -> tuple[str, int]:
    """Parse a GitHub PR URL to extract owner/repo and PR number."""
    pattern = r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.match(pattern, pr_url)
    if not match:
        raise ValueError(f"Invalid PR URL format: {pr_url}")

    owner, repo, pr_number = match.groups()
    return f"{owner}/{repo}", int(pr_number)


def get_pr_info(owner_repo: str, pr_number: int) -> dict:
    """Get PR information including merge commit SHA and merge date."""
    pr_data = run_gh_command(["api", f"repos/{owner_repo}/pulls/{pr_number}"])

    if not pr_data.get("merged"):
        raise ValueError(f"PR #{pr_number} is not merged yet")

    return {
        "merge_commit_sha": pr_data["merge_commit_sha"],
        "merged_at": pr_data["merged_at"],
        "title": pr_data["title"],
        "number": pr_data["number"],
    }


def get_releases_after_date(owner_repo: str, date_str: str) -> list[dict]:
    """Get all releases published after the given date."""
    releases = run_gh_command(["api", f"repos/{owner_repo}/releases", "--paginate"])

    merge_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

    relevant_releases = []
    for release in releases:
        if release.get("published_at"):
            published_date = datetime.fromisoformat(
                release["published_at"].replace("Z", "+00:00")
            )
            if published_date > merge_date:
                relevant_releases.append(
                    {
                        "tag_name": release["tag_name"],
                        "published_at": release["published_at"],
                        "name": release.get("name", release["tag_name"]),
                        "html_url": release["html_url"],
                    }
                )

    # Sort by published date (newest first)
    relevant_releases.sort(key=lambda x: x["published_at"], reverse=True)

    return relevant_releases


def check_commit_in_release(owner_repo: str, release_tag: str, commit_sha: str) -> bool:
    """Check if a commit is included in a release by comparing with the release tag."""
    try:
        # Compare the commit with the release tag
        comparison = run_gh_command(
            ["api", f"repos/{owner_repo}/compare/{release_tag}...{commit_sha}"]
        )

        # If status is "identical", the commit is exactly the release
        # If status is "behind", the commit is included in the release
        # If status is "ahead", the commit is not in the release
        status = comparison.get("status")
        return status in ["identical", "behind"]

    except Exception as e:
        print(f"Warning: Could not compare {commit_sha} with {release_tag}: {e}")
        return False


def main():
    if len(sys.argv) != 2:
        print("Usage: python check_pr_release_status.py <PR_URL>")
        print(
            "Example: python check_pr_release_status.py https://github.com/block/goose/pull/4020"
        )
        sys.exit(1)

    pr_url = sys.argv[1]

    try:
        # Parse PR URL
        owner_repo, pr_number = parse_pr_url(pr_url)
        print(f"Checking PR #{pr_number} in {owner_repo}")

        # Get PR information
        pr_info = get_pr_info(owner_repo, pr_number)
        print(f"PR Title: {pr_info['title']}")
        print(f"Merged at: {pr_info['merged_at']}")
        print(f"Merge commit: {pr_info['merge_commit_sha']}")
        print()

        # Get releases after merge date
        releases = get_releases_after_date(owner_repo, pr_info["merged_at"])

        if not releases:
            print("❌ No releases found after the PR merge date.")
            print("The PR changes have not been released yet.")
            return

        print(f"Found {len(releases)} release(s) after PR merge:")

        # Check each release to see if it includes the PR
        included_in_releases = []

        for release in releases:
            print(
                f"\n🔍 Checking release {release['tag_name']} ({release['published_at']})..."
            )

            if check_commit_in_release(
                owner_repo, release["tag_name"], pr_info["merge_commit_sha"]
            ):
                included_in_releases.append(release)
                print("  ✅ PR is included in this release")
            else:
                print("  ❌ PR is NOT included in this release")

        # Summary
        print("\n" + "=" * 60)
        if included_in_releases:
            print("✅ PR HAS BEEN RELEASED!")
            print(f"The PR is included in {len(included_in_releases)} release(s):")
            for release in included_in_releases:
                print(
                    f"  • {release['name']} ({release['tag_name']}) - {release['published_at']}"
                )
                print(f"    {release['html_url']}")
        else:
            print("❌ PR HAS NOT BEEN RELEASED YET")
            print("The PR was merged but is not included in any published releases.")
            if releases:
                print(
                    f"Latest release: {releases[0]['name']} ({releases[0]['tag_name']})"
                )

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
