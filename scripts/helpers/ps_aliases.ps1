# PowerShell convenience aliases for local manual workflow
# Dot-source this file in your PowerShell session to add quick aliases:
# . .\scripts\helpers\ps_aliases.ps1

Set-Alias sps-daily { powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\..\..\scripts\automation\run_daily_job.ps1" }
Set-Alias sps-weekly { powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\..\..\scripts\automation\run_weekly_optimization.ps1" }
Set-Alias sps-collect { powershell -NoProfile -ExecutionPolicy Bypass -Command "python scripts/collect_historical_results.py --all-leagues" }
Set-Alias sps-optimize { powershell -NoProfile -ExecutionPolicy Bypass -Command "python scripts/optimize_accuracy.py --mode full --league la-liga" }

Write-Host "Aliases defined: sps-daily, sps-weekly, sps-collect, sps-optimize" -ForegroundColor Green
