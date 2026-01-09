#!/usr/bin/env bash
# scrub_git_secrets.sh - *nix helper
# Usage: run in repo root. Backups created automatically.
set -euo pipefail

echo "Create a git bundle backup..."
git bundle create repo-backup.bundle --all

if ! command -v git-filter-repo >/dev/null 2>&1; then
  echo "git-filter-repo is not installed. Install via 'pip install git-filter-repo' or see https://github.com/newren/git-filter-repo"
  exit 1
fi

read -p "This will rewrite history and remove '.env' from all commits. Continue? (y/N) " warning
if [[ ${warning:-N} != "y" ]]; then
  echo "Aborting. No changes made."
  exit 1
fi

git filter-repo --invert-paths --paths .env
echo "Done. Please force push if you want to update remotes: git push --force --all"
