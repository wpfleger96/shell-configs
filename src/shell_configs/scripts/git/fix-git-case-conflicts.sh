#!/usr/bin/env bash

# Fix Git case-sensitivity conflicts on macOS

# Enable auto-pruning to prevent stale ref accumulation
git config --global fetch.prune true

# Fix refs in current repo (consolidates into single file)
git pack-refs --all

# Clean up any existing stale references
git remote prune origin

# Try to fetch just the current branch to avoid conflicts
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ "$BRANCH" != "HEAD" ]; then
    git fetch origin "$BRANCH" && git merge "origin/$BRANCH"
else
    echo "Note: In detached HEAD state. Run 'git fetch origin <branch>' manually."
fi

echo "Done! If you still get errors, try: git fetch origin <branch> && git merge origin/<branch>"
