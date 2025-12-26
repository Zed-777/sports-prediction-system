# PowerShell helper: store GitHub PAT in local .env file securely (asks for confirmation)
param(
    [switch]$Force
)
$envFile = Join-Path $PSScriptRoot '..\.env'
$envFile = (Resolve-Path $envFile).Path
Write-Host "This will add your GITHUB_TOKEN to: $envFile" -ForegroundColor Yellow
if (-not $Force) {
    $ok = Read-Host "Proceed and save token to .env? (y/N)"
    if ($ok -ne 'y' -and $ok -ne 'Y') { Write-Host 'Aborted'; exit 1 }
}
# Read secret securely
$token = Read-Host "Paste your GitHub Personal Access Token (will not be echoed)" -AsSecureString
$plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($token))
# Write to .env (append or replace existing entry)
if (-not (Test-Path $envFile)) { New-Item -Path $envFile -ItemType File -Force | Out-Null }
$content = Get-Content $envFile -Raw -ErrorAction SilentlyContinue
if ($content -match '^GITHUB_TOKEN=.*$') {
    $new = ($content -replace '^GITHUB_TOKEN=.*$', "GITHUB_TOKEN=$plain")
    Set-Content -Path $envFile -Value $new -Encoding UTF8
} else {
    Add-Content -Path $envFile -Value "`nGITHUB_TOKEN=$plain" -Encoding UTF8
}
Write-Host "Saved token to $envFile (do not commit this file)." -ForegroundColor Green
