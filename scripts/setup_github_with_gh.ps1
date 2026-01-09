<#
PowerShell helper: Setup GitHub repository and repo secrets using GitHub CLI (gh)

Features:
- Verifies that `gh` is installed and the user is authenticated (runs `gh auth login` if needed)
- Detects or creates a GitHub repo and sets it as git remote
- Reads local `.env` file and sets repository secrets (skips GITHUB_TOKEN)
- Optionally enables and dispatches workflows under `.github/workflows`

Usage:
  # Interactive (recommended)
  powershell -ExecutionPolicy Bypass -File scripts\setup_github_with_gh.ps1

  # Non-interactive: provide repo and --public/--private
  powershell -ExecutionPolicy Bypass -File scripts\setup_github_with_gh.ps1 -RepoOwner myorg -RepoName myrepo -Visibility public

Security:
- This script will not commit or echo secret values.
- It will skip setting a repository secret named GITHUB_TOKEN to avoid overriding Actions built-in token.

#>
param(
    [string]$RepoOwner = '',
    [string]$RepoName = '',
    [ValidateSet('public','private')][string]$Visibility = 'public',
    [switch]$NonInteractive
)

function Write-Err([string]$msg) { Write-Host $msg -ForegroundColor Red }
function Write-Ok([string]$msg) { Write-Host $msg -ForegroundColor Green }

# Check for gh
try {
    Get-Command gh -ErrorAction Stop | Out-Null
} catch {
    Write-Err "GitHub CLI 'gh' is not installed. Install from https://cli.github.com/ and re-run this script."
    exit 2
}

# Ensure gh auth
$authOk = $false
try {
    gh auth status --hostname github.com > $null 2>&1
    if ($LASTEXITCODE -eq 0) { $authOk = $true }
} catch { $authOk = $false }

if (-not $authOk) {
    if ($NonInteractive) {
        Write-Err "Not authenticated and running non-interactive. Run 'gh auth login' manually."
        exit 3
    }
    Write-Host "You're not authenticated with GitHub CLI. Running interactive 'gh auth login'..." -ForegroundColor Yellow
    gh auth login
    if ($LASTEXITCODE -ne 0) { Write-Err "gh auth login failed. Aborting."; exit 4 }
}

# Determine repo name
$repoFull = ''
if (-not [string]::IsNullOrWhiteSpace($RepoOwner) -and -not [string]::IsNullOrWhiteSpace($RepoName)) {
    $repoFull = "$RepoOwner/$RepoName"
} else {
    # Try to infer from existing git remote
    try {
        $origin = git remote get-url origin 2>$null
        if ($origin) {
            # Normalize origin to owner/repo
            if ($origin -match 'github.com[:/](.+?)/(.+?)(?:\.git)?$') {
                $repoFull = "$($matches[1])/$($matches[2])"
                Write-Host "Detected remote repo: $repoFull" -ForegroundColor Cyan
            }
        }
    } catch { }

    if (-not $repoFull -and -not $NonInteractive) {
        $repoFull = Read-Host "Enter GitHub repo (owner/repo). Leave blank to create a new repo"
    }
}

# If repo not provided, offer to create it
if (-not $repoFull) {
    if ($NonInteractive) { Write-Err "Repo not specified in non-interactive mode."; exit 5 }
    $create = Read-Host "No repo specified. Create a new repo on GitHub from this directory? (y/N)"
    if ($create -ne 'y' -and $create -ne 'Y') { Write-Err "Aborted (no repo)."; exit 6 }

    $defaultName = (Get-Item -Path .).BaseName
    if (-not [string]::IsNullOrWhiteSpace($RepoName)) { $defaultName = $RepoName }
    $name = Read-Host "Repository name" -Default $defaultName

    $vis = $Visibility
    Write-Host "Creating repository: $name (visibility: $vis)" -ForegroundColor Cyan
    gh repo create $name --$vis --source=. --remote=origin --push
    if ($LASTEXITCODE -ne 0) { Write-Err "gh repo create failed."; exit 7 }

    # Determine full name from gh
    $info = gh repo view --json nameWithOwner -q .nameWithOwner
    if ($info) { $repoFull = $info.Trim() }
}

# Validate repo exists
try {
    gh repo view $repoFull --json name > $null 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Err "Repository $repoFull not accessible. Check permissions."; exit 8 }
    Write-Ok "Repository confirmed: $repoFull"
} catch {
    Write-Err "Failed to reach repository $repoFull: $_"; exit 9
}

# Ensure git remote is set
try {
    $cur = git remote get-url origin 2>$null
    if (-not $cur) {
        $cloneUrl = gh repo view $repoFull --json sshUrl -q .sshUrl
        if ($cloneUrl) {
            git remote add origin $cloneUrl
            Write-Ok "Added git remote origin -> $cloneUrl"
        }
    } else {
        Write-Host "Existing git remote origin: $cur" -ForegroundColor Cyan
    }
} catch {
    Write-Err "Failed to configure git remote: $_"
}

# Read .env
$envFile = Join-Path $PSScriptRoot '..\.env'
$envFile = (Resolve-Path $envFile -ErrorAction SilentlyContinue).Path
if (-not $envFile) {
    Write-Host "No .env file found in project root. If you want to set secrets from a file, create .env first." -ForegroundColor Yellow
} else {
    $lines = Get-Content $envFile | Where-Object {$_ -and -not $_.Trim().StartsWith('#')}
    $kv = @{}
    foreach ($line in $lines) {
        if ($line -match '^(\s*([^=]+)\s*)=(.*)$') {
            $k = $matches[2].Trim()
            $v = $matches[3]
            # Skip blank or variables that are intentionally omitted
            if (-not $v) { continue }
            $kv[$k] = $v
        }
    }

    if ($kv.Count -gt 0) {
        Write-Host "Found the following possible secrets in .env:" -ForegroundColor Cyan
        $kv.Keys | ForEach-Object { Write-Host "  - $_" }
        if ($NonInteractive) {
            $toSet = $kv.Keys
        } else {
            $ok = Read-Host "Set these as repo secrets for $repoFull? (y/N)"
            if ($ok -ne 'y' -and $ok -ne 'Y') { Write-Host "Skipping secret setup." } else { $toSet = $kv.Keys }
        }

        if ($toSet) {
            foreach ($name in $toSet) {
                if ($name -eq 'GITHUB_TOKEN') { Write-Host "Skipping GITHUB_TOKEN (do not set this as a repo secret)."; continue }
                $value = $kv[$name]
                # Use gh secret set (safe) - do not echo value
                try {
                    echo "Setting secret: $name"
                    gh secret set $name --body "$value" --repo $repoFull
                    if ($LASTEXITCODE -eq 0) { Write-Ok "Secret $name set" } else { Write-Err "Failed to set $name" }
                } catch {
                    Write-Err "Error setting secret $name: $_"
                }
            }
        }
    } else {
        Write-Host "No key=value pairs found in .env to use as secrets." -ForegroundColor Yellow
    }
}

# List workflows and offer to enable/run
Write-Host "\nListing workflows for $repoFull..." -ForegroundColor Cyan
$wfs = gh workflow list --repo $repoFull --limit 50 --json name,fileName -q '.[] | {name: .name, file: .fileName}' 2>$null
if ($LASTEXITCODE -ne 0 -or -not $wfs) {
    Write-Host "No workflows found or unable to list workflows. Confirm that .github/workflows exists in the repo." -ForegroundColor Yellow
} else {
    Write-Host "Workflows found:" -ForegroundColor Cyan
    $wfsFormatted = gh workflow list --repo $repoFull
    Write-Host $wfsFormatted
    if (-not $NonInteractive) {
        $enable = Read-Host "Enable workflows and optionally run one now? (y/N)"
        if ($enable -eq 'y' -or $enable -eq 'Y') {
            # Enable all workflows (idempotent)
            foreach ($wf in (gh workflow list --repo $repoFull --limit 50 --json fileName -q '.[] | .fileName')) {
                Write-Host "Enabling $wf..."
                gh workflow enable $wf --repo $repoFull
            }
            $run = Read-Host "Run a workflow now? Enter file name (or leave blank to skip)"
            if ($run) {
                gh workflow run $run --repo $repoFull
                Write-Ok "Workflow dispatched: $run"
            }
        }
    }
}

Write-Ok "Setup complete. Review repository on GitHub: https://github.com/$repoFull"
