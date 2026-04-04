#!/usr/bin/env python3
"""Add manual result for Tottenham match, collect reports into historical file, then run full optimizer."""

import subprocess
import sys

from scripts.collect_historical_results import HistoricalResultsCollector

collector = HistoricalResultsCollector()
# Ensure historical files exist
collector.ensure_historical_files(["premier-league"])
# Collect predictions from reports directory
results = collector.collect_from_reports("premier-league")
count = collector.save_historical_data("premier-league", results)
print(f"Saved {count} prediction records to historical file")

# Update the Tottenham result (home=Tottenham 1, away=Liverpool 2)
match_id = "tottenham-hotspur-football-club_vs_liverpool-football-club_2025-12-20"
updated = collector.update_actual_results(
    "premier-league", match_id, 1, 2, provider_name="manual",
)
print(f"Updated actual result for {match_id}: {updated}")

# Show a small excerpt of the historical file
hist_file = collector.historical_dir / "premier-league_results.json"
print("Historical file:", hist_file)
print(hist_file.read_text()[:2000])

# Re-run full optimizer for premier-league
print("Running optimizer (full) for premier-league...")
subprocess.run(
    [
        sys.executable,
        "scripts/optimize_accuracy.py",
        "--mode",
        "full",
        "--league",
        "premier-league",
    ],
    check=False,
)
print("Done")
