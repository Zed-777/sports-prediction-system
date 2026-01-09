param(
    [string]$TaskName = "SportsPredictionSystem - Daily Fetch",
    [switch]$Confirm = $true
)

Set-StrictMode -Version Latest
Write-Host "Removing scheduled task: $TaskName"
try {
    schtasks /Delete /TN "$TaskName" /F | Out-Null
    Write-Host "Task removed (or did not exist)."
    exit 0
} catch {
    Write-Error "Failed to remove task: $_"
    exit 2
}