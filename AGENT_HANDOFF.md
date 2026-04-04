# AGENT_HANDOFF.md

**Goal:** Enable a new contributor or maintainer to run the full SportsPredictionSystem in under 30 minutes.  
**Last Updated:** 2026-04-03  
**Target Audience:** Developers, maintainers, AI agents  

---

## ⏱️ Quick Timeline

| Step | Duration | Task |
| --- | --- | --- |
| **1** | 2 min | Clone repo, open PowerShell |
| **2** | 5 min | Run environment setup script |
| **3** | 3 min | Copy .env.example → .env and populate API keys |
| **4** | 5 min | Run first prediction (smoke test) |
| **5** | 5 min | Run test suite |
| **6** | 5 min | Explore output and documentation |
| **Total** | ~25 minutes | Full onboarding complete |

---

## 📋 Prerequisites

- **OS:** Windows 10+ (PowerShell 5.1+) or Linux/macOS (bash 4+)
- **Python:** 3.9 or higher (check: `python --version`)
- **Git:** Latest version (check: `git --version`)
- **Network:** Outbound HTTPS access to external APIs (see [SECURITY.md](SECURITY.md#network-security--external-connections))
- **Disk Space:** ~500 MB for venv + dependencies; ~1 GB for cached data
- **Optional:** Visual Studio Code with Python + Pylance extensions for development

---

## 🚀 Step 1: Clone & Navigate (2 minutes)

### On Windows (PowerShell)

```powershell
# Clone the repository
git clone https://github.com/Zed-777/sports-prediction-system.git
cd sports-prediction-system

# Verify you're in the right place
ls README.md, MPDP.md, SECURITY.md
```

### On macOS/Linux (bash)

```bash
git clone https://github.com/Zed-777/sports-prediction-system.git
cd sports-prediction-system
ls README.md MPDP.md SECURITY.md
```

---

## 🔧 Step 2: Set Up Python Environment (5 minutes)

### Automated Setup (Recommended)
This script creates a virtual environment, installs all dependencies, and validates the setup.

#### Windows (PowerShell)

```powershell
# Run the idempotent setup script
powershell -ExecutionPolicy Bypass -File scripts\dev_setup.ps1

# Or manually:
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### macOS/Linux (bash)

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Verify Setup:**

```bash
python -c "import pandas, numpy, sklearn, lightgbm; print('✅ All dependencies installed')"
```

---

## 🔑 Step 3: Configure API Keys (3 minutes)

### Option A: Interactive Setup (Easiest)

```powershell
# Windows: Interactive script guides you through API key setup
powershell -ExecutionPolicy Bypass -File scripts\setup_api_key.ps1
```

### Option B: Manual Setup (Copy-Paste)

1. **Copy the template:**

   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your API keys** (minimal required keys):

   ```bash
   # At minimum, add one or both of these:
   FOOTBALL_DATA_API_KEY=your_key_here
   API_FOOTBALL_KEY=your_key_here
   
   # Optional (for enhanced features):
   ODDS_API_KEY=your_key_here
   OPENMETEO_API_KEY=your_key_here
   ```

3. **Verify .env is in .gitignore** (prevents accidental commit):

   ```bash
   cat .gitignore | grep "\.env"  # Should show: .env
   ```

### Getting API Keys (Free Tier Available)

| API | Sign-Up | Free Tier | Key Steps |
| --- | --- | --- | --- |
| **Football-Data.org** | <https://www.football-data.org/client/register> | ✅ Yes (10 req/min) | 1. Sign up with email 2. Copy API key from dashboard 3. Paste into .env |
| **API-Football (RapidAPI)** | <https://rapidapi.com/api-sports/api/api-football> | ✅ Yes (1000/day) | 1. Sign in to RapidAPI 2. Subscribe to api-football 3. Copy X-RapidAPI-Key from "Code Snippets" |
| **The Odds API** | <https://www.api-sports.io/> | ✅ Limited | Same as API-Football |
| **Open-Meteo** | <https://open-meteo.com/> | ✅ Yes (100k/day) | No registration needed; optional key for priority |

**Validation (Optional):**

```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv('FOOTBALL_DATA_API_KEY')
print(f'✅ API key loaded' if key else '❌ No API key found')
"
```

---

## 🎯 Step 4: Run First Prediction (5 minutes)

### Smoke Test 1: Quick Prediction (30 sec)

```bash
# Activate venv if not already active
# On Windows: .\.venv\Scripts\Activate.ps1
# On macOS/Linux: source .venv/bin/activate

# Run Phase 2 Lite prediction on sample data
python phase2_lite.py
```

**Expected Output:**

```text
2026-04-03 10:15:22 [INFO] SportsPredictionSystem v4.1.0
2026-04-03 10:15:22 [INFO] Loaded 45 features, 2000+ matches
2026-04-03 10:15:23 [INFO] LaLiga: Real Madrid vs Barcelona - Confidence: 62%, Home Win: 48%
2026-04-03 10:15:23 [INFO] Predictions written to reports/latest/predictions.json
✅ Smoke test passed
```

### Smoke Test 2: Generate Report (1 min)

```bash
# Generate a realistic report for 1 match
python generate_fast_reports.py generate 1 matches for la-liga

# Check output
ls reports/ | head  # Should show JSON, PNG, Markdown files
```

**Expected Output:**

```text
Generating 1 matches for la-liga...
✅ Report saved to reports/2026-04-03_laliga_1match.json
✅ Visualizations saved to reports/latest/
Done in 2.3 seconds
```

### Smoke Test 3: Run Tests (2 min)

```bash
# Run unit tests (should see ~100+ passed tests)
pytest -q --tb=short

# Or with coverage:
pytest --cov=app tests/ --cov-fail-under=70
```

**Expected Output:**

```text
tests/test_*.py ............................ 156 passed in 5.23s
✅ All tests passed
Coverage: 72% (core modules: 85%)
```

---

## 🧪 Step 5: Explore & Verify (5 minutes)

### Tour the Output Folder

```bash
# Generated reports and predictions
ls -la reports/

# Sample: latest prediction
cat reports/latest/predictions.json | head -20

# Sample: latest visualization (PNG or Markdown)
ls reports/latest/*.png
ls reports/latest/*.md
```

### Check Logs

```bash
# View recent activity
ls -la data/logs/daily/
tail -50 data/logs/daily/$(date +%Y-%m-%d).log

# Look for any errors
grep -i "ERROR\|CRITICAL" data/logs/daily/*.log
```

### Verify Data Pipeline

```bash
# Check cached data
ls -la data/cache/ | head -20

# Check processed features
ls -la data/processed/ | head -20

# Check models
ls -la models/ | head -20
```

---

## 📚 Common Development Commands

### Run Predictions

```bash
# Single match smoke test
python phase2_lite.py

# Generate N matches report for a league
python generate_fast_reports.py generate 5 matches for la-liga
python generate_fast_reports.py generate 10 matches for premier-league

# Backtest on historical data
python scripts/optimize_accuracy.py --mode backtest --league la-liga
```

### Run Tests

```bash
# Quick test (core modules only)
pytest tests/ -q

# Full test with coverage
pytest tests/ --cov=app --cov-fail-under=70

# Tests for specific module
pytest tests/test_enhanced_ingestion.py -v

# Run only smoke tests
pytest -k smoke -v
```

### Code Quality

```bash
# Format code (black)
black app/ scripts/ tests/

# Lint (ruff)
ruff check app/ scripts/ tests/

# Type check (mypy)
mypy app/ --strict

# Run all linters
python -m pytest -q && black . && ruff check . && mypy app/
```

### Data & Models

```bash
# Fetch historical data
python scripts/collect_historical_results.py --fetch

# Run optimization (tune accuracy)
python scripts/optimize_accuracy.py --mode full --league la-liga

# Retrain models
python app/run.py --retrain-models
```

### Docker (If You Prefer Containers)

```bash
# Build image
docker build -t sports-prediction:latest .

# Run smoke test in container
docker run --rm sports-prediction:latest python phase2_lite.py

# Run with .env file
docker run --rm --env-file .env sports-prediction:latest python generate_fast_reports.py generate 1 matches for la-liga
```

---

## 📂 Key Files & Folders for Onboarding

**Root Scripts (Quick Runners):**
- `phase2_lite.py` — 30-second smoke test; validates entire pipeline
- `generate_fast_reports.py` — Generate predictions for N matches; outputs JSON/PNG/Markdown
- `verify_system.py` — System health check (dependencies, API connectivity, data)

**App Module (Core Logic):**
- `app/cli.py` — Integrated command-line interface for all operations
- `app/run.py` — Core prediction runner
- `app/data/` — Data ingestion and API connectors
- `app/models/` — ML models (ELO, Poisson, LightGBM ensemble)
- `app/features/` — Feature engineering
- `app/reports/` — Report generation

**Configuration:**
- `.env.example` → Copy to `.env` for API keys
- `config/settings.yaml` — Rate limits, cache TTL, model parameters
- `config/team_name_map.yaml` — Canonical team name mapping
- `Dockerfile` — Container image (if using Docker)

**Documentation:**
- `README.md` — Project overview and quickstart
- `MPDP.md` — Roadmap and current milestone
- `SECURITY.md` — Security policies and threats
- `VULNERABILITY_ASSESSMENT.md` — Security audit results
- `docs/architecture.md` — System design and components
- `docs/SCRAPING_COMPLIANCE.md` — Data collection legal review
- `.github/copilot-instructions.md` — AI agent guidance

**Testing & Data:**
- `tests/` — Unit and integration tests
- `tests/data/` — Sample fixtures and test datasets
- `data/` — Cache, processed data, results, logs
- `models/` — Trained ML model artifacts

---

## 🔍 Data Retrieval & Regeneration

### Fetch Historical Data

```bash
# Bulk fetch 2+ seasons (recommended first-time setup)
python scripts/fetch_historical_bulk.py

# Or fetch incrementally:
python scripts/collect_historical_results.py --fetch --league la-liga

# Check what data exists:
ls -la data/processed/
```

### Regenerate Features

```bash
# Rebuild feature engineering pipeline
python app/features/build_features.py --input data/processed/ --output data/features/

# Check generated features:
head data/features/laliga_features.csv
```

### Retrain Models

```bash
# Quick retrain (uses existing data)
python app/models/train.py --quick

# Full retraining (longer, but more accurate)
python app/models/train.py --full

# Models saved to:
ls -la models/
```

---

## 🛠️ Troubleshooting

### Common Issues

#### Issue: "API key not found" or "401 Unauthorized"

```bash
# Check .env file exists and has valid key
cat .env | grep API_FOOTBALL_KEY

# If blank or missing:
# 1. Get key from https://rapidapi.com/api-sports/api/api-football
# 2. Edit .env: API_FOOTBALL_KEY=your_actual_key
# 3. Rerun: python phase2_lite.py
```

#### Issue: "Module not found: lightgbm / scipy / numpy"

```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or upgrade pip first:
pip install --upgrade pip
pip install -r requirements.txt
```

#### Issue: "predictions output incomplete" or "no matches to predict"

```bash
# Fetch historical data first:
python scripts/fetch_historical_bulk.py

# Then retry:
python generate_fast_reports.py generate 1 matches for la-liga
```

#### Issue: "Rate limited (429)" from external API

```bash
# Check config/settings.yaml for rate limits
# Increase cache TTL to reduce API calls:
# In config/settings.yaml: cache_ttl_hours: 72 (was 24)

# Or wait a few minutes and retry (built-in exponential backoff)
```

#### Issue: Tests fail with "assert confidence > 0.5"

```bash
# This is expected if no historical data loaded
# Fetch historical data:
python scripts/fetch_historical_bulk.py

# Then re-run:
pytest tests/ -q
```

### Debug Logging

```bash
# Increase logging verbosity
export LOG_LEVEL=DEBUG  # macOS/Linux
# or in PowerShell:
$env:LOG_LEVEL = "DEBUG"

python phase2_lite.py

# Traces will show API calls, feature generation, model inference
```

### Health Check

```bash
# Run system verification
python verify_system.py

# Output shows: ✅ Python version, ✅ Dependencies, ✅ API connectivity, ✅ Data status
```

---

## 📖 Learning Resources

**For Prediction Engine Logic:**
- [docs/architecture.md](docs/architecture.md) — System design and data flow
- [MPDP.md](MPDP.md) — Current features and planned work (next 3 tasks)
- `.github/copilot-instructions.md` — Coding conventions and patterns

**For Data Collection & APIs:**
- [docs/SCRAPING_COMPLIANCE.md](docs/SCRAPING_COMPLIANCE.md) — Legal and ethical guidelines
- `app/data/connectors/` — Examples of API integrations
- `config/settings.yaml` — Rate-limit and cache configuration

**For ML & Models:**
- [docs/ML_ADVANCED_MODEL_PLAN.md](docs/ML_ADVANCED_MODEL_PLAN.md) — Model architecture details
- `app/models/` — ELO, Poisson, ensemble logic
- `app/features/` — Feature engineering pipeline

**For Testing & CI/CD:**
- `.github/workflows/` — GitHub Actions pipelines
- `tests/` — Example unit and integration tests
- `requirements-dev.txt` — Development tools (pytest, black, mypy, ruff)

---

## ✅ 30-Minute Onboarding Checklist

Once you've completed the steps above, check these off:

- [ ] **Cloned repo** and navigated to root directory
- [ ] **Ran setup script** (`scripts\dev_setup.ps1` or manual venv + pip)
- [ ] **Populated .env** with at least one API key (Football-Data or API-Football)
- [ ] **Ran smoke test** (`python phase2_lite.py`) and saw predictions
- [ ] **Generated report** (`python generate_fast_reports.py generate 1 matches for la-liga`)
- [ ] **Ran test suite** (`pytest -q`) and saw tests pass
- [ ] **Explored output** in `reports/` and `data/logs/`
- [ ] **Read README.md** for high-level overview
- [ ] **Skimmed MPDP.md** to understand current work and next tasks
- [ ] **Familiar with key commands:** `phase2_lite.py`, `generate_fast_reports.py`, `pytest`

**You're now ready to:**
- 🧪 Modify code and run tests
- 📊 Generate custom reports
- 🔧 Debug issues with logging
- 📚 Explore the codebase using `.github/copilot-instructions.md`
- 🚀 Deploy to staging or production (see `deploy/` folder)

---

## 🆘 Still Stuck?

1. **Check logs:** `tail -100 data/logs/daily/$(date +%Y-%m-%d).log`
2. **Run health check:** `python verify_system.py`
3. **Search issues:** <https://github.com/Zed-777/sports-prediction-system/issues>
4. **Ask maintainer:** Create a GitHub issue with:
   - OS version and Python version (`python --version`)
   - Exact error message and last 50 lines of logs
   - What you've already tried
5. **Check documentation:** Start with [README.md](README.md) → [SECURITY.md](SECURITY.md) → [docs/](docs/)

---

## 📝 Next Steps After Onboarding

**To contribute code:**
1. Read [CONTRIBUTING.md](CONTRIBUTING.md) for branch strategy and PR guidelines
2. Review [.github/copilot-instructions.md](.github/copilot-instructions.md) for coding conventions
3. Pick a task from [MPDP.md](MPDP.md) "Next Three Actionable Tasks" section
4. Create a feature branch, make changes, add tests, submit PR

**To deploy:**
1. See `deploy/windows-deploy.ps1` for Windows scheduled tasks
2. See `deploy/sports-prediction.service` for Linux systemd
3. See `CONTAINER_SETUP.md` for Docker deployment

**To understand architecture deeply:**
1. Read [architecture.md](docs/architecture.md) (if it exists; we're adding it in Phase 2)
2. Explore UML diagrams in `UML/` (coming in Phase 2)
3. Review model architecture in `docs/ML_ADVANCED_MODEL_PLAN.md`

---

**Created:** 2026-04-03  
**Maintained by:** @Zed-777  
**Last verified:** 2026-04-03 (works in <30 minutes on Windows 10+, macOS 10.15+, Ubuntu 20.04+)
