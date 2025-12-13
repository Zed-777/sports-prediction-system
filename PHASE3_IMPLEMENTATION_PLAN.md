# Phase 3 Implementation Plan - League Tuning & Bayesian Updates

## Overview

Phase 3 is the final optimization tier designed to add +2-4% confidence accuracy improvement through:

- League-specific model calibration and weighting
- Bayesian continuous learning from match outcomes
- Context-aware adjustments (home/away, season phase, venue)

**Target System Confidence:** 70-84% (total +12-20% improvement)

---

## Phase 3.1: League-Specific Tuning

### LeagueTuner Architecture

**LeagueTuner Class** (`app/models/league_tuner.py`)

```python
class LeagueTuner:
    """Manages league-specific model tuning and calibration"""
    
    def __init__(self, leagues: List[str]):
        # Separate calibration managers per league
        self.league_calibrators = {league: CalibrationManager() for league in leagues}
        
        # Separate performance trackers per league
        self.league_trackers = {league: ModelPerformanceTracker() for league in leagues}
        
        # League characteristics
        self.league_characteristics = {
            'la-liga': {'pacing': 'moderate', 'defense': 'strong', 'goals': 2.4},
            'premier-league': {'pacing': 'fast', 'defense': 'moderate', 'goals': 2.8},
            'bundesliga': {'pacing': 'very_fast', 'defense': 'weak', 'goals': 3.1},
            'serie-a': {'pacing': 'slow', 'defense': 'very_strong', 'goals': 2.3},
            'ligue-1': {'pacing': 'moderate', 'defense': 'moderate', 'goals': 2.6}
        }
    
    def get_league_calibrator(self, league: str) -> CalibrationManager:
        """Get calibration manager for specific league"""
        return self.league_calibrators.get(league)
    
    def get_league_weights(self, league: str) -> Dict[str, float]:
        """Get dynamic weights for league"""
        tracker = self.league_trackers.get(league)
        if tracker:
            return tracker.calculate_dynamic_weights()
        return {}
    
    def record_league_match(self, league: str, prediction: float, outcome: float):
        """Record match outcome for league-specific learning"""
        cal = self.get_league_calibrator(league)
        if cal:
            cal.add_calibration_sample(prediction, outcome)
    
    def apply_league_adjustment(self, league: str, confidence: float) -> float:
        """Apply league-specific confidence adjustment"""
        char = self.league_characteristics.get(league, {})
        
        # Goals per game adjustment
        goals = char.get('goals', 2.6)
        if goals > 2.8:  # High-scoring league (Bundesliga)
            confidence *= 0.95  # Slightly lower confidence in high-variance league
        elif goals < 2.4:  # Low-scoring league (Serie A, La Liga)
            confidence *= 1.05  # Slightly higher confidence in predictable league
        
        return min(1.0, confidence)
```

### LeagueTuner Key Features

1. **Per-League Calibration**
   - Separate isotonic regression per league
   - Captures league-specific probability distributions
   - Adapts to rule changes or structural differences

2. **Performance Adaptation**
   - Track model accuracy per league
   - Adjust ensemble weights by league
   - Identify models that perform better in specific leagues

3. **Characteristic-Based Adjustment**
   - Pacing factors (fast vs slow play)
   - Defensive strength (affects goal frequency)
   - Goal frequency (affects prediction variance)

### LeagueTuner Integration Points

In `ai_enhanced_prediction()`:

```python
league = extract_league(match_data)
league_cal = self.league_tuner.get_league_calibrator(league)
if league_cal:
    confidence = league_cal.calibrate_probability(confidence)
confidence = self.league_tuner.apply_league_adjustment(league, confidence)
```

---

## Phase 3.2: Bayesian Update System

### Architecture

**BayesianUpdater Class** (`app/models/bayesian_updater.py`)

```python
class BayesianUpdater:
    """Maintains Bayesian posterior for confidence prediction"""
    
    def __init__(self, prior_alpha: float = 2.0, prior_beta: float = 2.0):
        self.prior_alpha = prior_alpha  # Beta distribution shape
        self.prior_beta = prior_beta
        
        # Posterior parameters (updated with outcomes)
        self.posterior_alpha = prior_alpha
        self.posterior_beta = prior_beta
        
        # Match history for learning
        self.match_history = []
    
    def record_match(self, confidence: float, home_won: bool):
        """Update posterior with match outcome"""
        # If confidence was high and team won (or low and team lost), strengthen posterior
        if (confidence > 0.5 and home_won) or (confidence <= 0.5 and not home_won):
            self.posterior_alpha += 1  # Successful prediction
        else:
            self.posterior_beta += 1  # Unsuccessful prediction
        
        self.match_history.append({
            'confidence': confidence,
            'outcome': home_won,
            'posterior_mean': self.get_posterior_mean()
        })
    
    def get_posterior_mean(self) -> float:
        """Get current posterior mean estimate"""
        total = self.posterior_alpha + self.posterior_beta
        return self.posterior_alpha / total if total > 0 else 0.5
    
    def get_posterior_std(self) -> float:
        """Get posterior standard deviation (uncertainty)"""
        alpha = self.posterior_alpha
        beta = self.posterior_beta
        total = alpha + beta
        variance = (alpha * beta) / (total ** 2 * (total + 1))
        return variance ** 0.5
    
    def adjust_confidence(self, raw_confidence: float) -> float:
        """Adjust confidence toward posterior mean"""
        posterior_mean = self.get_posterior_mean()
        posterior_std = self.get_posterior_std()
        
        # Blend with posterior (more blending with low uncertainty)
        blend_factor = min(0.3, posterior_std)
        adjusted = (raw_confidence * (1 - blend_factor)) + (posterior_mean * blend_factor)
        
        return adjusted
```

### Key Features

1. **Continuous Learning**
   - Beta-Binomial conjugate prior model
   - Updates with each match outcome
   - Learns true calibration curve

2. **Uncertainty Tracking**
   - Posterior standard deviation
   - Confidence intervals for predictions
   - Adjusts blending based on confidence

3. **Automatic Reversion**
   - When model is miscalibrated, posterior drifts
   - Predictions automatically shift toward empirical accuracy
   - Self-correcting without manual intervention

### BayesianUpdater Integration Points

In `_save_calibration_history()`:

```python
if hasattr(self, 'bayesian_updater'):
    self.bayesian_updater.save_state(filepath)
```

After match completion (external update):

```python
self.bayesian_updater.record_match(prediction_confidence, home_team_won)
```

---

## Phase 3.3: Context-Aware Weighting

### ContextExtractor Architecture

#### Home/Away Effects

```python
def get_home_away_adjustment(self, context: MatchContext) -> float:
    if context.is_home_team:
        return 1.05 + (context.home_advantage_factor * 0.02)
    else:
        return 0.95 - (context.away_penalty_factor * 0.02)
```

#### Season Phase Effects

```python
def get_season_phase_adjustment(self, weeks_into_season: int) -> float:
    if weeks_into_season < 5:
        return 0.92  # High volatility in early season
    elif weeks_into_season > 30:
        return 1.08  # More predictable near end of season
    else:
        return 1.00  # Normal mid-season
```

#### Competition Level

```python
def get_competition_adjustment(self, league: str, is_cup: bool) -> float:
    if is_cup:
        return 0.85  # Cup matches less predictable
    
    league_strengths = {
        'premier-league': 1.02,
        'la-liga': 1.00,
        'bundesliga': 0.98,
        'serie-a': 0.99,
        'ligue-1': 0.97
    }
    return league_strengths.get(league, 1.00)
```

#### Venue Performance

```python
def get_venue_adjustment(self, team: str, venue: str) -> float:
    # Track team performance at specific stadium
    venue_stats = self.venue_performance.get(f"{team}_{venue}", {})
    if venue_stats.get('matches', 0) >= 5:
        win_rate = venue_stats.get('win_rate', 0.5)
        return 0.95 + (win_rate * 0.10)  # Up to 1.05x
    return 1.00
```

### ContextExtractor Aggregation

```python
def get_total_context_adjustment(self, match_context: MatchContext) -> float:
    adjustments = [
        self.get_home_away_adjustment(match_context),
        self.get_season_phase_adjustment(match_context.weeks_into_season),
        self.get_competition_adjustment(match_context.league, match_context.is_cup),
        self.get_venue_adjustment(match_context.home_team, match_context.venue)
    ]
    
    # Geometric mean (multiplicative combination)
    result = 1.0
    for adj in adjustments:
        result *= adj
    return result ** (1/len(adjustments))  # Normalize
```

---

## Expected Performance Gains

| Component | Improvement | Implementation Complexity |
|-----------|-------------|--------------------------|
| League Tuning | +1-2% | Low |
| Bayesian Updates | +0.5-1% | Medium |
| Context Weighting | +0.5-1% | Medium |
| **Total Phase 3** | **+2-4%** | **Medium** |

**Final System Confidence:** 70-84% (from baseline 58-64%)

---

## Implementation Sequence

### Step 1: League Tuning (2-3 hours)

- [ ] Create `LeagueTuner` class
- [ ] Integrate with `EnhancedPredictor`
- [ ] Test per-league calibration
- [ ] Verify no regressions

### Step 2: Bayesian Updates (2-3 hours)

- [ ] Create `BayesianUpdater` class
- [ ] Implement Beta-Binomial model
- [ ] Integrate confidence adjustment
- [ ] Test with historical data

### Step 3: Context Weighting (2-3 hours)

- [ ] Create context extraction utility
- [ ] Implement all 4 adjustment types
- [ ] Integrate into prediction pipeline
- [ ] Validate adjustment ranges

### Step 4: Testing (2-3 hours)

- [ ] Create Phase 3 test suite
- [ ] Run regression tests on Phase 1 & 2
- [ ] Validate accuracy improvements
- [ ] Benchmark system performance

**Total Implementation Time:** 8-12 hours
**Total Test Coverage:** 15+ new tests

---

## Test Suite Structure (test_phase3_league_bayesian.py)

```python
def test_league_tuner():
    """Test per-league calibration"""
    # Verify separate calibration per league
    # Check league-specific adjustments
    
def test_bayesian_updater():
    """Test Bayesian confidence adjustment"""
    # Record match outcomes
    # Check posterior updates
    # Verify confidence drift
    
def test_context_weighting():
    """Test context-aware adjustments"""
    # Verify home/away effects
    # Check season phase adjustments
    # Validate venue performance
    
def test_phase3_integration():
    """End-to-end Phase 3 test"""
    # Generate prediction with all Phase 3 components
    # Verify improvements
    # Check stability with Phase 1 & 2
```

---

## Success Criteria

✓ Phase 3 implementation complete when:

- **League Tuning:** Per-league calibration working, accuracy +1-2%
- **Bayesian Updates:** Posterior tracking operational, self-corrects predictions
- **Context Weighting:** All 4 adjustments implemented and tested
- **Testing:** All tests passing, no regressions to Phase 1 & 2
- **Performance:** System confidence reaches 70-84% target range

---

## Files to Create

1. `app/models/league_tuner.py` (~200 lines)
2. `app/models/bayesian_updater.py` (~250 lines)
3. `app/utils/context_extractor.py` (~100 lines)
4. `test_phase3_league_bayesian.py` (~400 lines)

**Total New Code:** ~950 lines

---

## Next Steps

1. Start Phase 3.1 (League Tuning)
2. Mark todo items as in-progress one by one
3. Complete integration tests
4. Measure final confidence improvement
5. Verify production readiness

**Ready to proceed with Phase 3? [Y/N]**
