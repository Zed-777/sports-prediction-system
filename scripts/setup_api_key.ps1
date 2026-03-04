<#
.SYNOPSIS
    Interactive setup helper for Sports Prediction System API keys.

.DESCRIPTION
    Guides you through obtaining and configuring the required API keys.
    Updates .env and optionally sets GitHub repository secrets.

.EXAMPLE
    .\scripts\setup_api_key.ps1
#>

$ErrorActionPreference = "Stop"
$EnvFile = Join-Path $PSScriptRoot ".." ".env"
$EnvFile = [System.IO.Path]::GetFullPath($EnvFile)

function Write-Header($text) {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

function Read-CurrentKey($keyName) {
    if (Test-Path $EnvFile) {
        $line = Get-Content $EnvFile | Where-Object { $_ -match "^$keyName=" } | Select-Object -First 1
        if ($line) {
            $val = $line.Split("=", 2)[1].Trim().Trim('"').Trim("'")
            if ($val -and $val -notmatch "^YOUR_|^your_") { return $val }
        }
    }
    return $null
}

function Set-EnvKey($keyName, $value) {
    $content = ""
    if (Test-Path $EnvFile) { $content = Get-Content $EnvFile -Raw }

    if ($content -match "(?m)^$keyName=.*") {
        $content = $content -replace "(?m)^$keyName=.*", "$keyName=$value"
    } else {
        $content = $content.TrimEnd() + "`n$keyName=$value`n"
    }
    Set-Content -Path $EnvFile -Value $content -Encoding UTF8
    Write-Host "  [OK] $keyName written to .env" -ForegroundColor Green
}

# ──────────────────────────────────────────────────────────────────────────────
Write-Header "Sports Prediction System — API Key Setup"

Write-Host ""
Write-Host "This script will help you configure the following keys:" -ForegroundColor White
Write-Host "  1. FOOTBALL_DATA_API_KEY   (required — FREE)"
Write-Host "  2. API_FOOTBALL_KEY        (optional — paid, for injury data)"
Write-Host ""
Write-Host "You will also be asked if you want to push them to GitHub Secrets"
Write-Host "so the automated workflows can use them."
Write-Host ""
Read-Host "Press Enter to continue"

# ──────────────────────────────────────────────────────────────────────────────
Write-Header "Step 1: football-data.org API Key (FREE)"

$existing = Read-CurrentKey "FOOTBALL_DATA_API_KEY"
if ($existing) {
    Write-Host ""
    Write-Host "  Current key: $($existing.Substring(0, [Math]::Min(6, $existing.Length)))..." -ForegroundColor Yellow
    $confirm = Read-Host "  Key already set. Update it? (y/N)"
    if ($confirm.ToLower() -ne "y") {
        Write-Host "  Keeping existing key." -ForegroundColor Gray
        $fdKey = $existing
    } else {
        $existing = $null
    }
}

if (-not $existing) {
    Write-Host ""
    Write-Host "  Register for a FREE API key at:" -ForegroundColor White
    Write-Host "    https://www.football-data.org/client/register" -ForegroundColor Blue
    Write-Host ""
    Write-Host "  The free Tier 1 key gives you:"
    Write-Host "    - Premier League, La Liga, Bundesliga, Serie A, Ligue 1"
    Write-Host "    - Finished match results (current and recent seasons)"
    Write-Host "    - 10 API calls per minute"
    Write-Host ""
    $fdKey = Read-Host "  Paste your FOOTBALL_DATA_API_KEY"
    if ($fdKey) {
        Set-EnvKey "FOOTBALL_DATA_API_KEY" $fdKey
    } else {
        Write-Host "  Skipped." -ForegroundColor Yellow
    }
}

# ──────────────────────────────────────────────────────────────────────────────
Write-Header "Step 2: API-Football Key (Optional)"

Write-Host ""
Write-Host "  API-Football (RapidAPI) provides injury and suspension data."
Write-Host "  It improves predictions but is NOT required for core functionality."
Write-Host "  Sign up at: https://rapidapi.com/api-sports/api/api-football"
Write-Host ""
$setAf = Read-Host "  Do you have an API-Football key to configure? (y/N)"
if ($setAf.ToLower() -eq "y") {
    $afKey = Read-Host "  Paste your API_FOOTBALL_KEY"
    if ($afKey) { Set-EnvKey "API_FOOTBALL_KEY" $afKey }
} else {
    Write-Host "  Skipped." -ForegroundColor Gray
}

# ──────────────────────────────────────────────────────────────────────────────
Write-Header "Step 3: GitHub Repository Secrets (Optional)"

Write-Host ""
Write-Host "  Setting GitHub secrets allows the automated workflows to run:"
Write-Host "    - fetch-results.yml   (daily result collection)"
Write-Host "    - auto-optimize.yml   (weekly model tuning)"
Write-Host ""
$ghAvail = Get-Command gh -ErrorAction SilentlyContinue
if (-not $ghAvail) {
    Write-Host "  GitHub CLI (gh) not found. Skipping GitHub secrets." -ForegroundColor Yellow
    Write-Host "  Install from: https://cli.github.com/"
} else {
    $setGh = Read-Host "  Push keys to GitHub Secrets? (y/N)"
    if ($setGh.ToLower() -eq "y") {
        $repo = "Zed-777/sports-prediction-system"
        if ($fdKey) {
            gh secret set FOOTBALL_DATA_API_KEY --body $fdKey --repo $repo
            Write-Host "  [OK] FOOTBALL_DATA_API_KEY set in GitHub" -ForegroundColor Green
        }
        Write-Host ""
        Write-Host "  You can also set the optional SMTP mail keys now:"
        $setSMTP = Read-Host "  Configure SMTP email notifications? (y/N)"
        if ($setSMTP.ToLower() -eq "y") {
            $smtpHost = Read-Host "  SMTP_HOST (e.g. smtp.gmail.com)"
            $smtpPort = Read-Host "  SMTP_PORT (e.g. 587)"
            $smtpUser = Read-Host "  SMTP_USER"
            $smtpPass = Read-Host "  SMTP_PASS" -AsSecureString
            $emailTo  = Read-Host "  EMAIL_TO"
            $smtpPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                [Runtime.InteropServices.Marshal]::SecureStringToBSTR($smtpPass))
            foreach ($pair in @(
                @("SMTP_HOST", $smtpHost), @("SMTP_PORT", $smtpPort),
                @("SMTP_USER", $smtpUser), @("SMTP_PASS", $smtpPassPlain),
                @("EMAIL_TO",  $emailTo)
            )) {
                if ($pair[1]) { gh secret set $pair[0] --body $pair[1] --repo $repo }
            }
            Write-Host "  [OK] SMTP secrets set in GitHub" -ForegroundColor Green
        }
    }
}

# ──────────────────────────────────────────────────────────────────────────────
Write-Header "Step 4: Fetch Historical Data"

Write-Host ""
if ($fdKey) {
    $runFetch = Read-Host "  Run bulk historical data fetch now? (Y/n)"
    if ($runFetch.ToLower() -ne "n") {
        Write-Host ""
        Write-Host "  Fetching 2 seasons x 5 leagues (~2,000 matches)..." -ForegroundColor Cyan
        Write-Host "  This takes approx 5-8 minutes (API rate limit respected)."
        Write-Host ""
        $env:FOOTBALL_DATA_API_KEY = $fdKey
        $env:SKIP_INJURIES = "1"
        & python scripts/fetch_historical_bulk.py --seasons 2024 2023 --no-predictor
        Write-Host ""
        Write-Host "  Historical data fetched! Run prediction validation:" -ForegroundColor Green
        Write-Host "    python scripts/run_profitability_analysis.py --n-synthetic 0"
    }
} else {
    Write-Host "  No API key configured — skipping data fetch." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Once you have a key, run:"
    Write-Host "    python scripts/fetch_historical_bulk.py"
}

Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "  Setup complete." -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host ""
