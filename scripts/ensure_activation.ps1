<#
  Ensures the .venv exists and then activates it for the current session.
  If .venv doesn't exist, it creates a venv.
  This script is idempotent and safe to call from other scripts.

  Usage: .\scripts\ensure_activation.ps1  # dot-source or run
#>
param(
    [switch]$CreateIfMissing = $true
)

$venvPath = ".venv"
if (!(Test-Path -Path $venvPath)) {
    if ($CreateIfMissing) {
        Write-Host "Virtual environment not found; creating .venv..."
        python -m venv $venvPath
    } else {
        Write-Error "Virtual environment not found: $venvPath"
        exit 1
    }
}

Write-Host "Activating virtual environment: .venv"
.\.venv\Scripts\Activate.ps1
if ($?) {
    Write-Host "Virtual environment activated." -ForegroundColor Green
    $venvPython = ".\\.venv\\Scripts\\python.exe"
    & $venvPython -V
}