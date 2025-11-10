<#
Simple helper to create a virtual environment named .venv-Z1.1

Usage (PowerShell):
  # After installing Python, from repo root:
  .\scripts\create_env_Z1.1.ps1

Options:
  -InstallPhase2  Install extra Phase 2 dependencies from requirements_phase2.txt
#>

param(
    [switch]$InstallPhase2
)

Write-Host "Creating environment .venv-Z1.1 (PowerShell)" -ForegroundColor Cyan

# Check for python
try {
    $py = Get-Command python -ErrorAction Stop
} catch {
    Write-Host "Python executable not found in PATH. Please install Python first (see README or instructions)." -ForegroundColor Red
    exit 1
}

Write-Host "Python detected: $($py.Source)" -ForegroundColor Green

# Create venv
python -m venv .venv-Z1.1

if (-not (Test-Path ".\.venv-Z1.1\Scripts\Activate.ps1")) {
    Write-Host "Failed to create virtual environment." -ForegroundColor Red
    exit 1
}

Write-Host "Activating .venv-Z1.1..." -ForegroundColor Cyan
. .\.venv-Z1.1\Scripts\Activate.ps1

Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

if (Test-Path "requirements.txt") {
    Write-Host "Installing project requirements from requirements.txt..." -ForegroundColor Cyan
    pip install -r requirements.txt
} else {
    Write-Host "requirements.txt not found in repo root; skipping dependency install." -ForegroundColor Yellow
}

if ($InstallPhase2) {
    if (Test-Path "requirements_phase2.txt") {
        Write-Host "Installing Phase 2 extra requirements..." -ForegroundColor Cyan
        pip install -r requirements_phase2.txt
    } else {
        Write-Host "requirements_phase2.txt not found; skipping." -ForegroundColor Yellow
    }
}

Write-Host "`nDone. Activate the environment later with:`n. .\.venv-Z1.1\Scripts\Activate.ps1" -ForegroundColor Green
