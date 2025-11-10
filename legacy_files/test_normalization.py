#!/usr/bin/env python3
"""Test the normalization scale to show how percentages map to 1-10 scale"""

def normalize_probability_to_10_scale(probability_percent: float) -> float:
    """Convert probability percentage to 1-10 scale"""
    if probability_percent <= 1:
        return 1.0
    elif probability_percent <= 3:
        return 2.0
    elif probability_percent <= 5:
        return 3.0
    elif probability_percent <= 7:
        return 4.0
    elif probability_percent <= 9:
        return 5.0
    elif probability_percent <= 11:
        return 6.0
    elif probability_percent <= 13:
        return 7.0
    elif probability_percent <= 16:
        return 8.0
    elif probability_percent <= 20:
        return 9.0
    else:
        return 10.0

print("🎯 Probability Normalization Scale")
print("=" * 40)
print("Raw %  →  1-10 Scale  →  Meaning")
print("-" * 40)

test_values = [2.5, 4.1, 6.8, 8.6, 10.2, 12.4, 14.7, 17.3, 22.1, 33.0]

for prob in test_values:
    norm = normalize_probability_to_10_scale(prob)
    if norm <= 2:
        meaning = "Very Unlikely"
    elif norm <= 4:
        meaning = "Unlikely"
    elif norm <= 6:
        meaning = "Possible"
    elif norm <= 8:
        meaning = "Likely"
    else:
        meaning = "Very Likely"

    print(f"{prob:4.1f}%  →  ⭐{norm:.0f}/10       →  {meaning}")

print()
print("📊 Current Match Example:")
print("- Expected Score: 1-1 (12.4%) → ⭐7/10 (Likely)")
print("- Top 3 Combined: (33.0%) → ⭐10/10 (Very Likely)")
print()
print("✅ Much easier to understand than raw percentages!")
