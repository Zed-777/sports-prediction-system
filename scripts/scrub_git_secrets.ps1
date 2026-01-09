<#
Script: scrub_git_secrets.ps1
Purpose: Helper to remove `.env` contents and `.env` file from all Git history using git-filter-repo.

Prereqs:
- Install git-filter-repo (https://github.com/newren/git-filter-repo)
- Run this locally on a clone; it rewrites history.

WARNING: This rewrites Git history and will force push; ensure you have backups and notify contributors.
#>

param(
    [string]$pattern = '.env'
)

Write-Host "This script will remove ${pattern} from git history in the current repository" -ForegroundColor Yellow
Write-Host "Make a backup: git bundle create repo-backup.bundle --all" -ForegroundColor Magenta

if (-not (Get-Command git-filter-repo -ErrorAction SilentlyContinue)) {
    Write-Host "git-filter-repo not found. Install it first: https://github.com/newren/git-filter-repo" -ForegroundColor Red
    exit 1
}

Write-Host "Creating backup..."
git bundle create repo-backup.bundle --all

Write-Host "Running git-filter-repo to remove files matching ${pattern}..."
git filter-repo --invert-paths --paths $pattern

Write-Host "History rewritten. Force-push to origin (if desired): git push --force --all" -ForegroundColor Red

Write-Host "IMPORTANT: Also delete the file in the remote server and rotate keys in your providers." -ForegroundColor Red
