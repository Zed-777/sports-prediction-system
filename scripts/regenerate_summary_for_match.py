#!/usr/bin/env python3
"""Regenerate summary and images for an existing prediction.json
Usage: python scripts/regenerate_summary_for_match.py <path/to/prediction.json>
"""

import json
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from generate_fast_reports import SingleMatchGenerator

if len(sys.argv) < 2:
    print(
        "Usage: python scripts/regenerate_summary_for_match.py <path/to/prediction.json>",
    )
    sys.exit(2)

p = Path(sys.argv[1])
if not p.exists():
    print("File not found:", p)
    sys.exit(2)

with open(p, encoding="utf-8") as f:
    data = json.load(f)

# Directory containing prediction.json
full_path = str(p.parent)

gen = SingleMatchGenerator()
# Regenerate summary and image by default; use --skip-image to only regenerate markdown
skip_image = "--skip-image" in sys.argv
try:
    gen.save_summary(data, full_path)
    print("Summary regenerated successfully at", full_path)
except Exception as e:
    print("Failed to regenerate summary:", e)

if not skip_image:
    try:
        gen.save_image(data, full_path)
        print("Image regenerated successfully at", full_path)
    except Exception as e:
        print("Failed to regenerate image:", e)

# Update format copies (markdown, json, image) to formats directory
try:
    gen.save_format_copies(data, p.parent.name)
    print("Format copies updated")
except Exception as e:
    print("Failed to update format copies:", e)
