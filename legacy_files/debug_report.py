#!/usr/bin/env python3
import json
import os

# Test if the report generation functions are working
print("🔍 Checking report generation...")

# Check if the JSON was created and read it
json_path = "reports/leagues/bundesliga/matches/1.-FC-Union-Berlin_vs_Borussia-Mönchengladbach_2025-10-17/prediction.json"

if os.path.exists(json_path):
    print("✅ JSON file exists")
    with open(json_path, 'r', encoding='utf-8') as f:
        match_data = json.load(f)
    print(f"✅ JSON contains {len(match_data)} fields")
    print(f"   Expected Score: {match_data.get('expected_final_score')}")
    print(f"   Score Probability: {match_data.get('score_probability')}%")
    print(f"   Over 2.5 Goals: {match_data.get('over_2_5_goals_probability')}%")
    print(f"   Both Teams Score: {match_data.get('both_teams_score_probability')}%")
else:
    print("❌ JSON file not found")

# Check for other files
base_path = "reports/leagues/bundesliga/matches/1.-FC-Union-Berlin_vs_Borussia-Mönchengladbach_2025-10-17"
summary_path = f"{base_path}/summary.md"
png_path = f"{base_path}/prediction_card.png"

print(f"\n📄 Summary file exists: {os.path.exists(summary_path)}")
print(f"🖼️ PNG file exists: {os.path.exists(png_path)}")

if os.path.exists(base_path):
    files = os.listdir(base_path)
    print(f"📁 Files in directory: {files}")
