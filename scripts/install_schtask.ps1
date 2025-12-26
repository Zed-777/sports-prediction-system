param(
    [string]$TaskName = "SportsPredictionSystem - Daily Fetch",
    [string]$TaskTime = "03:00",
    [string]$ScriptPath = "$PSScriptRoot\\run_daily_fetch.ps1",
    [switch]$Replace,
    [switch]$UseHighestPrivilege
)

Set-StrictMode -Version Latest

Write-Host "Installing scheduled task '$TaskName' to run script: $ScriptPath at $TaskTime"

# Resolve full path
$fullScript = Resolve-Path -Path $ScriptPath -ErrorAction SilentlyContinue
if (-not $fullScript) {
    Write-Error "Script path not found: $ScriptPath"
    exit 1
}
$fullScript = $fullScript.Path

# Build schtasks command
# If Replace, delete existing
if ($Replace) {
    Write-Host "Removing existing task if present..."
    schtasks /Delete /TN "$TaskName" /F | Out-Null
}

$runArgs = "-ExecutionPolicy Bypass -File '$fullScript'"
$action = "powershell.exe $runArgs"

$highest = if ($UseHighestPrivilege) {" /RL HIGHEST"} else {" /RL LIMITED"}

# Create task - wrap /TR in double quotes and single-quote the inner script path
$createCmd = "schtasks /Create /SC DAILY /TN `"$TaskName`" /TR `"$action`" /ST $TaskTime$highest /F"
Write-Host "Running: $createCmd"
try {
    iex $createCmd
    Write-Host "Task created. To test it now run: schtasks /Run /TN `"$TaskName`""
    exit 0
} catch {
    Write-Error "Failed to create scheduled task: $_"
    exit 2
}