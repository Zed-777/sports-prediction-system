# Prepare the STATS folder for USB transfer
# Usage: .\prepare_for_transfer.ps1 [-OutputZip "STATS_transfer.zip"]
Param(
    [string]$OutputZip = "STATS_transfer_$((Get-Date).ToString('yyyyMMdd_HHmmss')).zip"
)

$root = (Get-Location).Path
$staging = Join-Path $env:TEMP "STATS_transfer_staging"

if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Path $staging | Out-Null

$excludeDirs = @('.venv', '.git', 'data/cache/expanded_cache', 'reports', 'models/ml_enhanced', 'logs', 'node_modules')

Get-ChildItem -Path $root -Force | ForEach-Object {
    if ($excludeDirs -contains $_.Name) {
        Write-Host "Skipping: $_.Name"
    } else {
        $dest = Join-Path $staging $_.Name
        if ($_.PSIsContainer) {
            Copy-Item -Path $_.FullName -Destination $dest -Recurse -Force
        } else {
            Copy-Item -Path $_.FullName -Destination $dest -Force
        }
    }
}

if (Test-Path $OutputZip) { Remove-Item $OutputZip -Force }
Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $OutputZip -Force
Remove-Item $staging -Recurse -Force
Write-Host "Created: $OutputZip"
Write-Host "Copy this ZIP file to your USB drive and extract it on the target machine. See README or .github/copilot-instructions.md for next steps."