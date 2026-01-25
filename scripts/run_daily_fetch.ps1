<#
Runs the daily fetch/backfill/regenerate pipeline locally.
Safe defaults: runs fetch-all, backfill-provider-ids, regenerate recent reports (5 runs, 60s delay).
Usage:
  # Basic daily run
  .\scripts\run_daily_fetch.ps1

  # Run with debug logging enabled
  .\scripts\run_daily_fetch.ps1 -Debug

  # Run only fetch
  .\scripts\run_daily_fetch.ps1 -FetchOnly

  # Set regenerate options
  .\scripts\run_daily_fetch.ps1 -RegenerateCount 3 -RegenerateDelay 30

Notes:
- Ensure your Python virtualenv is present (e.g., .venv, .venv-Z1.1, venv) and has dependencies installed.
- Put API keys in environment variables or a .env file at repo root (collector reads .env for keys).
#>

param(
    [switch]$Debug,
    [switch]$FetchOnly,
    [switch]$BackfillOnly,
    [switch]$RegenerateOnly,
    [int]$RegenerateCount = 5,
    [int]$RegenerateDelay = 60,
    [int]$PruneKeep = 0,
    [string]$LogDir = "$PSScriptRoot\..\logs\daily",
    [switch]$RunTests
)

Set-StrictMode -Version Latest
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$timestamp = Get-Date -Format yyyyMMdd_HHmmss
$logFile = Join-Path $LogDir "daily_fetch_$timestamp.log"

function Write-Log {
    param([string]$Message)
    $t = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$t] $Message"
    $line | Tee-Object -FilePath $logFile -Append | Out-Null
}

Write-Log "Starting daily fetch script (Debug=$Debug)"

# Ensure we run from the project root so relative script paths work when scheduled
try {
    $projectRoot = Resolve-Path -Path "$PSScriptRoot\.."
    Write-Log "Changing working directory to project root: $($projectRoot.Path)"
    Set-Location $projectRoot.Path
} catch {
    Write-Log "Failed to change directory to project root: $_"
}

# Find a virtualenv Activate script
$possibleVenvs = @('.venv','.venv-Z1.1','venv')
$activated = $false
foreach ($v in $possibleVenvs) {
    $act = Join-Path "$PSScriptRoot\.." "$v\Scripts\Activate.ps1"
    if (Test-Path $act) {
        Write-Log "Activating virtualenv: $act"
        try {
            & $act
            $activated = $true
            break
        } catch {
            Write-Log "Virtualenv activation failed: $_"
        }
    }
}
if (-not $activated) {
    Write-Log "No virtualenv activation script found; proceeding with system Python." 
}

# Helper to run a Python command and capture output
function Run-Python {
    param([string]$Command)
    Write-Log "Running: python $Command"
    try {
        # Use native invocation to capture output and exit code (split args to avoid passing a single filename)
        $parts = $Command -split ' '
        $output = & python @parts 2>&1
        $exit = $LASTEXITCODE
        if ($output) { $output -split "`n" | ForEach-Object { Write-Log "OUT: $_" } }
        return $exit
    } catch {
        Write-Log ("Failed to run python {0}: {1}" -f $Command, $_)
        return 1
    }
}

# Decide which steps to run
if (-not $BackfillOnly -and -not $RegenerateOnly) {
    if (-not $FetchOnly) {
        # Fetch all leagues
        $pyArgs = "scripts/collect_historical_results.py --fetch-all"
        if ($Debug) { $pyArgs += ' --debug' }
        $ec = Run-Python $pyArgs
        Write-Log "Fetch-all exit code: $ec"
    }

    if (-not $FetchOnly) {
        # Backfill provider ids
        $pyArgs = "scripts/collect_historical_results.py --backfill-provider-ids"
        if ($Debug) { $pyArgs += ' --debug' }
        $ec = Run-Python $pyArgs
        Write-Log "Backfill exit code: $ec"
    }
}

if (-not $FetchOnly -and -not $BackfillOnly) {
    # Regenerate reports (prune + regenerate)
    $pyArgs = "scripts/regenerate_reports.py --all --count $RegenerateCount --delay $RegenerateDelay --prune-keep $PruneKeep"
    if ($Debug) { $pyArgs += ' --debug' }
    $ec = Run-Python $pyArgs
    Write-Log "Regenerate exit code: $ec"
}

if ($RunTests) {
    Write-Log "Running unit tests..."
    $ec = Run-Python "-m pytest -q"
    Write-Log "Tests exit code: $ec"
}

Write-Log "Daily fetch script completed"
exit 0
