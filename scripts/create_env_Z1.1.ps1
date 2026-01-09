<#
Create and bootstrap the local virtual environment `.venv-Z1.1` for Windows PowerShell.

Usage:
  .\scripts\create_env_Z1.1.ps1 [-InstallPhase2]

This script will:
- Detect whether Python is available on PATH.
- Create `.venv-Z1.1` if missing.
- Activate the venv in the current PowerShell session.
- Upgrade pip and install `requirements.txt` and `requirements-dev.txt`.
- Optionally install Phase 2 extras when `-InstallPhase2` is passed.
#>

param(
    [switch]$InstallPhase2
)

Write-Host "Creating environment .venv-Z1.1 (PowerShell)" -ForegroundColor Cyan

# ensure python exists
try {
    $pyCmd = Get-Command python -ErrorAction Stop
} catch {
    Write-Host "Python executable not found in PATH. Please install Python first." -ForegroundColor Red
    exit 1
}

Write-Host "Python detected: $($pyCmd.Path)" -ForegroundColor Green

# create venv if missing
if (-not (Test-Path ".\.venv-Z1.1")) {
    Write-Host "Creating virtual environment .venv-Z1.1..." -ForegroundColor Cyan
    python -m venv .venv-Z1.1
} else {
    Write-Host "Virtual environment already exists: .venv-Z1.1" -ForegroundColor Yellow
}

# ensure activation script exists
if (-not (Test-Path ".\.venv-Z1.1\Scripts\Activate.ps1")) {
    Write-Host "Activation script not found after creating venv; aborting." -ForegroundColor Red
    exit 1
}

Write-Host "Activating .venv-Z1.1 in current shell..." -ForegroundColor Cyan
. .\.venv-Z1.1\Scripts\Activate.ps1

Write-Host "Upgrading pip and installing requirements..." -ForegroundColor Cyan
python -m pip install --upgrade pip
if (Test-Path "requirements.txt") { python -m pip install -r requirements.txt }
if (Test-Path "requirements-dev.txt") { python -m pip install -r requirements-dev.txt }

if ($InstallPhase2) {
    if (Test-Path "requirements_phase2.txt") { python -m pip install -r requirements_phase2.txt }
    if (Test-Path "requirements_phase2_fixed.txt") { python -m pip install -r requirements_phase2_fixed.txt }
}

Write-Host ""; Write-Host "Done. Verify with: python -c 'import sys; print(sys.executable)'" -ForegroundColor Green
