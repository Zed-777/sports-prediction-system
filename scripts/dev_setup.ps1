<#
  Developer setup script (Windows PowerShell) - sets up venv, installs runtime & dev dependencies,
  installs the package in editable mode (pip install -e .), and optionally runs a quick test.

  Usage:
  powershell -ExecutionPolicy Bypass -File scripts\dev_setup.ps1  # creates venv and installs deps
#>

param(
  [switch]$Force,
  [switch]$RunTests,
  [switch]$InstallPhase2
)

Write-Host "Preparing development environment for STATS (idempotent)..."
if (!(Test-Path -Path ".venv")) {
  Write-Host "Creating virtual environment: .venv"
  python -m venv .venv
}
Write-Host "Activating venv"
.\.venv\Scripts\Activate.ps1
# Print Python version and warn if it's Python 3.14+ which may not have pre-built wheels for some libs
$pythonVersion = (& python -V 2>&1)
Write-Host "Active Python version: $pythonVersion"
if ($pythonVersion -match "Python 3\.1[4-9]" ) {
  Write-Host "WARNING: Python 3.14+ may not have pre-built wheels for heavy compiled libs (numpy/pytensor/tensorflow). Consider using Python 3.13 for Phase2 installs." -ForegroundColor Yellow
}

$markerFile = ".venv\\.dev_installed"
if (-not (Test-Path -Path $markerFile) -or $Force) {
  Write-Host "Upgrading pip and installing required packages..."
  python -m pip install --upgrade pip
  Write-Host "Installing runtime requirements..."
  pip install -r requirements.txt
  Write-Host "Installing dev requirements..."
  pip install -r requirements-dev.txt
  if ($InstallPhase2 -and (Test-Path "requirements_phase2.txt")) {
    Write-Host "Installing Phase2 requirements (optional)..."
    pip install -r requirements_phase2.txt
  } else {
    Write-Host "Skipping Phase2 requirements. Use -InstallPhase2 to install them (may include heavy compiled libs)." -ForegroundColor Yellow
  }
  Write-Host "Installing project in editable mode (pip install -e .)"
  pip install -e .
  # Create or update marker file to avoid re-install next time
  "Installed: $(Get-Date -Format 's')" | Out-File -FilePath $markerFile -Encoding utf8
  Write-Host "Dev environment installed." -ForegroundColor Green
} else {
  Write-Host "Dev environment already installed; skipping package installs (use -Force to reinstall)" -ForegroundColor Yellow
}

if ($RunTests) {
  Write-Host "Running smoke tests..."
  .\scripts\run_tests.ps1 -Subset "tests/test_state_sync_file.py,tests/test_reset_status_scripts.py"
}

Write-Host "Setup complete. Activate venv with .\.venv\Scripts\Activate.ps1 and run your commands."
