<#
PowerShell helper to deploy SportsPredictionSystem on Windows
- Creates/activates a venv
<#
PowerShell helper to deploy SportsPredictionSystem on Windows
- Creates a venv if missing
- Installs requirements
- Copies .env.example to .env if missing
- Runs a smoke test
- Optionally registers a scheduled task to run the report generator daily (calls venv python directly)
#>

param(
    [string]$InstallPath = "$PWD",
    [string]$VenvPath = "$PWD\\.venv",
    [int]$DailyHour = 2
)

Write-Host "Deploying SportsPredictionSystem to $InstallPath"

# Create venv
if (-Not (Test-Path $VenvPath)) {
    Write-Host "Creating virtual environment at $VenvPath"
    python -m venv $VenvPath
} else {
    Write-Host "Virtual environment already exists at $VenvPath"
}

# Attempt to activate venv for the current session if possible
$activatePath = Join-Path $VenvPath 'Scripts\\Activate.ps1'
if (Test-Path $activatePath) {
    try {
        & $activatePath
    } catch {
        Write-Host "Warning: could not source Activate.ps1 in this session. Subsequent commands will call venv python directly."
    }
}

# Install requirements
$req = Join-Path $InstallPath 'requirements.txt'
if (Test-Path $req) {
    Write-Host "Installing requirements.txt"
    & (Join-Path $VenvPath 'Scripts\\python.exe') -m pip install --upgrade pip
    & (Join-Path $VenvPath 'Scripts\\python.exe') -m pip install -r $req
} else {
    Write-Host "requirements.txt not found in $InstallPath"
}

# Copy .env.example to .env if not present
$envExample = Join-Path $InstallPath '.env.example'
$envFile = Join-Path $InstallPath '.env'
if (Test-Path $envExample -and -Not (Test-Path $envFile)) {
    Copy-Item -Path $envExample -Destination $envFile
    Write-Host "Copied .env.example to .env - please edit .env to add API keys"
} elseif (-Not (Test-Path $envExample)) {
    Write-Host ".env.example not found. Please create .env with required API keys."
}

# Run basic smoke tests using the venv's python
Write-Host "Running smoke tests..."
$pyExe = Join-Path $VenvPath 'Scripts\\python.exe'
if (Test-Path $pyExe) {
    & $pyExe -m pytest -q tests/test_integration_flashscore.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Some tests failed - inspect output"
    }
} else {
    Write-Host "Python executable in venv not found; running system python instead"
    python -m pytest -q tests/test_integration_flashscore.py
    if ($LASTEXITCODE -ne 0) { Write-Host "Some tests failed - inspect output" }
}

# Register a scheduled task to run daily (optional) — runs venv python directly to avoid quoting issues
$taskName = "SportsPredictionSystemRunner"
$pythonExe = Join-Path $VenvPath 'Scripts\\python.exe'
$taskArgument = "'$InstallPath\\\\generate_fast_reports.py' generate 5 matches for la-liga"
try {
    if (Test-Path $pythonExe) {
        $action = New-ScheduledTaskAction -Execute $pythonExe -Argument $taskArgument
        $trigger = New-ScheduledTaskTrigger -Daily -At (Get-Date).Date.AddHours($DailyHour)
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Force
        Write-Host "Scheduled task '$taskName' registered to run daily at $DailyHour:00"
    } else {
        Write-Host "Venv python not found; skipping scheduled task creation."
    }
} catch {
    Write-Host "Failed to register scheduled task: $_"
}

Write-Host "Deployment helper finished. Please edit .env with your API keys and verify scheduled task logs."