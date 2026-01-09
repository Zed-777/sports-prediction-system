<#
Build and run the project's docker-compose service for quick local testing.

Usage (PowerShell):
    .\scripts\devcontainer_build.ps1 [-BuildOnly]

Options:
    -BuildOnly  : Build the image(s) but don't start containers.

Notes:
- Requires Docker Desktop to be installed and running on Windows.
- This script is a convenience wrapper around `docker-compose`.
#>

param(
    [switch]$BuildOnly
)

Write-Host "[devcontainer] Building docker-compose images..."

# Build using docker-compose
docker-compose build --no-cache

if ($BuildOnly) {
    Write-Host "[devcontainer] Build complete. Skipping container start as requested."
    exit 0
}

Write-Host "[devcontainer] Starting containers (attached)..."
docker-compose up --remove-orphans
