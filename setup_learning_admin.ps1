# Run setup script with Administrator privileges
# This script handles UAC elevation automatically

param(
    [switch]$Force
)

# Get current script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$setupScript = Join-Path $scriptDir "scripts\setup_automated_learning.py"

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[INFO] AdminPlease run this script as Administrator" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Option 1: Right-click this script and select 'Run as Administrator'" -ForegroundColor Cyan
    Write-Host "Option 2: Run in PowerShell as Admin:" -ForegroundColor Cyan
    Write-Host "    powershell -ExecutionPolicy Bypass -File setup_learning_admin.ps1" -ForegroundColor Cyan
    exit 1
}

Write-Host "[INFO] Running with Administrator privileges" -ForegroundColor Green
Write-Host ""

# Run the Python setup script
python $setupScript

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[SUCCESS] Setup completed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Verify task was created:" -ForegroundColor Cyan
    Write-Host '   schtasks /query /tn "SportsPrediction\SportsPredictionSystem-DailyLearning" /v' -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. View learning logs:" -ForegroundColor Cyan
    Write-Host "   Get-Content data/logs/automated/learning_loop_*.log -Tail 50" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Manual test (run immediately):" -ForegroundColor Cyan
    Write-Host '   schtasks /run /tn "SportsPrediction\SportsPredictionSystem-DailyLearning"' -ForegroundColor Gray
} else {
    Write-Host "[ERROR] Setup failed with exit code $LASTEXITCODE" -ForegroundColor Red
}
