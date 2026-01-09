<#
Run Daily Job
- Collects predictions from reports into historical DB
- Optional: prune old reports (disabled by default)
- Writes timestamped logs to data/logs/
#>
[CmdletBinding()]
param(
    [switch]$PruneReports
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir '..\..')
$logsDir = Join-Path $projectRoot 'data\logs'
if (-not (Test-Path $logsDir)) { New-Item -Path $logsDir -ItemType Directory | Out-Null }

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logFile = Join-Path $logsDir "daily_job_$timestamp.log"

function Log([string]$msg) {
    "$((Get-Date).ToString('o')) - $msg" | Tee-Object -FilePath $logFile -Append
}

Log "Starting daily job"

# Activate recommended virtual environments if present
$venvCandidates = @('.venv','\.venv_phase2','.venv-Z1.1')
$pythonCmd = 'python'
foreach ($v in $venvCandidates) {
    $act = Join-Path $projectRoot "$v\Scripts\Activate.ps1"
    if (Test-Path $act) {
        Log "Activating virtualenv: $v"
        try {
            & powershell -NoProfile -ExecutionPolicy Bypass -Command ". '$act' ; python --version" | Tee-Object -FilePath $logFile -Append
            $pythonCmd = 'python'
            break
        } catch {
            Log ('Failed to activate ' + $v + ': ' + $_)
        }
    }
}

# Run collector
Log "Running historical collector (all leagues)"
try {
    & $pythonCmd (Join-Path $projectRoot 'scripts\collect_historical_results.py') --all-leagues 2>&1 | Tee-Object -FilePath $logFile -Append
    Log "Collector completed"
} catch {
    Log "Collector failed: $_"
}

if ($PruneReports) {
    Log "Pruning reports (requested)"
    try {
        & $pythonCmd (Join-Path $projectRoot 'generate_fast_reports.py') prune 2>&1 | Tee-Object -FilePath $logFile -Append
        Log "Prune completed"
    } catch {
        Log "Prune failed: $_"
    }
}

Log "Daily job finished"
Exit 0
