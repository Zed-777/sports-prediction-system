# Bug Report: Expected Score vs xG Alignment

## Issue

Expected score prediction sometimes contradicts xG-derived outcome probabilities.

### Example (Real Oviedo vs RCD Mallorca 2025-12-05)

- **Expected Home Goals**: 0.9
- **Expected Away Goals**: 1.1
- **Home Win Probability**: 38.5% (implied by form + team strength)
- **Away Win Probability**: 28.5%
- **Recommendation**: "Competitive (Home Edge)"
- **Expected Score**: **0-1** (15.7%) ← Implies AWAY win ⚠️

## Root Cause

The Poisson-based score calculation is **mathematically correct** given the xG values (0.9 vs 1.1).

However:

1. xG difference of only 0.2 goals is **marginal** (~2% swing in probability space)
2. Win probabilities are calculated **separately** using form, H2H, and strategic factors
3. When xG values are close (within ±0.3), Poisson produces highly distributed probabilities
4. The "most likely score" (0-1) has only 15.7% probability - barely higher than 0-0 (14.8%) and 1-1 (13.3%)

## Impact Severity

**MODERATE** - The score IS statistically valid, but:

- Confuses users (contradicts narrative)
- May mislead betting decisions
- Technically correct but pedagogically poor

## Fix Options

### Option A: Score Selection Alignment (Recommended)

Implemented in current code - select score that matches outcome probabilities when xG is marginal.

**Status**: Attempted (lines 1268-1305 in enhanced_predictor.py)
**Issue**: Threshold (0.3 goal difference) too high for 0.2 gap

**Improved threshold**: Change to 0.15 goal difference

### Option B: Pass Win Probabilities to Score Calculator

Refactor `calculate_expected_score()` to accept pre-calculated win probabilities and bias score selection toward matching outcomes.

**Pros**: Most accurate
**Cons**: Requires function signature change, may impact other callers

### Option C: Document as Known Limitation

Add caveat to reports when xG difference < 0.3 and score contradicts recommendation.

**Pros**: Transparent, minimal code change
**Cons**: Doesn't fix the problem, just documents it

## Recommendation

**Implement Option A with lower threshold (0.15)**

```python
# Current (line 1278):
if xg_diff > 0.3 and home_score < away_score:

# Proposed:
if xg_diff > 0.15 and home_score < away_score:
```

This will catch marginal xG differences and align score with win probability outcomes.

## Verification Steps

1. Generate report for match with marginal xG difference
2. Check if expected score now matches outcome recommendation
3. Verify top 3 alternatives still include original Poisson top selection
4. Test with multiple leagues to ensure no regression

## Files Affected

- `enhanced_predictor.py` (calculate_expected_score method, lines 1268-1305)
- `generate_fast_reports.py` (score selection and reporting)

## Test Case

```
Match: Real Oviedo (xG 0.9) vs RCD Mallorca (xG 1.1)
Expected: Score should reflect "Home Edge" recommendation
Example: 1-0 or 1-1 instead of 0-1
Current: 0-1 (misaligned)
```
