# commit_optimization_results.ps1
# TODO #4 — Safe commit script for optimization results
#
# Creates a branch (or commits to current branch), adds optimization artifacts,
# commits, and optionally pushes.
#
# Usage:
#   .\scripts\commit_optimization_results.ps1
#   $env:AUTO_PUSH="true"; .\scripts\commit_optimization_results.ps1
#
# Env vars:
#   AUTO_PUSH=true   — push branch to origin after committing (default: false)
#   BRANCH_NAME      — override the target branch (default: auto-generated)
#   COMMIT_MSG       — override the commit message

param(
    [switch]$AutoPush,
    [string]$BranchName,
    [string]$CommitMsg
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---- Configuration ----------------------------------------------------------
$RepRoot   = Split-Path $PSScriptRoot -Parent
$DataDir   = Join-Path $RepRoot "data\optimization_results"
$ReportDir = Join-Path $RepRoot "reports\historical"
$LogDir    = Join-Path $RepRoot "data\logs"

# Decide whether to auto-push (CLI flag takes precedence over env var)
$doPush = $AutoPush.IsPresent -or ($env:AUTO_PUSH -eq "true")

# Branch name
if (-not $BranchName) {
    $BranchName = $env:BRANCH_NAME
}
if (-not $BranchName) {
    $BranchName = "opt/results-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
}

# Commit message
if (-not $CommitMsg) { $CommitMsg = $env:COMMIT_MSG }
if (-not $CommitMsg) { $CommitMsg = "chore: add optimization results $(Get-Date -Format 'yyyy-MM-dd')" }

# ---- Helpers ----------------------------------------------------------------
function Write-Step([string]$msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg)   { Write-Host "    OK: $msg" -ForegroundColor Green }
function Write-Warn([string]$msg) { Write-Host "    WARN: $msg" -ForegroundColor Yellow }

# ---- Preflight checks -------------------------------------------------------
Write-Step "Checking git status"
Push-Location $RepRoot
try {
    $gitStatus = git status --porcelain 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Not in a git repository or git is not available."
        exit 1
    }

    # Check remote exists
    $remotes = git remote 2>&1
    $hasRemote = ($LASTEXITCODE -eq 0) -and ($remotes -match "origin")

    if (-not $hasRemote) {
        Write-Warn "No 'origin' remote found. Push will be skipped even if AUTO_PUSH is set."
        $doPush = $false
    }
} catch {
    Write-Error "Git check failed: $_"
    exit 1
}

# ---- Collect files to stage -------------------------------------------------
Write-Step "Collecting files to stage"

$filesToAdd = @()

# Optimization results
if (Test-Path $DataDir) {
    $optFiles = Get-ChildItem $DataDir -Filter "*.json" -Recurse | Select-Object -ExpandProperty FullName
    if ($optFiles) {
        $filesToAdd += $optFiles
        Write-Ok "Found $($optFiles.Count) optimization result files"
    } else {
        Write-Warn "No .json files found in $DataDir"
    }
} else {
    Write-Warn "Optimization results directory not found: $DataDir"
}

# Historical accuracy summaries
if (Test-Path $ReportDir) {
    $histFiles = Get-ChildItem $ReportDir -Filter "*.json" -Recurse | Select-Object -ExpandProperty FullName
    $histFiles += Get-ChildItem $ReportDir -Filter "*.md" -Recurse | Select-Object -ExpandProperty FullName
    if ($histFiles) {
        $filesToAdd += $histFiles
        Write-Ok "Found $($histFiles.Count) historical report files"
    }
}

if ($filesToAdd.Count -eq 0) {
    Write-Host "`nNothing to commit — no optimization or historical files found." -ForegroundColor Yellow
    exit 0
}

# ---- Create branch ----------------------------------------------------------
Write-Step "Creating branch: $BranchName"
$currentBranch = git branch --show-current 2>&1
git checkout -b $BranchName 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Warn "Could not create branch '$BranchName'; committing to current branch '$currentBranch'"
}

# ---- Stage files ------------------------------------------------------------
Write-Step "Staging $($filesToAdd.Count) files"
foreach ($file in $filesToAdd) {
    git add $file 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Could not stage: $file"
    }
}

# Check if anything is actually staged
$staged = git diff --cached --name-only 2>&1
if (-not $staged) {
    Write-Host "`nNothing new to commit (all files already tracked and unchanged)." -ForegroundColor Yellow
    git checkout $currentBranch 2>&1 | Out-Null
    git branch -d $BranchName 2>&1 | Out-Null
    exit 0
}

Write-Ok "Staged $($staged.Count) changed files"

# ---- Commit -----------------------------------------------------------------
Write-Step "Committing"
git commit -m $CommitMsg 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "git commit failed"
    exit 1
}
Write-Ok "Committed: $CommitMsg"

# ---- Push (conditional) -----------------------------------------------------
if ($doPush) {
    Write-Step "Pushing branch '$BranchName' to origin"
    git push origin $BranchName 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "git push failed — check your remote access and try manually."
        exit 1
    }
    Write-Ok "Pushed to origin/$BranchName"
    Write-Host "`nNext: open a PR for branch '$BranchName' or merge manually." -ForegroundColor Cyan
} else {
    Write-Host "`nPush skipped (set `$env:AUTO_PUSH='true' or use -AutoPush flag to push)." -ForegroundColor Cyan
    Write-Host "Run: git push origin $BranchName" -ForegroundColor Gray
}

Write-Host "`nDone." -ForegroundColor Green
Pop-Location
