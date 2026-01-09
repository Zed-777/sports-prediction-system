## Workspace helper: auto-activate the `.venv-Z1.1` virtual environment for PowerShell terminals
# This script is invoked by the custom terminal profile in `.vscode/settings.json`.
$ErrorActionPreference = 'SilentlyContinue'

# Resolve workspace root (one level up from .vscode)
$workspaceRoot = Resolve-Path "$PSScriptRoot\.."

# Path to the venv activation script
$activate = Join-Path $workspaceRoot ".venv-Z1.1\Scripts\Activate.ps1"

if (Test-Path $activate) {
    Write-Host "Activating workspace venv: .venv-Z1.1"
    & $activate
} else {
    Write-Host "Workspace venv not found at: $activate"
}
