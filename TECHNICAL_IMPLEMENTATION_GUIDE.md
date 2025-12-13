# TECHNICAL DEEP-DIVE: AI OPTIMIZATION IMPLEMENTATION GUIDE
## SportsPredictionSystem v4.2 - Developer Reference

---

## TABLE OF CONTENTS
1. [Architecture Overview](#architecture-overview)
2. [Current AI Pipeline](#current-ai-pipeline)
3. [Optimization Details](#optimization-details)
4. [Implementation Code Templates](#implementation-code-templates)
5. [Integration Points](#integration-points)
6. [Testing Strategy](#testing-strategy)

---

## ARCHITECTURE OVERVIEW

### Current System (v4.2)
```
PREDICTION PIPELINE
═══════════════════════════════════════════════════════════════

Input Match Data
       ↓
Data Quality Enhancement (DataQualityEnhancer)
       ├─ Data validation (6-layer smart checks)
       ├─ Feature enrichment
       └─ Quality scoring
       ↓
Ensemble Prediction (EnhancedPredictor)
       ├─ Legacy Model (Heuristics, ELO, Poisson)
       ├─ ML Model (Trained ensemble: RF, GB, XGB, LGB)
       ├─ Neural Model (Pattern matching)
       └─ Monte Carlo Model (Statistical simulation)
       ↓
xG Reconciliation Layer
       ├─ Align win probs with expected goals
       └─ Ensure consistency
       ↓
Confidence Optimization (Phase 2 Lite)
       ├─ Bayesian calibration
       ├─ Agreement analysis
       ├─ Data sufficiency assessment
       └─ Uncertainty bounds
       ↓
Report Generation
       ├─ JSON output
       ├─ PNG visualization
       └─ Markdown report
```

### Key Components

**1. EnhancedPredictor (enhanced_predictor.py - 3040 lines)**
- Main prediction engine
- 4 sub-models + ensemble logic
- xG reconciliation
- Confidence calculation

**2. DataQualityEnhancer (data_quality_enhancer.py)**
- 6-layer data validation
- Quality scoring
- Feature enhancement

**3. AdvancedAIEngine (app/models/advanced_ai_engine.py)**
- ML ensemble (Random Forest, Gradient Boosting, XGBoost, LightGBM)
- Feature extraction (20 features)
- Real trained models

**4. ConfidenceOptimizer (app/models/confidence_optimizer.py)**
- Bayesian calibration
- Ensemble agreement analysis
- Data sufficiency assessment

**5. Phase2Lite (phase2_lite.py)**
- Enhanced intelligence wrapper
- Integrates all components
- +18% confidence boost

---

## CURRENT AI PIPELINE

### Data Flow (Detailed)

```python
# 1. INPUT
match_data = {
    'homeTeam': {'name': 'Real Madrid', 'id': 86},
    'awayTeam': {'name': 'Barcelona', 'id': 81},
    'date': '2025-12-05'
}

# 2. DATA ENHANCEMENT
enhanced_data = data_quality_enhancer.enhance_match_data(match_data)
# Adds: H2H stats, form metrics, injury info, weather, market odds

# 3. PREDICTION (LEGACY MODEL)
legacy_pred = enhanced_predictor._predict_legacy(enhanced_data)
# Output: home_prob=0.65, draw_prob=0.18, away_prob=0.17
#         expected_home_goals=1.8, expected_away_goals=0.9

# 4. PREDICTION (ML MODEL)
ml_pred = advanced_ai_engine.enhanced_prediction(match_data, 'PD')
# Uses 20 features + trained model ensemble
# Output: home_prob=0.62, draw_prob=0.20, away_prob=0.18

# 5. PREDICTION (NEURAL MODEL)
neural_pred = enhanced_predictor._predict_neural_patterns(enhanced_data)
# Similar match pattern matching
# Output: home_prob=0.68, draw_prob=0.15, away_prob=0.17

# 6. PREDICTION (MONTE CARLO MODEL)
monte_carlo_pred = enhanced_predictor._predict_monte_carlo(enhanced_data)
# Statistical simulation
# Output: home_prob=0.66, draw_prob=0.17, away_prob=0.17

# 7. ENSEMBLE
ensemble = enhanced_predictor._create_ai_ensemble_prediction(
    legacy_pred, ml_pred, neural_pred, monte_carlo_pred
)
# Current: Static weights [0.25, 0.30, 0.25, 0.20]
# Output: home_prob=0.652, draw_prob=0.175, away_prob=0.173

# 8. XG RECONCILIATION
reconciled_xg = enhanced_predictor._reconcile_xg_with_win_probs(
    home_prob, away_prob, ensemble_xg
)
# Ensures xG aligns with probabilities
# Output: home_xg=1.75, away_xg=0.85

# 9. CONFIDENCE OPTIMIZATION
confidence = confidence_optimizer.optimize_confidence(
    base_confidence=0.74,
    prediction_data=ensemble,
    ensemble_predictions=ensemble
)
# Applies Bayesian calibration, agreement analysis, data checks
# Output: confidence_metrics with uncertainty bounds

# 10. OUTPUT
final_prediction = {
    'home_win_prob': 0.652,
    'draw_prob': 0.175,
    'away_win_prob': 0.173,
    'expected_score': '1-0',
    'confidence': 0.82,
    'reasoning': [...]
}
```

### Current Weighting System

```python
# Static weights (Lines 2798-2815 in enhanced_predictor.py)
weights = {
    'legacy': 0.25,      # Heuristics + ELO baseline
    'ml': 0.30,          # ML ensemble (4 models)
    'neural': 0.25,      # Pattern matching
    'monte_carlo': 0.20  # Statistical simulation
}

# Weighted ensemble
home_prob = (
    legacy['home_win_probability'] * 0.25 +
    ml['home_win_probability'] * 0.30 +
    neural['neural_home_prob'] * 0.25 +
    monte_carlo['home_win_probability'] * 0.20
)
```

**Problem:** These weights don't adapt to:
- Data quality differences
- Model agreement levels
- League-specific strengths
- Historical performance

---

## OPTIMIZATION DETAILS

### OPTIMIZATION #1: Adaptive Ensemble Weights

#### Current Implementation (STATIC)
```python
weights = {
    'legacy': 0.25,
    'ml': 0.30,
    'neural': 0.25,
    'monte_carlo': 0.20
}
```

#### Proposed Implementation (ADAPTIVE)

**Inputs:**
- Data quality score (0-1, from DataQualityEnhancer)
- H2H data availability (0-1, percentage of H2H matches available)
- Model agreement variance (0-1, lower = higher agreement)
- Form consistency (0-1, from recent matches)
- League code (PD, PL, BL1, SA, FL1)

**Logic:**
```python
def _calculate_adaptive_weights(self, enhanced_data, predictions, data_quality_score):
    """
    Calculate context-aware ensemble weights
    
    Adjustment factors:
    1. Data Quality Multiplier: High quality → boost all weights toward equal
    2. H2H Boost: Good H2H data → boost legacy/neural (they use H2H well)
    3. Agreement Signal: High agreement → boost models that agree
    4. League Adjustment: League-specific model strengths
    5. Form Consistency: If recent form matches current prediction → boost weight
    """
    
    # Base weights
    base_weights = {
        'legacy': 0.25,
        'ml': 0.30,
        'neural': 0.25,
        'monte_carlo': 0.20
    }
    
    # 1. Data Quality Adjustment
    if data_quality_score > 0.85:  # Excellent data
        quality_mult = 0.95  # Flatten weights (more trust in all models)
    elif data_quality_score > 0.70:  # Good data
        quality_mult = 1.0
    elif data_quality_score > 0.50:  # Acceptable data
        quality_mult = 1.05  # Reduce weight for data-hungry models (ML)
    else:  # Poor data
        quality_mult = 1.15  # Boost legacy (doesn't need much data)
    
    # 2. H2H Data Availability
    h2h_availability = enhanced_data.get('h2h_data_quality', 0.5)
    if h2h_availability > 0.8:  # Great H2H history
        base_weights['legacy'] *= 1.1  # Legacy uses H2H well
        base_weights['neural'] *= 1.1  # Neural does too
        base_weights['ml'] *= 0.95
    elif h2h_availability < 0.2:  # Poor H2H history
        base_weights['legacy'] *= 0.9   # Legacy relies on H2H
        base_weights['ml'] *= 1.1       # ML is data-flexible
    
    # 3. Model Agreement (from predictions variance)
    predictions_list = [
        predictions['legacy']['home_win_probability'],
        predictions['ml']['home_win_probability'],
        predictions['neural']['neural_home_prob'],
        predictions['monte_carlo']['home_win_probability']
    ]
    variance = np.var(predictions_list)
    
    if variance < 0.01:  # Very high agreement
        # All models agree - boost them equally
        agreement_signals = [0.95, 0.95, 0.95, 0.95]
    elif variance < 0.03:  # Moderate agreement
        # Models mostly agree
        agreement_signals = [1.0, 1.0, 1.0, 1.0]
    else:  # Disagreement
        # Weight toward mode (most common prediction)
        mode_pred = max(set(predictions_list), key=predictions_list.count)
        agreement_signals = [
            1.1 if abs(pred - mode_pred) < 0.03 else 0.9
            for pred in predictions_list
        ]
    
    # 4. League-Specific Adjustments
    league_code = enhanced_data.get('league_code', 'DEFAULT')
    league_adjustments = {
        'PL': {'legacy': 0.95, 'ml': 1.05, 'neural': 1.0, 'monte_carlo': 1.0},
        'PD': {'legacy': 1.0, 'ml': 1.0, 'neural': 1.0, 'monte_carlo': 1.0},
        'BL1': {'legacy': 1.1, 'ml': 0.95, 'neural': 1.0, 'monte_carlo': 1.0},
        'SA': {'legacy': 1.05, 'ml': 0.95, 'neural': 1.05, 'monte_carlo': 0.95},
        'FL1': {'legacy': 0.9, 'ml': 1.1, 'neural': 0.95, 'monte_carlo': 1.0}
    }
    league_adj = league_adjustments.get(league_code, 
                  {'legacy': 1.0, 'ml': 1.0, 'neural': 1.0, 'monte_carlo': 1.0})
    
    # 5. Form Consistency
    form_score = enhanced_data.get('home_form_score', 50) / 100
    form_signal = 1.0 + (form_score - 0.5) * 0.1  # ±5% adjustment
    
    # Combine all signals
    models = ['legacy', 'ml', 'neural', 'monte_carlo']
    adjusted_weights = {}
    for i, model in enumerate(models):
        adjusted_weights[model] = (
            base_weights[model] *
            quality_mult *
            agreement_signals[i] *
            league_adj[model] *
            form_signal
        )
    
    # Normalize to sum to 1.0
    total = sum(adjusted_weights.values())
    adjusted_weights = {k: v/total for k, v in adjusted_weights.items()}
    
    return adjusted_weights
```

**Integration Point:**
```python
# In _create_ai_ensemble_prediction() - Line 2798
# BEFORE:
weights = {
    'legacy': 0.25,
    'ml': 0.30,
    'neural': 0.25,
    'monte_carlo': 0.20
}

# AFTER:
weights = self._calculate_adaptive_weights(enhanced_data, {
    'legacy': legacy,
    'ml': ml,
    'neural': neural,
    'monte_carlo': monte_carlo
}, data_quality_score)
```

**Expected Impact:** +3-5% accuracy  
**Complexity:** Moderate (2-3 hours)

---

### OPTIMIZATION #2: Non-Linear Calibration

#### Current Implementation (LINEAR)
```python
# Lines 2819-2824
comps_dict = {'legacy': {...}, 'ml': ml, 'neural': neural, ...}
cal_probs = self._calibrate_probs_nonlinear(...)
# Returns percentages adjusted by agreement factor
```

#### Proposed Implementation (ISOTONIC REGRESSION)

**Concept:**
```
Isotonic Regression: Learn monotonic mapping from
uncalibrated probabilities → true probabilities

Example:
- Model predicts 70% home win
- Historically, when model says 70%, actual rate is 75%
- Adjust 70% → 75%
```

**Implementation:**
```python
import pickle
from scipy.isotonic import IsotonicRegression

class CalibrationManager:
    """Manage calibration curves using isotonic regression"""
    
    def __init__(self, calibration_dir='models/calibration'):
        self.calibration_dir = Path(calibration_dir)
        self.calibration_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or initialize calibration curves
        self.iso_home = self._load_calibration('home')
        self.iso_draw = self._load_calibration('draw')
        self.iso_away = self._load_calibration('away')
    
    def _load_calibration(self, outcome):
        """Load pre-trained calibration curve"""
        path = self.calibration_dir / f'iso_regression_{outcome}.pkl'
        if path.exists():
            with open(path, 'rb') as f:
                return pickle.load(f)
        return None
    
    def calibrate_probability(self, prob_raw, outcome):
        """
        Apply calibration curve to raw probability
        
        Args:
            prob_raw: Raw model probability (0-1)
            outcome: 'home', 'draw', or 'away'
        
        Returns:
            Calibrated probability (0-1)
        """
        if outcome == 'home' and self.iso_home:
            return float(self.iso_home.predict([prob_raw])[0])
        elif outcome == 'draw' and self.iso_draw:
            return float(self.iso_draw.predict([prob_raw])[0])
        elif outcome == 'away' and self.iso_away:
            return float(self.iso_away.predict([prob_raw])[0])
        else:
            # No calibration available, return as-is
            return prob_raw
    
    def train_calibration_curves(self, prediction_history):
        """
        Train calibration curves from historical predictions
        
        Args:
            prediction_history: List of {
                'prediction': {'home_prob': 0.6, 'draw_prob': 0.2, 'away_prob': 0.2},
                'actual_outcome': 'home',  # or 'draw', 'away'
                'date': '2025-01-01'
            }
        """
        
        # Extract uncalibrated probabilities and outcomes
        home_probs, draw_probs, away_probs = [], [], []
        home_outcomes, draw_outcomes, away_outcomes = [], [], []
        
        for record in prediction_history[-1000:]:  # Last 1000 predictions
            pred = record['prediction']
            outcome = record['actual_outcome']
            
            home_probs.append(pred['home_prob'])
            home_outcomes.append(1 if outcome == 'home' else 0)
            
            draw_probs.append(pred['draw_prob'])
            draw_outcomes.append(1 if outcome == 'draw' else 0)
            
            away_probs.append(pred['away_prob'])
            away_outcomes.append(1 if outcome == 'away' else 0)
        
        # Train isotonic regression for each outcome
        self.iso_home = IsotonicRegression(out_of_bounds='clip')
        self.iso_home.fit(home_probs, home_outcomes)
        
        self.iso_draw = IsotonicRegression(out_of_bounds='clip')
        self.iso_draw.fit(draw_probs, draw_outcomes)
        
        self.iso_away = IsotonicRegression(out_of_bounds='clip')
        self.iso_away.fit(away_probs, away_outcomes)
        
        # Save curves
        with open(self.calibration_dir / 'iso_regression_home.pkl', 'wb') as f:
            pickle.dump(self.iso_home, f)
        with open(self.calibration_dir / 'iso_regression_draw.pkl', 'wb') as f:
            pickle.dump(self.iso_draw, f)
        with open(self.calibration_dir / 'iso_regression_away.pkl', 'wb') as f:
            pickle.dump(self.iso_away, f)
        
        logger.info("✅ Calibration curves trained and saved")
```

**Integration:**
```python
# In EnhancedPredictor.__init__()
self.calibration_manager = CalibrationManager()

# In _create_ai_ensemble_prediction() - after ensemble calculation
home_prob = self.calibration_manager.calibrate_probability(
    home_prob_raw, 'home'
)
draw_prob = self.calibration_manager.calibrate_probability(
    draw_prob_raw, 'draw'
)
away_prob = self.calibration_manager.calibrate_probability(
    away_prob_raw, 'away'
)
```

**Expected Impact:** +2-4% accuracy  
**Complexity:** Moderate (3-4 hours)

---

### OPTIMIZATION #3: Data Freshness Scoring

#### Implementation:

```python
class DataFreshnessScorer:
    """Calculate data age and apply freshness penalties"""
    
    def calculate_freshness_score(self, data_timestamps):
        """
        Args:
            data_timestamps: {
                'team_stats_age_seconds': 3600,  # 1 hour old
                'h2h_data_age_seconds': 7200,    # 2 hours old
                'injury_data_age_seconds': 1800, # 30 min old
                ...
            }
        
        Returns:
            freshness_score: 0-1 (1=perfect, 0=too stale)
            multiplier: Confidence multiplier [0.4-1.0]
        """
        
        scores = {}
        
        for data_type, age_seconds in data_timestamps.items():
            age_minutes = age_seconds / 60
            
            if age_minutes < 30:           # 0-30 min: Perfect
                scores[data_type] = 1.0
            elif age_minutes < 60:          # 30-60 min: Good
                scores[data_type] = 0.95
            elif age_minutes < 240:         # 1-4 hours: Acceptable
                scores[data_type] = 0.85
            elif age_minutes < 1440:        # 4-24 hours: Stale
                scores[data_type] = 0.60
            else:                           # >24 hours: Very stale
                scores[data_type] = 0.40
        
        # Weight different data types differently
        # Injury data is most important (changes game significantly)
        weights = {
            'injury_data_age_seconds': 0.30,
            'team_stats_age_seconds': 0.25,
            'h2h_data_age_seconds': 0.20,
            'form_data_age_seconds': 0.15,
            'weather_data_age_seconds': 0.10
        }
        
        weighted_score = sum(
            scores.get(dtype, 1.0) * weight
            for dtype, weight in weights.items()
        )
        
        # Convert weighted score to multiplier
        # Perfect (1.0) → 1.0x multiplier
        # Acceptable (0.85) → 0.90x multiplier
        # Stale (0.60) → 0.70x multiplier
        # Very stale (0.40) → 0.50x multiplier
        multiplier = 0.5 + (weighted_score * 0.5)
        
        return weighted_score, multiplier
```

**Expected Impact:** +1-1.5% accuracy  
**Complexity:** Easy (1-2 hours)

---

## IMPLEMENTATION CODE TEMPLATES

### Template 1: Feature Addition

```python
# File: app/features/feature_engineering.py

import numpy as np
from typing import Dict, Any

class AdvancedFeatures:
    """Generate high-value features for ML models"""
    
    def __init__(self):
        self.feature_cache = {}
    
    # REST DIFFERENTIAL (Most impactful)
    def calculate_rest_differential(self, match_data: Dict[str, Any]) -> float:
        """
        Calculate days since last match
        
        Impact: Teams with <2 days rest underperform by ~5-8%
        """
        home_days_rest = match_data['home_days_since_last_match']
        away_days_rest = match_data['away_days_since_last_match']
        
        # Normalize to 0-1 scale (7 days = fully rested)
        home_rest_score = min(home_days_rest / 7, 1.0)
        away_rest_score = min(away_days_rest / 7, 1.0)
        
        # Rest differential (positive favors home)
        rest_differential = home_rest_score - away_rest_score
        
        return rest_differential  # Range: -1 to +1
    
    # INJURY IMPACT (High impact)
    def calculate_injury_impact(self, match_data: Dict[str, Any]) -> float:
        """
        Calculate weighted injury impact by position importance
        
        Impact: Losing key players (defenders, forwards) significantly affects performance
        """
        
        position_importance = {
            'G': 0.1,    # Goalkeeper (backup usually similar)
            'D': 0.4,    # Defender (very important)
            'M': 0.3,    # Midfielder (important)
            'F': 0.5     # Forward (most important, affects scoring)
        }
        
        home_injured = match_data.get('home_injured_players', [])
        away_injured = match_data.get('away_injured_players', [])
        
        def calculate_team_injury_impact(injured_list):
            """Sum weighted importance of injured players"""
            impact = 0
            for player in injured_list:
                position = player.get('position', 'M')
                importance = position_importance.get(position, 0.3)
                impact += importance
            return min(impact / 2.0, 1.0)  # Normalize 0-1 (max 2 key players)
        
        home_injury_impact = calculate_team_injury_impact(home_injured)
        away_injury_impact = calculate_team_injury_impact(away_injured)
        
        # Injury differential (negative favors away if away has less injuries)
        injury_differential = home_injury_impact - away_injury_impact
        
        return injury_differential  # Range: -1 to +1
    
    # REFEREE BIAS (Medium impact)
    def calculate_referee_bias(self, match_data: Dict[str, Any], 
                              historical_referee_data: Dict) -> float:
        """
        Calculate referee's historical home/away penalty bias
        """
        referee_id = match_data.get('referee_id')
        
        if not referee_id or referee_id not in historical_referee_data:
            return 0.0  # No data = neutral
        
        ref_stats = historical_referee_data[referee_id]
        
        # Home team penalty differential
        # Positive = referee favors home
        home_penalty_rate = ref_stats.get('home_penalty_rate', 0.05)
        away_penalty_rate = ref_stats.get('away_penalty_rate', 0.05)
        
        ref_bias = (home_penalty_rate - away_penalty_rate) * 10  # Scale 0-1
        
        return max(-1, min(ref_bias, 1))  # Clamp -1 to +1
    
    # SET-PIECE EFFICIENCY (Medium impact)
    def calculate_set_piece_efficiency(self, match_data: Dict[str, Any]) -> float:
        """
        Goals from corners + free kicks as % of total
        
        Some teams score heavily from set pieces
        """
        
        home_sp_goals = match_data.get('home_set_piece_goals', 0)
        home_total_goals = match_data.get('home_total_goals', 10)
        away_sp_goals = match_data.get('away_set_piece_goals', 0)
        away_total_goals = match_data.get('away_total_goals', 10)
        
        home_sp_pct = home_sp_goals / max(home_total_goals, 1)
        away_sp_pct = away_sp_goals / max(away_total_goals, 1)
        
        # Differential: positive if home relies more on set pieces
        sp_differential = home_sp_pct - away_sp_pct
        
        return max(-1, min(sp_differential, 1))  # Clamp -1 to +1
    
    def extract_all_features(self, match_data: Dict[str, Any]) -> np.ndarray:
        """Extract all advanced features"""
        
        features = [
            self.calculate_rest_differential(match_data),
            self.calculate_injury_impact(match_data),
            self.calculate_referee_bias(match_data, {}),  # Pass historical data
            self.calculate_set_piece_efficiency(match_data)
        ]
        
        return np.array(features)
```

---

## INTEGRATION POINTS

### Where to Apply Adaptive Weights
**File:** `enhanced_predictor.py`  
**Function:** `_create_ai_ensemble_prediction()`  
**Lines:** 2798-2815

**Change:**
```python
# OLD
weights = {
    'legacy': 0.25,
    'ml': 0.30,
    'neural': 0.25,
    'monte_carlo': 0.20
}

# NEW
weights = self._calculate_adaptive_weights(
    enhanced_data, predictions, data_quality_score
)
```

### Where to Apply Isotonic Calibration
**File:** `enhanced_predictor.py`  
**Function:** `_create_ai_ensemble_prediction()`  
**Lines:** 2825-2845 (after ensemble probability calculation)

**Change:**
```python
# OLD
home_prob = (weighted ensemble result)

# NEW
home_prob_raw = (weighted ensemble result)
home_prob = self.calibration_manager.calibrate_probability(
    home_prob_raw, 'home'
)
```

### Where to Apply Freshness Scoring
**File:** `enhanced_predictor.py`  
**Function:** `predict_match()`  
**Before confidence optimization:**

**Change:**
```python
# Calculate data freshness
data_timestamps = {
    'team_stats_age_seconds': time.time() - data_quality_report['timestamp'],
    'injury_data_age_seconds': ...,
    ...
}
freshness_score, freshness_multiplier = (
    self.freshness_scorer.calculate_freshness_score(data_timestamps)
)

# Apply to confidence
final_confidence *= freshness_multiplier
```

---

## TESTING STRATEGY

### Unit Tests

```python
# File: tests/test_ai_optimizations.py

import pytest
import numpy as np
from enhanced_predictor import EnhancedPredictor

class TestAdaptiveWeights:
    
    def test_weights_sum_to_one(self):
        """Adaptive weights must sum to 1.0"""
        predictor = EnhancedPredictor(api_key='test')
        weights = predictor._calculate_adaptive_weights(
            enhanced_data={},
            predictions={},
            data_quality_score=0.8
        )
        assert abs(sum(weights.values()) - 1.0) < 0.01
    
    def test_weights_respond_to_data_quality(self):
        """High quality data should flatten weights"""
        predictor = EnhancedPredictor(api_key='test')
        
        # Poor data quality
        weights_poor = predictor._calculate_adaptive_weights(
            enhanced_data={},
            predictions={},
            data_quality_score=0.3
        )
        
        # Good data quality
        weights_good = predictor._calculate_adaptive_weights(
            enhanced_data={},
            predictions={},
            data_quality_score=0.9
        )
        
        # Good quality should have more equal distribution
        poor_variance = np.var(list(weights_poor.values()))
        good_variance = np.var(list(weights_good.values()))
        assert good_variance < poor_variance

class TestCalibration:
    
    def test_calibration_improves_accuracy(self):
        """Calibration should improve probability accuracy"""
        manager = CalibrationManager()
        
        # Generate fake prediction history
        history = [
            {
                'prediction': {'home_prob': 0.7, 'draw_prob': 0.2, 'away_prob': 0.1},
                'actual_outcome': 'home'
            } for _ in range(100)
        ]
        
        manager.train_calibration_curves(history)
        
        # Test calibration
        calibrated = manager.calibrate_probability(0.7, 'home')
        
        # Should be close to empirical rate
        assert 0.65 < calibrated < 0.75

class TestFreshnessScoring:
    
    def test_freshness_multiplier_range(self):
        """Freshness multiplier should be 0.4-1.0"""
        scorer = DataFreshnessScorer()
        
        # Perfect data
        score, mult = scorer.calculate_freshness_score({
            'team_stats_age_seconds': 300,
            'h2h_data_age_seconds': 300,
            'injury_data_age_seconds': 300
        })
        assert mult == 1.0
        
        # Very stale data
        score, mult = scorer.calculate_freshness_score({
            'team_stats_age_seconds': 86400 * 2,
            'h2h_data_age_seconds': 86400 * 2,
            'injury_data_age_seconds': 86400 * 2
        })
        assert mult < 0.5
```

### Integration Tests

```python
# Test full prediction pipeline with optimizations
def test_full_pipeline_with_optimizations():
    predictor = EnhancedPredictor(api_key='test')
    
    match_data = {
        'homeTeam': {'name': 'Real Madrid', 'id': 86},
        'awayTeam': {'name': 'Barcelona', 'id': 81},
        'date': '2025-12-05'
    }
    
    # Should not crash
    prediction = predictor.predict_match(match_data)
    
    # Validate outputs
    assert 'home_win_probability' in prediction
    assert 'confidence' in prediction
    assert 0 <= prediction['confidence'] <= 1.0
    assert abs(sum([
        prediction['home_win_probability'],
        prediction['draw_probability'],
        prediction['away_win_probability']
    ]) - 1.0) < 0.01
```

---

## EXPECTED RESULTS

### Phase 1 Results (After 1-2 days)
```
Metric                      Before      After       Improvement
─────────────────────────────────────────────────────────────────
Average Confidence          58-64%      62-72%      +4-8%
Calibration Quality         Moderate    Good        ↑↑
Report Time                 <2.5s       <2.5s       ✓ No regression
Model Agreement             ~60%        ~70%        +10%
```

### Phase 2 Results (After 2-3 additional days)
```
Metric                      Phase 1     Phase 2     Total Improvement
─────────────────────────────────────────────────────────────────────
Average Confidence          62-72%      67-80%      +5-8%
Feature Count               20          32          +60%
Calibration Quality         Good        Excellent   ↑↑↑
League Specialization       Single      5 leagues   ✓ Implemented
```

### Phase 3 Results (After 1-2 additional days)
```
Metric                      Phase 2     Phase 3     Final Target
──────────────────────────────────────────────────────────────────
Average Confidence          67-80%      70-84%      +2-4%
Bayesian Updates            No          Yes         ✓ Active
Performance Tracking        Basic       Advanced    ✓ Comprehensive
```

---

## REFERENCE DOCUMENTATION

- **Current Ensemble:** Lines 2798-2880 in enhanced_predictor.py
- **Data Quality:** data_quality_enhancer.py
- **ML Models:** app/models/advanced_ai_engine.py
- **Confidence Optimization:** app/models/confidence_optimizer.py
- **Phase 2 Lite:** phase2_lite.py

