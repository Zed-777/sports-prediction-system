# architecture.md

**Last Updated:** 2026-04-03  
**Version:** v4.1.0  
**Target Audience:** Developers, architects, maintainers  

---

## 📐 System Architecture Overview

The SportsPredictionSystem is a **batch-driven sports forecasting engine** that:
1. **Ingests** historical and real-time match data from multiple APIs
2. **Transforms** raw data into ML-ready features (ELO ratings, team form, player stats, context)
3. **Predicts** match outcomes using ensemble models (ELO, Poisson, LightGBM, Bayesian calibration)
4. **Validates** predictions against multi-layer data quality checks
5. **Reports** predictions with confidence metrics and explainability

```text
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL DATA SOURCES                         │
│  Football-Data.org │ API-Football │ FBref │ Understat │ Weather │
└────────────────────────┬──────────────────────────────────────┘
                         │ (HTTPS, per-host rate-limiting)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   DATA INGESTION LAYER                           │
│  ├─ app/data/connectors/ (API clients, cache managers)         │
│  ├─ enhanced_data_ingestion.py (orchestration)                 │
│  └─ data/cache/ (Redis-compatible JSON caching)               │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                 DATA VALIDATION & QUALITY                        │
│  ├─ data_quality_enhancer.py (outlier detection, schema check)  │
│  ├─ Pydantic validators (app/types.py - strict type checking)   │
│  └─ Cross-source verification (3 APIs, flag discrepancies)      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│              FEATURE ENGINEERING & PREPROCESSING                 │
│  ├─ app/features/ (ELO rating, form, defensive solidity, xG)   │
│  ├─ Player impact scoring (weighted by goals, assists, xG)     │
│  ├─ Match context classification (derby, title race, etc.)      │
│  └─ Weather and travel fatigue adjustments                     │
└───────────────────────┬────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────────┐
│                 MACHINE LEARNING MODELS                          │
│  ├─ ELO Model (ratings decay, recency weight, momentum)         │
│  ├─ Poisson Model (goal distribution, under/over thresholds)   │
│  ├─ LightGBM Ensemble (feature-based outcome predictor)        │
│  ├─ Bayesian Calibration (confidence tuning via 6-layer checks)│
│  └─ Model Disagreement Detector (if models diverge → low conf)  │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│           PREDICTION AGGREGATION & CONFIDENCE SCORING            │
│  ├─ Ensemble voting (3+ models) with weighted averaging         │
│  ├─ 6-Layer Confidence Validation:                              │
│  │   1. Neural network input validation                        │
│  │   2. Historical accuracy baseline                           │
│  │   3. Feature completeness check                             │
│  │   4. Model disagreement penalty                             │
│  │   5. Market odds alignment check                            │
│  │   6. Bayesian uncertainty quantification                    │
│  └─ Output: Match result probs (Home, Draw, Away) + confidence │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│              REPORTING & EXPLAINABILITY LAYER                    │
│  ├─ app/reports/ (JSON, PNG, Markdown generators)              │
│  ├─ Confidence breakdowns by source                             │
│  ├─ Feature importance (SHAP values for LightGBM)              │
│  └─ Visualization (matplotlib, plotly for dashboards)          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Folder Structure & Component Mapping

```text
sports-prediction-system/
│
├── app/                               # Core application modules
│   ├── __init__.py
│   ├── cli.py                        # Command-line interface entry point
│   ├── run.py                        # Main prediction orchestration
│   ├── config.py                     # Configuration loader
│   ├── types.py                      # Pydantic models (strict type validation)
│   │
│   ├── data/                         # Data layer
│   │   ├── connectors/               # External API clients
│   │   │   ├── football_data.py      # Football-Data.org API
│   │   │   ├── api_football.py       # API-Football (RapidAPI)
│   │   │   ├── injuries.py           # Injury/availability connector
│   │   │   ├── odds.py               # Betting odds aggregation
│   │   │   └── weather.py            # Open-Meteo weather data
│   │   └── cache.py                  # Redis-compatible caching (JSON backend)
│   │
│   ├── features/                     # Feature engineering
│   │   ├── __init__.py
│   │   ├── build_features.py         # Feature pipeline orchestrator
│   │   ├── elo_ratings.py            # Dynamic ELO with recency weighting
│   │   ├── form_metrics.py           # Form calculations (5/10 match averages)
│   │   ├── player_impact.py          # Player-level importance scoring
│   │   ├── xg_features.py            # Expected goals feature engineering
│   │   └── context_classification.py # Match context (derby, title race)
│   │
│   ├── models/                       # ML models and inference
│   │   ├── __init__.py
│   │   ├── base.py                   # Base model interface
│   │   ├── elo_model.py              # ELO rating predictor
│   │   ├── poisson_model.py          # Poisson goal distribution
│   │   ├── lightgbm_model.py         # Gradient boosting ensemble
│   │   ├── ensemble.py               # Multi-model voting & aggregation
│   │   ├── ensemble_disagreement.py  # Detect model divergence
│   │   ├── calibration.py            # Bayesian confidence calibration
│   │   └── player_impact.py          # Player-level importance (also in features/)
│   │
│   ├── reports/                      # Report generation
│   │   ├── __init__.py
│   │   ├── generator.py              # Base report class
│   │   ├── json_report.py            # JSON output
│   │   ├── markdown_report.py        # Markdown + tables
│   │   ├── visualization.py          # PNG/HTML visualization (matplotlib)
│   │   └── dashboard.py              # Dash/Streamlit dashboard (future)
│   │
│   ├── utils/                        # Shared utilities
│   │   ├── __init__.py
│   │   ├── http.py                   # HTTP client with rate-limiting
│   │   ├── cache.py                  # Cache backend abstraction
│   │   ├── logging.py                # Logging with secret redaction
│   │   ├── math_utils.py             # Statistical helpers
│   │   └── validation.py             # Data validation utilities
│   │
│   ├── analytics/                    # Analytical tools (accuracy tracking)
│   │   ├── backtest.py               # Backtesting framework
│   │   └── accuracy_metrics.py       # Win rate, ROI, Brier score
│   │
│   └── monitoring/                   # Observability (future)
│       └── metrics.py                # Prometheus-style metrics (optional)
│
├── data/                              # Data layer (not in version control)
│   ├── raw/                          # Raw API responses (snapshots)
│   ├── processed/                    # Cleaned, validated data
│   ├── cache/                        # JSON cache files (API responses)
│   ├── expanded_cache/               # Enriched cache with extra fields
│   ├── features/                     # Engineered features (CSV)
│   ├── historical/                   # Time-series snapshots (3+ years)
│   ├── logs/                         # Application logs (rotated)
│   ├── backup_csv/                   # Backup/export format
│   ├── optimization_results/         # Hyperparameter tuning outputs
│   └── snapshots/                    # Point-in-time backup data
│
├── models/                            # Trained ML artifacts (not in version control)
│   ├── elo_ratings.pkl               # Serialized ELO state
│   ├── lightgbm_classifier.pkl       # LightGBM binary classifier
│   ├── ensemble_scaler.pkl           # Feature scaler for ensemble
│   ├── calibration_model.pkl         # Confidence calibration model
│   ├── advanced/                     # Advanced model variants
│   └── neural/                       # Neural network models (future)
│
├── tests/                             # Test suite
│   ├── __init__.py
│   ├── test_enhanced_ingestion.py    # Data ingestion tests
│   ├── test_features.py              # Feature engineering tests
│   ├── test_models.py                # Model inference tests
│   ├── test_reports.py               # Report generation tests
│   ├── test_data_quality.py          # Quality check tests
│   ├── data/                         # Test fixtures and sample data
│   └── conftest.py                   # Pytest configuration
│
├── scripts/                           # Standalone utilities & automation
│   ├── optimize_accuracy.py          # Backtest and hyperparameter tuning
│   ├── collect_historical_results.py # Fetch completed match results
│   ├── fetch_historical_bulk.py      # Bulk historical data loader
│   ├── dev_setup.ps1                 # Windows environment setup
│   ├── setup_api_key.ps1             # Interactive API key configuration
│   ├── run_daily_fetch.ps1           # Daily scheduled data update
│   └── ... (other automation scripts)
│
├── config/                            # Configuration files
│   ├── settings.yaml                 # Rate limits, cache TTL, model params
│   ├── team_name_map.yaml            # Canonical team name mapping
│   └── schemas/                      # JSON schema definitions
│
├── docs/                              # Documentation
│   ├── architecture.md               # This file
│   ├── SCRAPING_COMPLIANCE.md        # Legal/ethical data collection
│   ├── ML_ADVANCED_MODEL_PLAN.md     # Model enhancements roadmap
│   ├── automation.md                 # Scheduled task setup
│   └── ... (other guides)
│
├── .github/
│   ├── workflows/                    # GitHub Actions CI/CD
│   │   ├── ci.yml                    # Main Python tests
│   │   ├── ci-windows.yml            # Windows-specific tests
│   │   ├── audit.yml                 # Dependency scanning
│   │   └── ... (other workflows)
│   ├── CODEOWNERS                    # Code review assignment
│   └── pull_request_template.md      # PR checklist
│
├── deploy/                            # Deployment & infrastructure
│   ├── windows-deploy.ps1            # Windows Task Scheduler setup
│   ├── sports-prediction.service     # Linux systemd service
│   └── docker-compose.yml            # Docker Compose orchestration
│
├── .env.example                       # API key template (copy to .env)
├── .gitignore                         # Version control exclusions
├── requirements.txt                   # Python dependencies (pinned)
├── requirements-dev.txt               # Development tools
├── Dockerfile                         # Container image definition
├── .dockerignore                      # Docker build exclusions
├── README.md                          # Project overview & quickstart
├── MPDP.md                           # Roadmap and development plan
├── SECURITY.md                        # Security policies & threat model
├── VULNERABILITY_ASSESSMENT.md        # Security audit results
├── AGENT_HANDOFF.md                  # Onboarding guide (this file!)
├── CONTRIBUTING.md                    # Contributor guidelines (Phase 2)
├── PROJECT_GUIDELINES.md             # Repository standards
├── CHANGELOG.md                       # Release history
├── LICENSE                            # MIT License
│
└── pyproject.toml                     # Python project metadata
```

---

## 🔄 Data Flow & Processing Pipeline

### A. Startup Sequence (app/run.py)

```text
1. Load Configuration
   ├─ config/settings.yaml (rate limits, cache TTL)
   ├─ .env (API keys)
   └─ config/team_name_map.yaml (team name canonicalization)

2. Initialize Data Layer
   ├─ Create database connection (SQLite or PostgreSQL)
   ├─ Initialize cache backend (JSON or Redis)
   └─ Load cached ELO ratings from data/historical/

3. Fetch Latest Data
   ├─ Call Football-Data.org API for next matches
   ├─ Call API-Football for injury/lineup updates
   ├─ Call Open-Meteo for weather data
   └─ Cache responses with TTL

4. Validate Data Quality
   ├─ Check all required fields present (Pydantic validation)
   ├─ Check for outliers (Z-score, IQR-based)
   ├─ Cross-validate across 2+ sources
   └─ Flag and skip bad records

5. Build Features (for each match)
   ├─ Load historical teams stats (3+ years if available)
   ├─ Calculate ELO ratings (with recency decay)
   ├─ Calculate form metrics (5/10 match rolling averages)
   ├─ Load player impact scores
   ├─ Classify match context (derby, title race, etc.)
   └─ Combine into feature vector (n=60 features)

6. Predict (for each match)
   ├─ ELO model → P(Home), P(Away)
   ├─ Poisson model → P(Home), P(Away) + goal distribution
   ├─ LightGBM model → P(Home), P(Away) + feature importance
   ├─ Ensemble voting (weighted average of 3 models)
   └─ 6-layer confidence calibration

7. Generate Reports
   ├─ JSON output (machine-readable, includes all metadata)
   ├─ Markdown output (human-readable tables, commentary)
   └─ PNG output (visualization of confidence, model agreement)

8. Post-Process & Archive
   └─ Store predictions in data/processed/
   ├─ Log metrics (accuracy tracking)
   └─ Upload to cloud storage (if configured)
```

### B. Match Prediction Flow (Detail)

For each match: **Real Madrid vs Barcelona**

```text
┌─ FETCH DATA (2 sec)
├─ Team stats: Real Madrid (ELO: 1820), Barcelona (ELO: 1780)
├─ Player availability: 3 key Barcelona players out (injury)
├─ Recent form: Real Madrid W-W-D-W (4 of last 5 won)
├─ Weather: Clear, 20°C, no extreme conditions
└─ Fixture context: La Liga Week 30 (title race)

┌─ FEATURE ENGINEERING (1 sec)
├─ ELO deltas: +40 for Real Madrid (home advantage)
├─ Form differential: Real Madrid +2.5 goal diff avg (5-match)
├─ Player impact: -0.8 Barcelona strength multiplier (injuries)
├─ Context: Title race → confidence boost for both teams
└─ Feature vector: [1820, 1780, 2.5, -0.8, 0.05, ...] (60 dims)

┌─ MODEL PREDICTIONS (0.5 sec)
├─ ELO: P(Home=55%, Draw=25%, Away=20%)
├─ Poisson: P(Home=52%, Draw=26%, Away=22%)
├─ LightGBM: P(Home=58%, Draw=24%, Away=18%)
├─ Ensemble: P(Home=55%, Draw=25%, Away=20%)
└─ Model agreement: HIGH (models agree within 5%) → confidence boost

┌─ CONFIDENCE CALIBRATION (0.3 sec)
├─ 6-layer checks:
│   1. Input validation: PASS (all features present)
│   2. Baseline check: Real Madrid avg P(win home) = 58%
│   3. Feature completeness: 60/60 features present → PASS
│   4. Model disagreement: LOW (3% spread) → light penalty
│   5. Market odds: Consensus P(Home) = 54% (close to model)
│   6. Bayesian uncertainty: σ=3% (low uncertainty)
├─ Final confidence: **62%** (rounded from calibrated 62.3%)
└─ Confidence breakdown: {ELO: 0.18, Poisson: 0.16, LightGBM: 0.22, market: 0.06}

┌─ REPORT GENERATION (0.5 sec)
└─ JSON:
   {
     "match": "Real Madrid vs Barcelona",
     "predictions": {
       "home": {"prob": 0.55, "expected_goals": 1.8},
       "draw": {"prob": 0.25},
       "away": {"prob": 0.20, "expected_goals": 1.2}
     },
     "confidence": 0.62,
     "models": {
       "elo": {"home": 0.55, ...},
       "poisson": {"home": 0.52, ...},
       "lightgbm": {"home": 0.58, "feature_importance": {...}}
     }
   }
```

---

## 🔌 Integration Points & External APIs

### Primary Data Sources

| API | Purpose | Rate Limit | Cache TTL | Fallback |
| --- | --- | --- | --- | --- |
| **Football-Data.org** | Match schedule, standings, results | 10 req/min (free) | 24 hours | Historical DB |
| **API-Football (RapidAPI)** | Lineup, injuries, H2H stats | 1000 req/day (free) | 12 hours | Season historical |
| **FBref.com** | Advanced stats (xG, shot quality) | Robots.txt limit | 7 days | Previous season |
| **Understat.com** | xG, understat-specific metrics | Conservative scrape | 7 days | Previous season |
| **Open-Meteo** | Weather conditions | 100k req/day (free) | 24 hours | Historical avg |
| **The Odds API** | Betting consensus | 500 req/month (free) | 6 hours | Model only |

### Secondary Sources (OAuth/Auth Required)

- **NewsAPI** (optional): Team news for injury context
- **Slack webhook** (optional): Notifications
- **MLflow** (optional): Model versioning & experiment tracking

---

## 🚀 Request Lifecycle (Match Prediction)

```text
REQUEST: POST /predict
├─ Payload: {"league": "la-liga", "match_id": 12345}
│
├─ VALIDATION
│   ├─ Check match exists in data/processed/
│   └─ Return 404 if not found
│
├─ DATA FETCHING
│   ├─ Check cache first (data/cache/<match_id>.json)
│   ├─ If >24h old: fetch from API, update cache
│   └─ Return cached copy if fresh
│
├─ FEATURE ENGINEERING
│   ├─ Load team stats (3+ years historical)
│   ├─ Calculate ELO, form, context
│   └─ Validate feature completeness
│
├─ MODEL INFERENCE
│   ├─ ELO: 3 models (quick, <100ms)
│   ├─ Poisson: 1 model (quick, <100ms)
│   ├─ LightGBM: 1 model (quick, <500ms)
│   └─ Ensemble: weighted average
│
├─ CONFIDENCE CALIBRATION
│   ├─ Apply 6-layer checks
│   └─ Final confidence: 30-95%
│
├─ RESPONSE
│   ├─ predictions.json (home, draw, away probs)
│   ├─ confidence (0.30-0.95)
│   ├─ model_breakdown (individual model predictions)
│   └─ feature_importance (top 5 features)
│
└─ LOGGING
    ├─ Log prediction + confidence
    ├─ Store in data/logs/daily/<date>.log
    └─ Track for accuracy backtesting
```

**Response Time:** ~1.5–3 seconds per match (depends on API freshness)

---

## 🎯 Background Jobs & Scheduled Tasks

### Daily (6:00 AM UTC)

```powershell
# Windows Task: "SportsPrediction-DailyFetch"
scripts\run_daily_fetch.ps1
  ├─ Fetch latest match results (completed matches from yesterday)
  ├─ Update team standings and form metrics
  ├─ Retrain dynamic ELO ratings
  └─ Log: data/logs/daily/<date>.log
```

### Weekly (Sunday, 8:00 PM UTC)

```powershell
# Windows Task: "SportsPrediction-WeeklyOptimization"
python scripts/optimize_accuracy.py --mode backtest --league la-liga
  ├─ Backtest current model on 50+ recent matches
  ├─ Evaluate accuracy metrics (win rate, Brier score, ROI)
  ├─ Save results to data/optimization_results/
  └─ Email or Slack notification if accuracy ↑ or issues detected
```

### On-Demand

```bash
# Manual retraining (takes 5-10 min depending on data size)
python app/models/train.py --full
  ├─ Rebuild all models using 3+ years historical data
  ├─ Hyperparameter tuning via Optuna
  ├─ Save artifacts to models/
  └─ Backtest before deployment
```

---

## 🔴 Failure Modes & Recovery

| Failure Mode | Impact | Detection | Recovery |
| --- | --- | --- | --- |
| **API unavailable** | Can't fetch fresh data | 3 failed retries within 10s | Use cached data from <24h ago; flag in logs |
| **Rate-limited (429)** | API throttles us | Response code 429 | Exponential backoff; retry after delay; reduce request rate |
| **Bad data (missing fields)** | Incomplete prediction | Pydantic validation fails | Skip match; log error; use previous season stats as fallback |
| **Model timeout (>30s)** | Prediction hangs | Timeout exception | Return cached prediction; log incident |
| **Disk full** | Logging stops; cache fails | OSError on write | Cleanup old logs/cache; alert maintainer |
| **Bad model artifacts** | Prediction crashes | Model loading fails | Fallback to previous model version; retrain |

**Recovery Strategy:** Always-on fallback model (ELO-only) that requires no external data and trains in <1 second.

---

## 📊 Performance Characteristics

| Operation | Typical Duration | Bottleneck | Optimization |
| --- | --- | --- | --- |
| **API fetch (1 match)** | 500–1000 ms | Network latency | Caching, batch requests |
| **Data validation** | 50–100 ms | Pydantic schema checks | Vectorized validation |
| **Feature engineering** | 100–200 ms | ELO/form calculations | Pre-compute where possible |
| **Model inference** | 300–800 ms | LightGBM ensemble | Use CPU parallelization |
| **Confidence calibration** | 50–100 ms | 6-layer checks | Vectorize checks |
| **Report generation** | 200–500 ms | JSON serialization | Cache template |
| **Total (1 match)** | **1.5–3.5 sec** | — | Parallel API calls where possible |
| **Batch (100 matches)** | **120–280 sec** | — | Process in parallel (multiprocessing) |

---

## 🔐 Security & Data Privacy

- ✅ **API keys:** Environment variables only; never logged
- ✅ **Data validation:** Pydantic strict type checking; no pickle deserialization
- ✅ **SQL safety:** SQLAlchemy ORM (no string concatenation)
- ✅ **Rate-limiting:** Per-host throttle configuration; exponential backoff
- ✅ **Logging:** Sensitive fields redacted (app/utils/logging.py)
- ✅ **Data retention:** Historical data in data/historical/ follows 3-year policy

See [SECURITY.md](SECURITY.md) for comprehensive threat model.

---

## 🧪 Testing Strategy

| Test Level | Scope | Location | Coverage Target |
| --- | --- | --- | --- |
| **Unit tests** | Individual functions (features, models) | tests/test_*.py | ≥80% on core modules |
| **Integration tests** | Multi-module workflows (ingest → predict → report) | tests/test_integration.py | ≥70% on end-to-end flows |
| **Smoke tests** | Quick sanity checks (API connectivity, model loading) | tests/test_smoke.py | All critical paths |
| **Backtests** | Model accuracy on historical data | scripts/optimize_accuracy.py | ≥55% win rate on 6+ month holdout |

**Run locally:** `pytest tests/ --cov=app --cov-fail-under=70`

---

## 📈 Scalability Considerations

### Current (Batch)
- **~1.5–3.5 sec per match prediction**
- **100 matches in 2–5 minutes** (parallelized)
- **API-limited** (rate limits on external services)

### Future (AWS/Cloud scaling)
- Deploy as **containerized microservice** (Dockerfile ready)
- Use **SQS/Celery** for async job queue
- Use **S3 for model artifacts**, DynamoDB for caching
- Use **RDS PostgreSQL** instead of SQLite
- Target: <100ms per match (with parallel inference)

### Model Serving (Future)
- Model quantization (reduce from 100MB to 10MB)
- ONNX export for cross-platform inference
- TensorFlow Lite for edge deployment

---

## 🔄 Version Control & Reproducibility

- **Data versioning:** data/snapshots/ stores point-in-time backups
- **Model versioning:** models/ folder with deterministic filenames (e.g., `lightgbm_20260403_v4.1.pkl`)
- **Dependency pinning:** requirements.txt pins all versions (e.g., `pandas==2.0.0`)
- **Git tags:** Release tags (e.g., `v4.1.0`) for reproducible builds

---

## 📚 Related Documentation

- [MPDP.md](MPDP.md) – Roadmap and current features
- [SECURITY.md](SECURITY.md) – Security threat model and mitigations
- [AGENT_HANDOFF.md](AGENT_HANDOFF.md) – Developer onboarding
- [docs/ML_ADVANCED_MODEL_PLAN.md](docs/ML_ADVANCED_MODEL_PLAN.md) – Deep dive into model enhancements
- [.github/copilot-instructions.md](.github/copilot-instructions.md) – Coding conventions

---

**Architecture Version:** v4.1.0  
**Last Updated:** 2026-04-03  
**Maintained by:** @Zed-777
