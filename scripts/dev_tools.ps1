<#
  Simple interactive developer tools for Windows PowerShell
  - Wraps common tasks like setup, test, status, reset flags, run generator

  Usage (PowerShell):
    powershell -ExecutionPolicy Bypass -File scripts\dev_tools.ps1
#>

function Show-Menu {
    Clear-Host
    Write-Host "Developer Tools - STATS"
    Write-Host "1) Setup environment (dev_setup)"
    Write-Host "2) Run smoke tests"
    Write-Host "3) Run full test suite"
    Write-Host "4) Show status (disabled flags + metrics)"
    Write-Host "5) Reset disabled flags"
    Write-Host "6) Generate a report (no injuries + export metrics)"
    Write-Host "7) Exit"
}

function Run-Choice {
    param([int]$choice)
    # Ensure the venv is active for all choices
    $null = .\scripts\ensure_activation.ps1
    $venvPython = ".\\.venv\\Scripts\\python.exe"
    & $venvPython -V
    $venvPython = ".\\.venv\\Scripts\\python.exe"
    switch ($choice) {
        1 {
            Write-Host "Setting up environment..."
            powershell -ExecutionPolicy Bypass -File scripts\dev_setup.ps1 -RunTests
        }
        2 {
            Write-Host "Running smoke tests..."
            & $venvPython -m pytest -q tests/test_state_sync_file.py tests/test_reset_status_scripts.py
        }
        3 {
            Write-Host "Running full test suite (can be slow)..."
            & $venvPython -m pytest -q
        }
        4 {
            Write-Host "Status (disabled flags + metrics):"
            & $venvPython scripts/status.py
        }
        5 {
            Write-Host "Resetting disabled flags (clear all)..."
            & $venvPython scripts/reset_disabled_flags.py --clear-all
        }
        6 {
            Write-Host "Generate report (1 match for la-liga) with --no-injuries and --export-metrics..."
            & $venvPython generate_fast_reports.py generate 1 matches for la-liga --no-injuries --export-metrics
        }
        7 { exit }
    }
}

while ($true) {
    Show-Menu
    $opt = Read-Host "Choose an option (1-7)"
    try {
        Run-Choice -choice ([int]$opt)
    } catch {
        Write-Host "Invalid choice, try again"
    }
    Read-Host "Press Enter to continue..."
}
