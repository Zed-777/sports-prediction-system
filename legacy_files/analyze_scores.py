#!/usr/bin/env python3
import math


def poisson_prob(k, lam):
    """Calculate Poisson probability"""
    return (lam ** k * math.exp(-lam)) / math.factorial(k)

# Test with actual values from the match
home_expected = 1.6
away_expected = 2.2

print("🔍 Analyzing Score Probabilities")
print("=" * 40)
print(f"Expected Goals: {home_expected} - {away_expected}")
print()

# Calculate all combinations 0-5 goals
all_scores = []
for h in range(6):
    for a in range(6):
        prob = poisson_prob(h, home_expected) * poisson_prob(a, away_expected)
        all_scores.append(((h, a), prob))

# Sort by probability
all_scores.sort(key=lambda x: x[1], reverse=True)

print("Top 10 Most Likely Scores:")
print("-" * 30)
for i, ((h, a), prob) in enumerate(all_scores[:10]):
    print(f"{i+1:2d}. {h}-{a}: {prob*100:.1f}%")

print()
print("Current system only checks 0-3 goals:")
current_scores = []
for h in range(4):
    for a in range(4):
        prob = poisson_prob(h, home_expected) * poisson_prob(a, away_expected)
        current_scores.append(((h, a), prob))

current_scores.sort(key=lambda x: x[1], reverse=True)
print(f"Most likely in 0-3 range: {current_scores[0][0][0]}-{current_scores[0][0][1]} ({current_scores[0][1]*100:.1f}%)")

print()
print("📊 Analysis:")
total_prob_0_3 = sum([prob for _, prob in current_scores])
print(f"Total probability covered by 0-3 goals: {total_prob_0_3*100:.1f}%")

total_prob_all = sum([prob for _, prob in all_scores])
print(f"Total probability of all outcomes: {total_prob_all*100:.1f}%")
