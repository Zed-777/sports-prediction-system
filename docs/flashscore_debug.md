# FlashScore Debugging

When `scripts/run_historical_backfill.py` or `scripts/collect_historical_results.py` is run with `--debug`, the `FlashScoreScraper` will save raw responses to:

```
reports/debug/flashscore/
```

Each file is named like `www_flashscore_es_futbol_inglaterra_premier-league__attempt1_<ts>.html` and represents a single fetch attempt. Use `scripts/debug_flashscore_inspect.py --dir reports/debug/flashscore` to summarize file types and detect common patterns (HTML, script payloads, compressed payloads).

Common troubleshooting steps:

- If files are classified as `other`, inspect a sample file to see whether they contain obfuscated JavaScript or compressed payloads (brotli/zlib). The repository includes a small heuristic that tries to decompress brotli/zlib payloads before extracting match data.
- If files appear to be an anti-bot/consent page, consider using official APIs (Football-Data.org or API-Football) by setting `FOOTBALL_DATA_API_KEY` and/or `API_FOOTBALL_KEY` in your environment or `.env`.
- To run an end-to-end backfill with API updates (preferred when keys are available):

  ```bash
  python scripts/run_historical_backfill.py --leagues premier-league --days 365 --execute --commit
  ```

- If you need help analyzing the debug files, run `scripts/debug_flashscore_inspect.py` and share the `reports/metrics/flashscore_debug_summary.json` output.
