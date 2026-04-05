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

### Setup Instructions (5 minutes, One-Time)

**Prerequisite**: Administrator privileges on Windows

```powershell
# Step 1: Navigate to project root
cd C:\Dev\STATS

# Step 2: Run setup script (admin required)
python scripts/setup_automated_learning.py

# Expected output:
# [SUCCESS] Scheduled task created successfully!
# [INFO] Learning loop will run tomorrow at 4 AM UTC
```

**What it does**:
- Validates Python learning loop script exists
- Creates Windows Task Scheduler task
- Task folder: `SportsPrediction`
- Task name: `SportsPredictionSystem-DailyLearning`
- Schedule: Daily 4 AM UTC
- Runtime: ~45-90 minutes (5 leagues × 10-15 min each)

### Verification Commands

```powershell
# Check task exists
schtasks /query /tn "SportsPrediction\SportsPredictionSystem-DailyLearning" /v

# View recent runs
Get-Content data/logs/automated/learning_loop_*.log | Select-Object -Last 50

# Manually trigger (test)
schtasks /run /tn "SportsPrediction\SportsPredictionSystem-DailyLearning"
```

### Scripts Involved

#### `scripts/setup_automated_learning.py` (Setup)
- **Purpose**: Register Windows Task Scheduler task (run once)
- **Run**: `python scripts/setup_automated_learning.py [--force]`
- **Output**: Creates Task Scheduler task running learning loop daily
- **Requires**: Administrator (checked via `ctypes.windll.shell.IsUserAnAdmin()`)
- **Status**: ✅ READY

#### `scripts/automated_learning_loop.py` (Daily Runner)
- **Purpose**: Execute 4-step learning cycle (runs daily 4 AM UTC)
- **Run**: `python scripts/automated_learning_loop.py [--league {all|premier-league|la-liga|...}]`

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

#### **Option 1: Windows Task Scheduler (PRIMARY - Current)**
- **Pros**: Native to Windows, reliable, no external dependencies, local execution
- **Cons**: Windows-only
- **Setup**: `python scripts/setup_automated_learning.py`
- **Status**: ✅ IMPLEMENTED

#### **Option 2: GitHub Actions (FALLBACK - Future v4.2)**
- **Pros**: Cross-platform, integrated with repo, free, monitored via GitHub UI
- **Cons**: Require GitHub token, API rate limits, network-dependent
- **Workflow**: `.github/workflows/daily-learning.yml` (TBD)
- **Schedule**: `0 4 * * *` (4 AM UTC daily via `schedule`)
- **Status**: 🔳 NOT YET IMPLEMENTED

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
4 AM UTC (Daily)
  │
  ├─► [Task Scheduler] Main entry: schtasks runs Python
  │   │
  │   └─► [setup_automated_learning.py] Initial registration (one-time setup)
  │       └─► Registers Task Scheduler task to run learning loop
  │
  └─► [learning_loop.py] Execution (daily)
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
      └─► [Log Summary]
          ├─ Status: SUCCESS/FAILURE
          ├─ Models retrained: {5 leagues}
          ├─ Accuracy delta: {before → after %}
          └─ Next run: {tomorrow 4 AM UTC}
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

### Enable Automated Learning (One-Time)
```powershell
# Run as Administrator
python scripts/setup_automated_learning.py

# Verify
schtasks /query /tn "SportsPrediction\SportsPredictionSystem-DailyLearning"
```

### Monitor Learning (Ongoing)
```powershell
# View latest log
Get-Content data/logs/automated/learning_loop_*.log -Tail 30

# Manually trigger today (for testing)
schtasks /run /tn "SportsPrediction\SportsPredictionSystem-DailyLearning"
```

---

## 🔧 Architecture Decisions

### Why Python for Learning Loop (Not PowerShell)?
- **Simplicity**: Direct subprocess calls, exception handling, logging (no $() nesting issues)
- **Portability**: Python backend already in use for ML; single language throughout
- **Maintainability**: Less brittle than nested PowerShell error expressions
- **Logging**: Python logging module = cleaner output than Write-Progress

### Why Windows Task Scheduler (Not GitHub Actions)?
- **Local execution**: No network dependency, API rate limits, or GitHub token rotation
- **Reliability**: Native Windows feature, no external failures
- **Privacy**: All data stays in-house (no cloud sync)
- **Development velocity**: GitHub Actions future-proof (v4.2+), but Task Scheduler ready now

### Why 4 AM UTC?
- **Time**: Low-traffic cluster for APIs (4 AM UTC = 11 PM EST = off-peak)
- **Before trading**: Predictions ready for next day's markets
- **Run window**: 45-90 min fits comfortably before work hours

---

## 📝 Next Steps (Post-v4.1.1)

### v4.1.2 (Bug Fixes)
- [ ] Add webhook notifications (email on drift detection)
- [ ] Implement circuit breaker (skip days if API down >12 hours)
- [ ] Add model comparison dashboard (accuracy trends over time)

### v4.2 (GitHub Actions)
- [ ] Implement `.github/workflows/daily-learning.yml` (fallback automation)
- [ ] Store secrets in GitHub (API keys, SMTP config)
- [ ] Artifact storage for historical logs

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
