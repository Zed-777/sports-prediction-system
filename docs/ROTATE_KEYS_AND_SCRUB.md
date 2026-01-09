# Rotate API Keys & Scrub Secrets from Git History

This guide explains how to safely rotate API keys and scrub secrets from Git history.

IMPORTANT: This operation rewrites Git history; coordinate with team and create backups.

Steps to scrub `.env` from Git and rotate keys:

1. Make a full repository backup:

```powershell
git bundle create repo-backup.bundle --all
```

1. Run git-filter-repo locally (this rewrites history):

PowerShell:

```powershell
# Install git-filter-repo and run
git filter-repo --invert-paths --paths .env
```

Linux/macOS:

```bash
git filter-repo --invert-paths --paths .env
```

1. Force push to origin *after* communicating with the team (warning: this rewrites history for all contributors):

```bash
git push --force --all
git push --force --tags
```

1. Rotate keys at the provider portals (Football-Data.org / API-Football / others):

- Login to provider dashboard
- Revoke the old key
- Create a new key
- Update the `secrets` in CI and the `.env` for local use (do not commit keys)

1. Verify the new keys are working using the scripts included:

  ```powershell
  # Check Football-Data key
  python scripts/check_football_data_key.py
  # Check all keys
  python scripts/list_api_keys_status.py
  ```

1. Optional: If old keys were used in other systems, rotate/purge them there as well.

Notes:

- The repo now includes a helper `scripts/scrub_git_secrets.sh` and `scripts/scrub_git_secrets.ps1`.
- It is your responsibility to back up data before rewriting history.
- After rewriting history, other contributors must re-clone the repository to avoid synchronization issues.
