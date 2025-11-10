#!/usr/bin/env python3
"""Generate Serie A match quickly"""
from generate_clean_reports import CleanReportGenerator

generator = CleanReportGenerator()
result = generator.generate_match_report("serie_a")
print("✅ Serie A match generated successfully!")
