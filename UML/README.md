# UML Diagrams - SportsPredictionSystem Architecture

This directory contains visual architecture diagrams for the SportsPredictionSystem. Diagrams are stored as Mermaid `.mmd` files for easy maintenance and version control, with rendered versions available on GitHub.

---

## 📊 Diagrams

### 1. Component Diagram (`component_diagram.mmd`)

**Purpose:** Shows the high-level architecture and component relationships.

**Scope:**
- External data sources (APIs)
- Data ingestion layer (connectors, cache, validation)
- Processing layer (feature engineering, ML models, ensemble)
- Output layer (report generation, storage)
- Configuration and utilities shared across components
- CI/CD and testing infrastructure

**Key Relationships:**
- External APIs → Connectors → Cache → Validation → Processing
- Configuration (settings.yaml, team_name_map.yaml) drives all components
- Utilities (HTTP client, logging, caching) used throughout
- CI/CD triggers tests and scheduled automation

**How to Read:**
1. **Red boxes** (top): External APIs we depend on
2. **Yellow boxes** (left): Configuration that drives behavior
3. **Orange → Blue → Green**: Data flow from ingestion to output
4. **Purple boxes** (bottom right): Automation and testing

**Mapping to Code Folders:**

```text
Component: app/data/connectors/
├─ Code: app/data/connectors/*.py (football_data.py, api_football.py, etc.)
├─ Purpose: HTTP clients for each external API
└─ Caching: Handled by Cache Layer (data/cache/)

Component: Data Validation
├─ Code: data_quality_enhancer.py, app/types.py
├─ Purpose: Pydantic schema validation + statistical checks
└─ Storage: Validated data written to data/raw/ or data/processed/

Component: app/features/
├─ Code: app/features/*.py (elo_ratings.py, form_metrics.py, etc.)
├─ Purpose: Transform raw data into ML-ready features
└─ Output: Feature vectors (60+ dimensions)

Component: app/models/
├─ Code: app/models/*.py (elo_model.py, poisson_model.py, lightgbm_model.py)
├─ Purpose: Independent model inference
└─ Artifacts: models/*.pkl (serialized model weights)

Component: Ensemble Aggregation
├─ Code: app/models/ensemble.py, calibration.py
├─ Purpose: Weighted voting + 6-layer confidence calibration
└─ Output: Final predictions (Home/Draw/Away probs + confidence)

Component: app/reports/
├─ Code: app/reports/*.py
├─ Purpose: Format predictions as JSON, Markdown, PNG
└─ Output: reports/ folder (machine-readable + human-readable)
```

---

### 2. Sequence Diagram (`sequence_diagram.mmd`)

**Purpose:** Shows the runtime flow of a prediction request from start to finish.

**Scope:**
- Startup sequence (load config, initialize cache)
- Data fetch from external APIs
- Data validation and quality checks
- Feature engineering
- Model inference (3 models in parallel)
- Ensemble voting and confidence calibration (6 layers)
- Report generation (JSON, Markdown, PNG)
- Result storage and logging

**Key Phases:**

1. **STARTUP** (implicit at beginning)
   - Load configuration (settings.yaml, team_name_map.yaml)
   - Initialize cache backend
   - Load historical ELO ratings from data/historical/

2. **FETCH** (API calls)
   - Get next matches from Football-Data.org API
   - Check cache first (24-hour TTL)
   - If cache miss: fetch updated data; store for next time

3. **VALIDATE** (Data quality checks)
   - Pydantic schema validation (required fields, types)
   - Statistical checks (Z-score outliers, range validation)
   - Cross-source verification (compare across 2+ APIs)

4. **FEATURES** (Feature engineering)
   - Load 3+ years of historical team data
   - Calculate ELO ratings with recency weighting
   - Calculate form metrics (rolling 5-match, 10-match averages)
   - Add player impact, match context, weather
   - Output: 60-dimensional feature vector

5. **PREDICT** (Model inference, parallelized)
   - **ELO Model:** Rating deltas → P(Home), P(Away)
   - **Poisson Model:** Goal distribution → predicted score probs
   - **LightGBM Model:** Feature-based classifier → outcome probs
   - Each runs independently; results combined in next step

6. **ENSEMBLE** (Voting + calibration)
   - Weighted average of 3 models
   - 6-layer confidence validation:
     1. Input validation (features non-null and in bounds)
     2. Baseline accuracy (compare vs historical average)
     3. Feature completeness (60/60 fields present)
     4. Model disagreement (penalty if models diverge)
     5. Market odds alignment (consensus from betting markets)
     6. Bayesian uncertainty (quantified via calibration model)
   - Output: Final confidence % (30–95%)

7. **REPORT** (Output generation)
   - JSON: Machine-readable with all metadata
   - Markdown: Human-readable tables and commentary
   - PNG: Visual confidence bars and model agreement charts

8. **STORE** (Persistence)
   - Write all outputs to reports/ folder
   - Log predictions for later backtesting
   - Archive to data/processed/ for historical analysis

9. **FEEDBACK** (Accuracy tracking, optional)
   - Store prediction → Later compare vs actual result
   - Used to evaluate model performance and retrain

**Call Flow Highlights:**

```text
App/CLI
  ├─ Load config
  ├─ Fetch from APIs (cache-first)
  ├─ Validate (Pydantic + quality checks)
  ├─ Features (ELO, form, context → vector)
  ├─ Models (run 3 in parallel)
  │   ├─ ELO predictions
  │   ├─ Poisson predictions
  │   └─ LightGBM predictions
  ├─ Ensemble (weighted avg + 6-layer calibration)
  ├─ Reports (JSON + Markdown + PNG)
  ├─ Store (data/processed/)
  └─ Log (data/logs/daily/)
```

**Typical Latency:**
- API fetch: 500–1000 ms
- Validation: 50–100 ms
- Feature engineering: 100–200 ms
- Model inference: 300–800 ms (3 models in parallel)
- Ensemble + calibration: 50–100 ms
- Report generation: 200–500 ms
- **Total per match: 1.5–3.5 seconds**

---

## 🔗 Diagram-to-Code Mapping

### By Component

| Diagram Element | Code Location | Responsibility |
| --- | --- | --- |
| Football-Data.org API | `app/data/connectors/football_data.py` | Fetch matches, standings, results |
| API-Football RapidAPI | `app/data/connectors/api_football.py` | Fetch injuries, lineups, H2H stats |
| FBref / Understat | `app/data/connectors/fbref.py`, `understat.py` | xG, shot quality, advanced stats (future) |
| Cache Layer | `app/utils/cache.py`, `data/cache/` | JSON caching with TTL |
| Validation | `data_quality_enhancer.py`, `app/types.py` | Pydantic schemas, outlier detection |
| ELO Rating | `app/features/elo_ratings.py` | Recency-weighted team ratings |
| Form Metrics | `app/features/form_metrics.py` | 5/10-match rolling averages |
| Player Impact | `app/features/player_impact.py` | Weighted importance (goals, assists, xG) |
| Match Context | `app/features/context_classification.py` | Derby, title race, cup final classification |
| ELO Model | `app/models/elo_model.py` | Rating delta → outcome probability |
| Poisson Model | `app/models/poisson_model.py` | Expected goals → goal distribution |
| LightGBM Model | `app/models/lightgbm_model.py` | Feature-based ensemble predictor |
| Ensemble | `app/models/ensemble.py` | Weighted voting of 3 models |
| Calibration | `app/models/calibration.py` | 6-layer confidence validation |
| JSON Report | `app/reports/json_report.py` | Machine-readable output format |
| Markdown Report | `app/reports/markdown_report.py` | Human-readable tables and commentary |
| PNG Visualization | `app/reports/visualization.py` | Matplotlib/Plotly charts |
| Storage | `data/processed/`, `reports/` | Result persistence |
| Logging | `app/utils/logging.py`, `data/logs/daily/` | Activity tracking and debugging |

### By Runtime Flow

| Phase | Duration | Code Path |
| --- | --- | --- |
| 1. Load config | - | `app/config.py` → `config/settings.yaml` |
| 2. Init cache | - | `app/utils/cache.py` → `data/cache/` |
| 3. Fetch from APIs | 0.5–1.0 sec | `app/data/connectors/*.py` with rate-limiting |
| 4. Validate | 0.05–0.1 sec | `data_quality_enhancer.py`, `app/types.py` |
| 5. Engineer features | 0.1–0.2 sec | `app/features/*.py` (ELO, form, context) |
| 6. ELO inference | 0.05–0.1 sec | `app/models/elo_model.py` |
| 7. Poisson inference | 0.1–0.2 sec | `app/models/poisson_model.py` |
| 8. LightGBM inference | 0.2–0.5 sec | `app/models/lightgbm_model.py` |
| 9. Ensemble voting | 0.02–0.05 sec | `app/models/ensemble.py` |
| 10. Calibration (6 layers) | 0.05–0.1 sec | `app/models/calibration.py` |
| 11. Report generation | 0.2–0.5 sec | `app/reports/*.py` |
| 12. Storage | 0.02–0.05 sec | `data/processed/`, `reports/` |

---

## 🔄 When Diagrams Should Be Updated

Update diagrams when:
- New external data source integrated (add to component diagram)
- Feature engineering step added (update features box)
- New validation layer introduced (update validation box)
- Model architecture changed (update models box + sequence)
- Report format added (update report generation step)
- Deployment target changes (add infrastructure components)

**Update Process:**
1. Edit `.mmd` file (Mermaid markdown)
2. Test rendering in GitHub editor (preview)
3. Commit and push
4. Create/update corresponding `.png` or `.svg` exports (optional, for presentations)

---

## 📚 Related Documentation

- [architecture.md](../architecture.md) — Textual system architecture (complements these diagrams)
- [MPDP.md](../MPDP.md) — Roadmap and planned architecture changes
- [SECURITY.md](../SECURITY.md) — Security threat model (influences API + cache design)
- `.github/copilot-instructions.md` — Coding conventions for components

---

## 🛠️ Diagram Rendering

### View in GitHub
- Mermaid diagrams render automatically in GitHub (`.mmd` files)
- Click on any `.mmd` file in the `UML/` folder to see rendered diagram

### Export to PNG/SVG
Use any Mermaid rendering tool:

```bash
# Option 1: Mermaid CLI
npm install -g @mermaid-js/mermaid-cli
mmdc -i UML/component_diagram.mmd -o UML/component_diagram.png

# Option 2: Mermaid Live Editor
# Go to https://mermaid.live/ → paste .mmd content → export PNG/SVG

# Option 3: VS Code extension
# Install "Mermaid Markdown Syntax Highlighting" extension
```

### Embed in Documentation

```markdown
# Use in markdown files:
![Component Diagram](../UML/component_diagram.mmd)

# Or with HTML:
<img src="../UML/component_diagram.mmd" alt="Component Diagram" />
```

---

## 📝 Mermaid Syntax Notes

**Component Diagram:**
- `subgraph "Name"`: Groups related components
- `A --> B`: Directed edge (dependency)
- `A -.-> B`: Dashed edge (optional/configuration dependency)
- `classDef`: Color styling for semantic grouping

**Sequence Diagram:**
- `participant A`: Actor in sequence
- `A->>B`: Synchronous call
- `A-->>B`: Return/response
- `par ... and ... end`: Parallel execution
- `alt ... else ... end`: Conditional branching
- `Note over A`: Annotated comment

---

**Last Updated:** 2026-04-03  
**Maintained by:** @Zed-777
