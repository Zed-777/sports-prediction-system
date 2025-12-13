<#
  Phase2 Install Helper (Windows PowerShell)

  - Attempts to install Phase 2 (heavy) dependencies using either the 'py' launcher with Python 3.13
    or using 'mamba' to create a conda environment with Python 3.13.
  - If neither is available, prints actionable instructions for the developer.

  Usage:
    powershell -ExecutionPolicy Bypass -File scripts\phase2_install_helper.ps1
#>
param(
    [switch]$Force
)

Write-Host "Phase2 Install Helper - Attempting to detect install options..."

function Try-Py313 {
    try {
        $pyOut = py -3.13 -V 2>&1
        if ($LASTEXITCODE -eq 0) { return $true }
        return $false
    } catch { return $false }
}

function Try-Mamba {
    try { Get-Command mamba -ErrorAction Stop | Out-Null; return $true } catch { return $false }
}

if (Try-Py313) {
    Write-Host "Python 3.13 detected via 'py' launcher - using it for Phase2 installation"
    py -3.13 -m venv .venv_phase2
    .\.venv_phase2\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    python -m pip install -r requirements_phase2.txt
    Write-Host "Phase2 packages attempted to be installed in .venv_phase2. Activate with: .\\.venv_phase2\\Scripts\\Activate.ps1"
    exit 0
}

if (Try-Mamba) {
    Write-Host "mamba detected. Creating conda environment 'sps_py313' with Python 3.13"
    mamba create -n sps_py313 python=3.13 -y
    Write-Host "Activating conda env sps_py313 and installing pip requirements..."
    mamba run -n sps_py313 --no-capture-output pip install -r requirements_phase2.txt
    Write-Host "Phase2 packages installed in conda env 'sps_py313'. Activate using 'mamba activate sps_py313' or 'conda activate sps_py313'"
    exit 0
}

Write-Host "No suitable installer found (py -3.13 or mamba). To install Phase2 dependencies, either:" -ForegroundColor Yellow
Write-Host "  1) Install Python 3.13 and run: py -3.13 -m venv .venv_phase2; .\\.venv_phase2\\Scripts\\Activate.ps1; python -m pip install -r requirements_phase2.txt" -ForegroundColor Cyan
Write-Host "  2) Install Miniconda & mamba, then run: mamba create -n sps_py313 python=3.13 -y; mamba run -n sps_py313 pip install -r requirements_phase2.txt" -ForegroundColor Cyan
Write-Host "  3) Use Docker with an image that supports TensorFlow for Windows (if available)" -ForegroundColor Cyan

Write-Host "If you need help, ask the repo maintainer or install an appropriate Python version for Windows to proceed." -ForegroundColor Red
exit 0
