<#
  Helper to run tests using the .venv Python to avoid dependency mismatch and re-installation.
  Usage:
    .\scripts\run_tests.ps1  # runs all tests
    .\scripts\run_tests.ps1 -Subset 'tests/test_state_sync_file.py,tests/test_reset_status_scripts.py'
#>
param(
    [string]$Subset,
    [switch]$UseDummyKeys,
    [switch]$SkipNetwork
)

# Dot-source the activation script to ensure env changes persist to this session
. .\scripts\ensure_activation.ps1

$venvPython = ".\\.venv\\Scripts\\python.exe"
if ($UseDummyKeys) {
    if (-not $env:ODDS_API_KEY) { $env:ODDS_API_KEY = 'DUMMY-ODDS-KEY' }
    Write-Host "Using dummy key for ODDS_API_KEY during tests"
}

# Optionally skip network tests by unsetting real API keys
if ($SkipNetwork) {
    Write-Host "Skipping network-dependent tests by unsetting API keys from environment"
    # Use [Environment]::SetEnvironmentVariable to ensure changes are inherited by subprocess
    [Environment]::SetEnvironmentVariable('API_FOOTBALL_KEY', $null, [EnvironmentVariableTarget]::Process)
    [Environment]::SetEnvironmentVariable('FOOTBALL_DATA_API_KEY', $null, [EnvironmentVariableTarget]::Process)
    Write-Host "  - Cleared API_FOOTBALL_KEY and FOOTBALL_DATA_API_KEY for current process"
    # Keep ODDS_API_KEY populated with a dummy to satisfy connector presence checks (but avoid real API calls)
    if (-not $env:ODDS_API_KEY) { $env:ODDS_API_KEY = 'DUMMY-ODDS-KEY' }
}

if ($PSBoundParameters.ContainsKey('Subset') -and $Subset) {
    $tests = $Subset -split ',' | ForEach-Object { $_.Trim() }
    & $venvPython -m pytest -q $tests
} else {
    & $venvPython -m pytest -q
}