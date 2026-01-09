#!/usr/bin/env pwsh
<#
Orchestrator: fetch -> ingest -> train
Usage (PowerShell):
  .\scripts\auto_update_and_train.ps1 -Competition PD -Start 2018 -End 2024

#>

param(
    [string]$Competition = 'PD',
    [int]$Start = 2018,
    [int]$End = 2024
)

Write-Host "Auto update start: fetch -> ingest -> train" -ForegroundColor Cyan

if (Get-Command python -ErrorAction SilentlyContinue) {
    $python = 'python'
} else {
    $python = "$PSScriptRoot\..\.venv-Z1.1\Scripts\python.exe"
}

if (-not (Test-Path $python)) {
    Write-Host "Python executable not found: $python" -ForegroundColor Red
    exit 1
}

if ($env:FOOTBALL_DATA_API_KEY) {
    Write-Host "Fetching historical data for competition $Competition seasons $Start..$End" -ForegroundColor Green
    & $python "$PSScriptRoot\fetch_historical_api.py" --competition $Competition --start $Start --end $End
} else {
    Write-Host "No FOOTBALL_DATA_API_KEY set; skipping API fetch" -ForegroundColor Yellow
}

Write-Host "Ingesting CSVs and API results (if any)..." -ForegroundColor Green
& $python "$PSScriptRoot\collect_historical_data.py"

Write-Host "Training models from processed dataset..." -ForegroundColor Green
& $python "$PSScriptRoot\train_models.py" --force

Write-Host "Auto update complete." -ForegroundColor Cyan
