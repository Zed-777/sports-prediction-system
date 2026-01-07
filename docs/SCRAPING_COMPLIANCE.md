# Scraping & Data Collection Compliance Checklist

This short checklist documents legal and ethical considerations for scraping and collecting third-party sports data. Use it as a starting point and consult legal counsel for production use.

1. Check site Terms of Service (ToS) before scraping
   - Do not scrape sites that explicitly forbid automated access.
   - Prefer official APIs (with permission/contract) when available.

2. Respect robots.txt and rate limits
   - Read and follow robots.txt for each host.
   - Use polite scraping: obey crawl-delay, and set conservative request rates.
   - Use `app/utils/http.safe_request_get` and per-host throttle configuration in `config/settings.yaml`.

3. Avoid heavy or real-time scraping at scale
   - For high-volume needs, negotiate a commercial API or data partnership.
   - Cache responses and use snapshots (`data/cache/`) to minimize repeated requests.

4. Attribution & provenance
   - Record source, URL, and timestamp for all scraped items (reports should include `provenance`).
   - Keep raw HTML/JSON debug dumps under `reports/debug/` or `data/cache/` for auditing.

5. Personal data & privacy
   - Avoid collecting or persisting personally sensitive information not required for predictions.
   - When storing social posts, store only relevant fields, and respect platform reuse policies.

6. Social media (Twitter/X, etc.)
   - Use official APIs when possible and follow platform developer policies.
   - For scraping public posts, record author, timestamp, and include disclaimer for rumor-based data.

7. Rate-limiting & error handling
   - Implement retries with exponential backoff and exponential backoff on 429 responses.
   - Persist temporary disable flags (see `data_quality_enhancer._injuries_disabled_until`) to avoid repeated rate-limits.

8. Team / Club site scraping
   - Prefer official press/RSS feeds for lineup & injury confirmations.
   - For content behind login or paywall, do not scrape; seek permission or licensed feeds.

9. Recording provenance and confidence
   - Every fallback data source must include `provenance` and a `confidence` score.
   - In tests and reports, document when fallbacks were used.

10. Review & approval
    - Add a short compliance note to PRs that add new scrapers.
    - Maintain a list of allowed sources and a short legal rationale in `docs/`.

If you want, I can add a short script to automatically fetch and validate robots.txt for a list of hosts (FlashScore, SofaScore, Transfermarkt, club sites). Tell me which hosts to include and I will add it.