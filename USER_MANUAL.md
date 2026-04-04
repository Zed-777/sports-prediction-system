# User Manual — Sports Prediction System v4.1.0

**Welcome!** This manual guides you through installing, using, and interpreting predictions from the Sports Prediction System.

---

## Table of Contents

1. [Quick Start (5 minutes)](#quick-start-5-minutes)
2. [Installation & Setup](#installation--setup)
3. [Generating Predictions](#generating-predictions)
4. [Understanding Prediction Output](#understanding-prediction-output)
5. [Workflows & Use Cases](#workflows--use-cases)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Configuration](#advanced-configuration)

---

## Quick Start (5 minutes)

### Minimal Example: Generate 1 Prediction

```powershell
# 1. Navigate to project directory
cd C:\Dev\STATS

# 2. Activate Python environment
.\venv\Scripts\Activate.ps1

# 3. Generate a prediction for 1 upcoming Premier League match
python generate_fast_reports.py generate 1 matches for premier-league
```

**Output:** A prediction card (PNG) and summary (markdown) saved to:

```text
reports/leagues/premier-league/matches/<match>_<date>/
```

Open `prediction_card.png` to see your first prediction! 📊

---

## Installation & Setup

### Prerequisites

- **Python:** 3.8 or higher
- **Windows/Linux/Mac:** Tested on Windows; others should work
- **Disk space:** ~2 GB (for data cache and models)
- **Internet:** Required for API calls (Football-Data.org, API-Football, Open-Meteo)

### Step 1: Clone or Download the Repository

```bash
# If cloning from GitHub:
git clone https://github.com/Zed-777/sports-prediction-system.git
cd sports-prediction-system

# Or download and extract the ZIP file, then:
cd sports-prediction-system
```

### Step 2: Create Virtual Environment

**On Windows (PowerShell):**

```powershell
python -m venv .venv
.\venv\Scripts\Activate.ps1
```

**On Mac/Linux (Bash):**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

*Expected output:* ~50+ packages installed in 2–3 minutes.

### Step 4: Configure API Keys

Create a `.env` file in the project root (copy from `.env.example`):

```powershell
# Windows PowerShell:
Copy-Item .env.example .env

# Mac/Linux:
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# Football-Data.org (Free tier: 10 requests/minute)
FOOTBALL_DATA_API_KEY=your_key_here

# API-Football (RapidAPI) — needed for injury data
API_FOOTBALL_RAPIDAPI_KEY=your_key_here

# Open-Meteo — FREE, no key needed
# (Weather data is automatic)
```

**How to get API keys:**
- **Football-Data.org:** Sign up at [https://www.football-data.org/](https://www.football-data.org/) (free tier available)
- **API-Football:** Sign up at [https://rapidapi.com/api-sports/api/api-football](https://rapidapi.com/api-sports/api/api-football) (free tier: 100 requests/day)

⚠️ **No key?** The system will work with fallbacks (some features may be limited).

### Step 5: Verify Installation

```bash
python verify_system.py
```

Expected output:

```text
=== SYSTEM HEALTH CHECK ===

✓ All Python imports: OK
✓ Configuration: Loaded
✓ Data directories: Ready
✓ Models loaded: 3/3
```

✅ **You're ready!**

---

## Generating Predictions

### Command Syntax

```bash
python generate_fast_reports.py generate <N> matches for <league>
```

**Parameters:**

| Parameter | Values | Example |
| --- | --- | --- |
| `<N>` | Number of matches | `1`, `5`, `10` |
| `<league>` | League code | `premier-league`, `la-liga`, `serie-a`, `bundesliga`, `ligue-1` |

### Examples

**Generate 5 Premier League predictions:**

```bash
python generate_fast_reports.py generate 5 matches for premier-league
```

**Generate 1 La Liga prediction:**

```bash
python generate_fast_reports.py generate 1 matches for la-liga
```

**Generate 10 Bundesliga predictions:**

```bash
python generate_fast_reports.py generate 10 matches for bundesliga
```

### Processing Time

- **Per match:** 80–120 seconds (includes API calls, weather, injuries, form analysis)
- **5 matches:** ~7–10 minutes
- **Parallel processing:** Not yet supported; matches processed sequentially

### Output Locations

Reports are saved by league and match:

```text
reports/
├── leagues/
│   ├── premier-league/
│   │   └── matches/
│   │       └── west-ham-united-fc_vs_wolverhampton-wanderers-fc_2026-04-10/
│   │           ├── prediction_card.png      ← Visual prediction
│   │           └── summary.md               ← Detailed analysis
│   ├── la-liga/
│   ├── serie-a/
│   └── ...
```

---

## Understanding Prediction Output

### The Prediction Card (PNG)

Each report includes a visual card with:

```text
╔════════════════════════════════════════════════╗
║    West Ham United FC vs Wolverhampton         ║
║    Premier League • 2026-04-10 • 19:00         ║
╚════════════════════════════════════════════════╝

📊 PREDICTED FINAL SCORE
   West Ham United FC 1-0 Wolverhampton Wanderers FC
   Expected Goals: 1.4 - 0.8

🎯 CONFIDENCE METRICS
   72% — Prediction Confidence
   54% — Data Quality

📈 MATCH OUTCOME PROBABILITY
   ┌─────────────────────────────────┐
   │ West Ham Win:        47%  ✅     │
   │ Draw:                28%         │
   │ Wolverhampton Win:   25%         │
   └─────────────────────────────────┘

🎲 ADVANCED METRICS
   • Both Teams to Score (BTTS): 44%
   • Over 2.5 Goals: 40%
   • Form Assessment: West Ham stronger (28% vs 19%)
```

### Key Metrics Explained

| Metric | What It Means | How to Use |
| --- | --- | --- |
| **Prediction Confidence** | How sure the system is about the outcome (0–100%) | 70%+ = high confidence; 50–60% = lower confidence |
| **Data Quality** | How much reliable data was available (0–100%) | 90%+ = excellent; 70–80% = good; <70% = limited |
| **Expected Goals (xG)** | Estimated quality chances created (0–5) | Home team 1.4, Away team 0.8 = home team created better chances |
| **Win Probability** | Estimated chance home/away/draw wins (%) | Home 47%, Draw 28%, Away 25% = slight home advantage |
| **BTTS (Both Teams Score)** | Probability both teams score at least 1 goal | 44% = moderate, expect low-scoring match |
| **Over/Under 2.5 Goals** | Total goals expected to be higher or lower than 2.5 | Over 40% = slightly likely to have ≤2 goals |

### Summary Markdown

The `summary.md` file includes:

1. **Executive Summary** — League, date, confidence, data quality
2. **Form Analysis** — Recent performance of both teams
3. **Head-to-Head** — Historical matchup record
4. **Expected Score** — Most likely score + probability breakdown
5. **Betting Lines** — BTTS, Over/Under, exact scores
6. **Weather & Conditions** — Temperature, wind, impact on play
7. **Advanced Predictions** — Shot quality, player impact (if available)

---

## Workflows & Use Cases

### Use Case 1: Quick Daily Summary

**Goal:** Check predictions for today's matches (~5 min/day)

```bash
# Morning routine
python generate_fast_reports.py generate 5 matches for premier-league

# Open the latest reports/leagues/premier-league/matches/
# -> Open prediction_card.png in your browser or image viewer
```

### Use Case 2: Pre-Match Analysis

**Goal:** Deep dive into one specific match before kickoff

```bash
# Generate 1 match
python generate_fast_reports.py generate 1 matches for premier-league

# Open the generated summary.md file
# -> Read: Expected score, form analysis, weather impact, H2H
# -> Check: Data quality (ensure ≥80% confidence)
```

### Use Case 3: Weekly Review

**Goal:** Compare predictions across multiple leagues

```bash
# Generate predictions for all major leagues
python generate_fast_reports.py generate 5 matches for premier-league
python generate_fast_reports.py generate 5 matches for la-liga
python generate_fast_reports.py generate 5 matches for bundesliga

# Browse reports/leagues/ and compare win probabilities across leagues
```

### Use Case 4: Backtesting (Advanced)

**Goal:** Evaluate how accurate predictions are over time

```bash
# After matches have been played:
python advanced_prediction_engine.py backtest --lookback=30 --league=premier-league

# Output: Accuracy metrics, calibration charts, ROI analysis
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'app'"

**Solution:** Ensure you're in the project root directory:

```powershell
cd C:\Dev\STATS
.\.venv\Scripts\Activate.ps1
```

### Issue: "API Rate Limit Exceeded (429)"

**Cause:** Too many API calls to Football-Data.org or API-Football in a short time.

**Solution:**
1. Wait 5–10 minutes before running again
2. Check your API key quotas:
   - Football-Data.org: 10 requests/min (free tier)
   - API-Football: 100 requests/day (free tier)
3. Consider upgrading to a paid tier if prediction generation is a daily task

### Issue: "Data not available — using fallback"

**Cause:** An external API (weather, injuries, form) is unavailable or rate-limited.

**Impact:** Prediction will use heuristics instead of live data; confidence may be slightly lower.

**Solution:** Re-run the prediction in 5–10 minutes (data will be cached).

### Issue: "No upcoming matches found"

**Cause:** The league's season has ended or API has no data for the date range.

**Solution:**
- Check if the league is in-season (e.g., Premier League season is Aug–May)
- Try a different league
- Verify your API key is valid: `Test API key` in Football-Data.org dashboard

### Issue: Prediction card image is blank or corrupted

**Cause:** Matplotlib rendering issue or missing fonts.

**Solution:**

```bash
# Reinstall matplotlib
pip uninstall matplotlib -y
pip install matplotlib
```

### Issue: ".env file not found" error

**Cause:** `.env` file is missing.

**Solution:**

```bash
# Create .env from template
Copy-Item .env.example .env  # Windows
cp .env.example .env          # Mac/Linux

# Edit .env and add your API keys
```

### Issue: Slow performance / taking >2 min per match

**Cause:**
- Slow internet connection
- API server slowdown
- Your machine is busy with other processes

**Solution:**
1. Close other applications
2. Check internet speed: `ping google.com`
3. Try again in 5 minutes

---

## Advanced Configuration

### Customizing Prediction Output

Edit `config/settings.yaml` to customize:

```yaml
# Prediction confidence threshold (only show ≥ threshold)
min_confidence: 0.65

# Data quality threshold
min_data_quality: 0.70

# Number of historical seasons to consider
form_window_matches: 10

# Cache TTL (Time-To-Live)
cache_ttl_minutes: 120
```

### Adjusting Model Weights

The system uses an ensemble of models. To adjust their relative weights:

```python
# In enhanced_predictor.py, find:
MODEL_WEIGHTS = {
    'xg_model': 0.35,        # Expected Goals
    'elo_model': 0.25,       # Team strength (ELO)
    'form_model': 0.20,      # Recent form
    'h2h_model': 0.10,       # Head-to-head history
    'market_model': 0.10,    # Betting odds
}

# Adjust as needed and re-run predictions
```

### Exporting Predictions to CSV

```bash
python scripts/export_predictions_csv.py --league=premier-league --output=results.csv
```

Output: `results.csv` with columns: Team1, Team2, PredictedScore, Confidence, WinProbability

### Running Evaluation Tests

```bash
# Evaluate model accuracy on historical data
python test_enhanced_ingestion.py -v

# Expected output: Test coverage ≥ 70%
```

---

## Getting Help

### Documentation

- **Architecture:** See [docs/architecture.md](docs/architecture.md)
- **Data sources:** See [docs/data-sources.md](docs/)
- **API reference:** See [AGENT_HANDOFF.md](AGENT_HANDOFF.md) for developer setup

### Reporting Issues

Found a bug? Have a suggestion?

1. Check [GitHub Issues](https://github.com/Zed-777/sports-prediction-system/issues)
2. Create a new issue with:
   - What you were trying to do
   - Error message (if any)
   - Python version (`python --version`)
   - League and match details

### Contact

**Maintainer:** See [MAINTAINERS.md](MAINTAINERS.md)

**Security issues:** See [SECURITY.md](SECURITY.md) for responsible disclosure

---

## Disclaimer

⚠️ **Educational Purposes Only**

This system is designed for **analysis and research**. Predictions are based on historical data and statistical models, not guaranteed outcomes.

- **Do not use** for financial betting or gambling decisions
- **Always verify** predictions with domain expertise and current news
- **Understand risk:** Sports outcomes are inherently unpredictable
- **Keep responsible:** Gamble responsibly or not at all

See [AGENT_HANDOFF.md](AGENT_HANDOFF.md#disclaimer) for full terms.

---

## Frequently Asked Questions

**Q: How accurate are the predictions?**
A: ~55% on test data (2+ seasons). This is better than random (50%) but not perfect. Use as one data point, not the only one.

**Q: Can I use this for live betting?**
A: Not recommended. Predictions are pre-match only; real-time updates are limited.

**Q: How often should I update the model?**
A: Monthly with new match data. The system auto-retrains when 50+ new matches are available.

**Q: What leagues are supported?**
A: Premier League (England), La Liga (Spain), Serie A (Italy), Bundesliga (Germany), Ligue 1 (France). Others via custom API setup.

**Q: Do I need a GPU for faster predictions?**
A: No. CPU is sufficient. Predictions take 80–120 seconds per match regardless.

**Q: Can I contribute predictions or feedback?**
A: Yes! See [CONTRIBUTING.md](CONTRIBUTING.md) for how to submit issues and improvements.

---

## Version & Updates

- **Current Version:** 4.1.0
- **Release Date:** 2026-04-04
- **Python Support:** 3.8–3.12

See [CHANGELOG.md](CHANGELOG.md) for release history and updates.

---

## Happy Predicting! 🎯⚽
