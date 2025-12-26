<#
Register Scheduled Tasks (Windows)
- Creates two scheduled tasks:
  * SPS_DailyCollection (runs daily at 03:00)
  * SPS_WeeklyOptimization (runs weekly Mon at 04:00)
- Use -Remove to remove tasks instead
#>
param(
    [switch]$Remove,
    [string]$DailyTime = '03:00',
    [string]$WeeklyTime = '04:00'
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir '..\..')
$dailyScript = Join-Path $projectRoot 'scripts\automation\run_daily_job.ps1'
$weeklyScript = Join-Path $projectRoot 'scripts\automation\run_weekly_optimization.ps1'

if ($Remove) {
    Write-Host "Removing scheduled tasks (if present)"
    schtasks /Delete /TN "SPS_DailyCollection" /F > $null 2>&1
    schtasks /Delete /TN "SPS_WeeklyOptimization" /F > $null 2>&1
    Write-Host "Tasks removed (if they existed)"
    exit 0
}

Write-Host "Registering scheduled tasks..."
# Daily
schtasks /Create /SC DAILY /TN "SPS_DailyCollection" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File `"$dailyScript`"" /ST $DailyTime /F
if ($LASTEXITCODE -eq 0) { Write-Host "Registered SPS_DailyCollection at $DailyTime" -ForegroundColor Green } else { Write-Host "Failed to register SPS_DailyCollection" -ForegroundColor Yellow }

# Weekly (Monday)
schtasks /Create /SC WEEKLY /D MON /TN "SPS_WeeklyOptimization" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File `"$weeklyScript`"" /ST $WeeklyTime /F
if ($LASTEXITCODE -eq 0) { Write-Host "Registered SPS_WeeklyOptimization on MON at $WeeklyTime" -ForegroundColor Green } else { Write-Host "Failed to register SPS_WeeklyOptimization" -ForegroundColor Yellow }

Write-Host "Registration complete. Use -Remove to delete these tasks." -ForegroundColor Cyan
