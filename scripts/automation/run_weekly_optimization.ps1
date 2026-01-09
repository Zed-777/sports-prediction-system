<#
Run Weekly Optimization
- Runs full optimizer for configured leagues (default: la-liga)
- Writes logs to data/logs and ensures results are stored in data/optimization_results
#>
[CmdletBinding()]
param(
    [string[]]$Leagues = @('la-liga'),
    [switch]$DryRun
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir '..\..')
$logsDir = Join-Path $projectRoot 'data\logs'
if (-not (Test-Path $logsDir)) { New-Item -Path $logsDir -ItemType Directory | Out-Null }

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logFile = Join-Path $logsDir "weekly_opt_$timestamp.log"

function Log([string]$msg) {
    "$((Get-Date).ToString('o')) - $msg" | Tee-Object -FilePath $logFile -Append
}

Log "Starting weekly optimization"

# Activate venv if available (best-effort)
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

foreach ($league in $Leagues) {
    Log "Running optimizer for $league"
    if ($DryRun) {
        Log "Dry run: skipping actual optimization"; continue
    }
    try {
        & $pythonCmd (Join-Path $projectRoot 'scripts\optimize_accuracy.py') --mode full --league $league 2>&1 | Tee-Object -FilePath $logFile -Append
        Log "Optimizer completed for $league"
    } catch {
        Log "Optimizer failed for $league: $_"
    }
}

Log "Weekly optimization finished"
Exit 0
