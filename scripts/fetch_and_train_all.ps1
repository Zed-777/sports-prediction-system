# PowerShell script to fetch historical data via APIs, collect and train models
# Ensure you set these environment variables before running:
# $env:FOOTBALL_DATA_API_KEY, $env:API_FOOTBALL_KEY, $env:API_FOOTBALL_LEAGUES, $env:COLLECT_SEASONS

if (-not $env:COLLECT_SEASONS) { $env:COLLECT_SEASONS = '2018,2019,2020,2021,2022,2023,2024' }

Write-Host "Seasons to collect: $env:COLLECT_SEASONS"

if ($env:FOOTBALL_DATA_API_KEY) {
    Write-Host 'Fetching from Football-Data.org (PD) ...'
    python scripts/fetch_historical_api.py --competition PD --seasons $($env:COLLECT_SEASONS -split ',') --fd --outfile fd_pd_all_seasons.csv
} else { Write-Host 'FOOTBALL_DATA_API_KEY not set — skipping Football-Data.org fetch' }

if ($env:API_FOOTBALL_KEY) {
    $leagues = $env:API_FOOTBALL_LEAGUES
    if (-not $leagues) { $leagues = '140' }
    foreach ($league in $leagues -split ',') {
        Write-Host "Fetching from API-Football for league: $league ..."
        python scripts/fetch_historical_api.py --competition $league --seasons $($env:COLLECT_SEASONS -split ',') --af --outfile api_football_${league}_all_seasons.csv
    }
} else { Write-Host 'API_FOOTBALL_KEY not set — skipping API-Football fetch' }

# Now collect CSVs (this will parse and process whatever CSVs we have in data/backup_csv/)
python scripts/collect_historical_data.py

# Train from processed dataset
python scripts/train_models.py

Write-Host 'Fetch and training pipeline complete.'
