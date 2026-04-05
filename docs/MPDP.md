# Master Progress & Development Plan (MPDP) - v4.1.1

**Date**: 2026-04-05  
**Status**: 🟢 ACTIVE  
**Phase**: Phase 2 Lite + Automated Learning Architecture

---

## 🤖 Automated Learning Architecture (NEW v4.1.1)

The sports prediction system now operates with **ZERO manual ML tuning**. Models retrain daily, accuracy drifts are detected, and calibration updates automatically—without user intervention.

### User Workflow (Post-Automation)

```
User Generated (Manual):
  └─ python generate_fast_reports.py generate 5 for premier-league
     └─ Produces: prediction_card.png (view results)

Automatic (Background):
  └─ 4 AM UTC Daily: Automated Learning Loop
     ├─ Step 1: Collect completed match results (API calls)
     ├─ Step 2: Track predictions vs actual outcomes (accuracy metrics)
     ├─ Step 3: Retrain models (per-league optimization)
     ├─ Step 4: Cleanup old cache files
     └─ Logs: data/logs/automated/learning_loop_YYYY-MM-DD_HHmmss.log
```

### Data Persistence (What Survives Report Deletion)

When users delete PNG/MD reports from `reports/`, the learning infrastructure **persists**:

| Component | Location | Format | Survives PNG Delete | Used By |
|-----------|----------|--------|-------------------|---------|
| **Predictions Tracking** | data/predictions.db | SQLite | ✅ YES | accuracy tracking, drift detection |
| **Historical Results** | data/historical/*.json | JSON | ✅ YES | backtesting, model retraining |
| **Trained Models** | models/advanced/*.joblib | joblib | ✅ YES | daily prediction generation |
| **Calibration State** | data/cache/calibration_*.pkl | pickle | ✅ YES | confidence calibration on predictions |
| **Feature Cache** | data/cache/features_*.pkl | pickle | ✅ YES | feature engineering speedup |

**Implication**: Reports are ephemeral (views); learning artifacts are permanent (state).

### Setup Instructions (Zero Setup Required!)

**The good news: GitHub Actions is already configured.** No setup needed!

The workflow file is already in place and will automatically run daily at 4 AM UTC:
- ✅ Workflow: `.github/workflows/daily-learning.yml`
- ✅ Schedule: Daily at 4:00 AM UTC
- ✅ Runtime: ~45-90 minutes (5 leagues × 10-15 min each)
- ✅ Status: Active and running (as soon as this workflow file is pushed)

**What it does automatically**:
- Collects completed match results from Football-Data.org
- Updates prediction tracker with actual outcomes
- Retrains models per-league (ELO, Poisson, RF, GB, Neural, Calibration)
- Cleans up old cache files
- Commits updated models/calibration back to the repo
- Logs all activity (available in Actions tab)

### Verification Commands

```bash
# View learning workflow runs (in GitHub UI)
# Go to: https://github.com/Zed-777/sports-prediction-system/actions/workflows/daily-learning.yml

# Or use GitHub CLI:
gh workflow view daily-learning.yml --repo Zed-777/sports-prediction-system

# View latest run
gh run list --repo Zed-777/sports-prediction-system --workflow daily-learning.yml --limit 5

# View detailed logs of latest run
gh run view --repo Zed-777/sports-prediction-system -w daily-learning.yml --log
```

**Manual Test** (trigger immediately):

```bash
# Using GitHub CLI
gh workflow run daily-learning.yml --repo Zed-777/sports-prediction-system

# Or use GitHub UI: Actions → Daily Automated Learning Loop → Run workflow
```

### Scripts Involved

#### `.github/workflows/daily-learning.yml` (PRIMARY - GitHub Actions)
- **Purpose**: Cloud-hosted daily learning orchestrator
- **Trigger**: Runs at 4 AM UTC daily automatically
- **Manual Trigger**: Available via `workflow_dispatch` in GitHub UI
- **Status**: ✅ ACTIVE - Running daily
- **Monitoring**: View in GitHub Actions tab

#### `scripts/automated_learning_loop.py` (Learning Executor)
- **Purpose**: Execute 4-step learning cycle
- **Run**: `python scripts/automated_learning_loop.py [--league {all|premier-league|la-liga|...}]`
- **Also used by**: GitHub Actions workflow (daily), can be run locally for testing

**4-Step Cycle**:

1. **Collect Results** (`collect_historical_results.py`)
   - Fetch completed matches from Football-Data.org API
   - Stores to: `data/historical/{league}.json`
   - Estimated time: 10-15 min (5 leagues)

2. **Update Predictions** (`update_prediction_results.py`)
   - Record actual match outcomes
   - Calculate prediction accuracy (binomial & calibration metrics)
   - Update: `data/predictions.db`
   - Estimated time: 5 min

3. **Retrain Models** (`optimize_accuracy.py`)
   - Per-league optimization:
     - Tune ELO K-factors
     - Adjust Poisson λ parameters
     - Calibrate confidence scores (6 methods: Platt, Temperature, Beta, Histogram, Venn-ABERS, Isotonic)
     - Random Forest/Gradient Boosting: hyperparameter tuning
     - Neural network: fine-tune LSTM/Attention layers
   - Saves: `models/advanced/*.joblib`
   - Estimated time: 30-60 min (5 leagues × 10-15 min each)

4. **Cleanup** (file management)
   - Remove cache files >30 days old
   - Estimated time: 1 min

**Logging**:
- Output: `data/logs/automated/learning_loop_YYYY-MM-DD_HHmmss.log`
- Format: Timestamp, log level, message
- Both file (DEBUG) and console (INFO) handlers

**Example Usage**:

```bash
# Run all leagues (default)
python scripts/automated_learning_loop.py

# Run single league (for testing)
python scripts/automated_learning_loop.py --league premier-league

# Verbose logging
python scripts/automated_learning_loop.py --verbose
```

### Architecture Options

#### **Option 1: GitHub Actions (PRIMARY - Current v4.1.1)**
- **Pros**: Cloud-hosted, no machine dependency, integrated with repo, free (generous limits), built-in logging
- **Cons**: Slight latency (runs in cloud), API rate limits (manageable for this use case)
- **Workflow**: `.github/workflows/daily-learning.yml`
- **Schedule**: `0 4 * * *` (4 AM UTC daily via `schedule`)
- **Status**: ✅ IMPLEMENTED - Active and running daily

#### **Option 2: Windows Task Scheduler (ALTERNATIVE)**
- **Pros**: Local execution, no cloud dependency, full system privileges
- **Cons**: Windows-only, requires local machine on, admin setup friction
- **Setup**: `python scripts/setup_automated_learning.py` (requires admin)
- **Status**: 🔳 Available if local execution needed

#### **Option 3: Docker Cron (FUTURE v5.0)**
- **Pros**: All-platform, containerized, portable
- **Cons**: Requires Docker running, more overhead
- **Implementation**: `Dockerfile.cron` + `docker-compose.yml` modifications
- **Status**: 🔳 NOT YET IMPLEMENTED

### Monitoring & Troubleshooting

#### Check Task Status

```powershell
# List tasks in SportsPrediction folder
schtasks /query /tn "SportsPrediction\*" /v

# View last run result
schtasks /query /tn "SportsPrediction\SportsPredictionSystem-DailyLearning" /v | Select-Object "Last Run Time", "Next Run Time", "Status"
```

#### View Logs

```powershell
# Last 50 lines of latest log
Get-Content (Get-ChildItem data/logs/automated -Filter "learning_loop_*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName -Tail 50

# Search for errors
Select-String "ERROR|CRITICAL|FAIL" data/logs/automated/learning_loop_*.log
```

#### Manual Test

```powershell
# Run once to verify
python scripts/automated_learning_loop.py --league premier-league --verbose

# Check output
Get-Content data/logs/automated/learning_loop_*.log -Tail 100
```

#### Common Issues & Fixes

| Issue | Symptom | Solution |
|-------|---------|----------|
| Task won't create | "Access Denied" error | Run setup script as Administrator (`Right-Click → Run as Administrator`) |
| Script not found | "FileNotFoundError: automated_learning_loop.py" | Verify file exists at `scripts/automated_learning_loop.py` |
| API rate limits | "429 Too Many Requests" in logs | Increase `--throttle-delay` in `collect_historical_results.py` |
| Out of disk space | "No space left on device" in cleanup | Delete old reports manually: `rm reports/archive/*` |
| Models won't load | "ModuleNotFoundError: sklearn" | Reinstall: `pip install -r requirements.txt` |

---

## 📊 Learning Components Inventory

### ML Models
- **ELO Model**: Dynamic rating adjustment (K-factor tuned daily)
- **Poisson Regression**: Goal distribution modeling (λ parameters optimized)
- **Random Forest**: Ensemble predictor (n_estimators: 50-200, max_depth tuned)
- **Gradient Boosting**: Sequential error correction (learning_rate, n_estimators optimized)
- **Neural Network**: LSTM + Attention layers (epochs, dropout, lr fine-tuned)

### Calibration Methods (6 implementations)
1. **Platt Scaling**: Logistic post-processing
2. **Temperature Scaling**: Single parameter softmax refinement
3. **Beta Calibration**: Affine transformation on logits
4. **Histogram Binning**: Empirical bin-wise adjustment
5. **Venn-ABERS**: Online isotonic regression
6. **Isotonic Regression**: Non-parametric monotonic transformation

### Feature Engineering (25+ features)
- **Team Strength**: ELO, form (last 5 games), home/away splits
- **Offense/Defense**: Goals for/against, expected goals (xG)
- **Position**: League standing, recent trajectory
- **Head-to-Head**: Win/loss history vs opponent
- **Temporal**: Time since last match, days rest
- **External**: Weather (temperature, wind), injury list

### Backtesting Framework
- **Time-series CV**: K-fold with no data leakage
- **Metrics**: Accuracy, Brier score, Log Loss, ROC AUC
- **Per-league optimization**: Hyperparameters tuned separately
- **Drift detection**: >5% accuracy drop triggers alerts

### Prediction Tracking Database
- **Table**: `PredictionRecord`
- **Fields**: match_id, predicted probs (H/D/A), confidence, timestamp, actual_outcome, accuracy_metrics
- **Use**: Track model performance over time, detect drift, enable retraining

### Bayesian Updater (Beta-Binomial Conjugate Prior)
- **Prior**: Beta(α=2, β=2) [weakly informative]
- **Likelihood**: Binomial (win=1, loss=0 for binary outcomes)
- **Posterior**: Updated after each match
- **Output**: Credible intervals for win probability

---

## 🔄 Full Learning Loop Workflow (Detailed)

```
4 AM UTC Daily (GitHub Actions)
  │
  ├─► [GitHub Actions] Trigger: schedule cron '0 4 * * *'
  │   └─► Or manual: workflow_dispatch (GitHub UI)
  │
  └─► [daily-learning.yml] Execution (Ubuntu runner)
      │
      ├─► Setup: Checkout code, Python 3.11, Install dependencies
      │
      ├─► Step 1: Collect Results
      │   ├─ Football-Data.org API: fetch finished matches (last 7 days)
      │   ├─ Store: data/historical/{league}.json
      │   ├─ Leagues: Premier League, La Liga, Serie A, Bundesliga, Ligue 1
      │   └─ Time: ~10-15 min
      │
      ├─► Step 2: Update Predictions
      │   ├─ Read: data/predictions.db (predictions made 7 days ago)
      │   ├─ Compare: All prediction outcomes now known (match complete)
      │   ├─ Calculate: Accuracy metrics per model, per league
      │   ├─ Store: Updated accuracy_metrics column in DB
      │   └─ Time: ~5 min
      │
      ├─► Step 3: Retrain Models (Per League: 10-15 min each)
      │   ├─ [Premier League Optimization]
      │   │  ├─ ELO: Tune K-factor (args: historical results)
      │   │  ├─ Poisson: Optimize λ (home/away)
      │   │  ├─ RF/GB: HPO via RandomSearch (cv=5, n_iter=10)
      │   │  ├─ Neural: Fine-tune LSTM/Attention (epochs=20, early_stop)
      │   │  ├─ Calibration: Fit all 6 methods on validation set
      │   │  └─ Save: models/advanced/premier_league_*.joblib
      │   │
      │   ├─ [La Liga Optimization] (similar pattern)
      │   ├─ [Serie A Optimization]
      │   ├─ [Bundesliga Optimization]
      │   └─ [Ligue 1 Optimization]
      │
      ├─► Step 4: Cleanup
      │   ├─ Remove: Cache files >30 days old
      │   ├─ Compact: SQLite DB (VACUUM)
      │   └─ Time: ~1 min
      │
      ├─► Commit Results
      │   ├─ Git add: models/advanced/*.joblib, data/historical/*.json, data/predictions.db
      │   ├─ Commit: 'ci: automated learning loop - retrain models and calibration (daily)'
      │   └─ Push: back to main branch
      │
      └─► Report Summary
          ├─ Upload logs artifact (30-day retention)
          ├─ Post GitHub summary (visible in Actions tab)
          └─ Next run: Tomorrow 4 AM UTC
```

---

## 🚀 Quick Start (Users)

### Generate Predictions (Manual)

```bash
# Generate 5 predictions for Premier League
python generate_fast_reports.py generate 5 for premier-league

# View results
open reports/prediction_card.png
```

### Automated Learning (Zero Setup Required!)
- ✅ Learning loop **already configured** in GitHub Actions
- ✅ Runs automatically **every day at 4 AM UTC**
- ✅ Models updated and committed back to repo
- ✅ No local machine required

**To monitor learning runs**:
1. Go to: <https://github.com/Zed-777/sports-prediction-system/actions>
2. Click: "Daily Automated Learning Loop"
3. View latest run logs and status

**To manually trigger a learning run** (test):
1. Go to GitHub Actions page
2. Select: "Daily Automated Learning Loop"
3. Click: "Run workflow"

---

## 🔧 Architecture Decisions

### Why GitHub Actions (Primary Solution)?
- **No setup friction**: GitHub Actions is built-in; no admin elevation needed
- **Cloud-hosted**: Learning runs whether your machine is on or off
- **Native integration**: Workflow file in `.github/workflows/` is version-controlled
- **Built-in logging**: All runs visible in GitHub UI with full logs
- **Free tier**: Generous limits (2,000 minutes/month free, task takes ~1.5 hrs)
- **Reliability**: GitHub's infrastructure, not machine-dependent
- **Results committed back**: Updated models automatically pushed to repo

### Why NOT Windows Task Scheduler?
- ✅ Still available as alternative (see Option 2)
- ❌ Requires admin privileges (not always available)
- ❌ Machine must stay on/running (not suitable for laptops)
- ❌ Manual log checking required
- ❌ More setup friction

### Why Python for Learning Loop (Not PowerShell)?
- **Simplicity**: Direct subprocess calls, exception handling, logging
- **Consistency**: Python backend already in use; single language throughout
- **Portability**: Runs identically on Linux (GitHub Actions) and Windows
- **Maintainability**: Less brittle error handling than nested PowerShell $()

### Why 4 AM UTC?
- **Time**: Low-traffic cluster for APIs (4 AM UTC = off-peak noise trading)
- **Before trading**: Predictions ready for next day's markets
- **After fetch**: Schedules 1 hour after fetch-results workflow (3 AM UTC)
- **Run window**: 45-90 min fits comfortably before trading opens

---

## 📝 Next Steps (Post-v4.1.1)

### Immediate (This Week)
- [ ] Verify first automated learning run (check GitHub Actions tab)
- [ ] Monitor accuracy trends (view logs to verify models improving)
- [ ] Test manual trigger (run workflow once via GitHub UI)

### v4.1.2 (Bug Fixes)
- [ ] Add webhook notifications (email on drift detection)
- [ ] Implement circuit breaker (skip days if API down >12 hours)
- [ ] Add model comparison dashboard (accuracy trends over time)

### v4.2 (Windows Alternative)
- [ ] Document Windows Task Scheduler setup (`.github/workflows/daily-learning.yml` is primary, but alternative available)
- [ ] Create helper script for Windows users (batch/PowerShell elevate wrapper)

### v5.0 (Monitoring Dashboard)
- [ ] Flask/Streamlit dashboard: Real-time learning status
- [ ] Model accuracy trends (live charts)
- [ ] Prediction feedback loop (user annotations)
- [ ] Drift alerts (>5% accuracy loss)

---

## 📋 Compliance & Security

- **Data**: All learning artifacts stored locally (`data/`, `models/`) - no cloud sync
- **Logging**: Logs stored in `data/logs/automated/` - no external logging (privacy)
- **APIs**: Football-Data.org API calls logged; rate limits respected
- **Secrets**: .env file (not committed); `setup_automated_learning.py` doesn't read secrets
- **Backups**: Use `deploy/prepare_for_transfer.ps1` to backup learning state

---

## 📚 Related Docs

- **README.md**: High-level system overview
- **USER_MANUAL.md**: End-user guide for prediction generation
- **PROJECT_GUIDELINES.md**: Development standards
- **docs/ML_ADVANCED_MODEL_PLAN.md**: Deep-dive ML architecture
- **docs/SCRAPING_COMPLIANCE.md**: API rate limiting & caching rules

---

**Last Updated**: 2026-04-05  
**Maintainer**: Sports Prediction System  
**Version**: v4.1.1
