#!/usr/bin/env python3
"""
Historical Results Collector
=============================

Collects completed match results to build a historical dataset
for real backtesting and accuracy measurement.

This should be run periodically (e.g., daily) to build up
a dataset of predictions vs actual outcomes.

Usage:
    python scripts/collect_historical_results.py --league la-liga
    python scripts/collect_historical_results.py --all-leagues
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import argparse
import os

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HistoricalResultsCollector:
    """Collects and stores historical match results for backtesting"""

    SUPPORTED_LEAGUES = [
        "la-liga",
        "premier-league",
        "serie-a",
        "bundesliga",
        "ligue-1",
    ]

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.historical_dir = PROJECT_ROOT / "data" / "historical"
        self.historical_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir = PROJECT_ROOT / "reports" / "leagues"

    def detect_report_leagues(self) -> List[str]:
        """Detect league directories under reports/leagues and return their names"""
        if not self.reports_dir.exists():
            return []
        leagues = [p.name for p in self.reports_dir.iterdir() if p.is_dir()]
        return leagues

    def ensure_historical_files(
        self, leagues: Optional[List[str]] = None, use_detected: bool = True
    ) -> List[str]:
        """Create empty historical JSON files for the supplied leagues (or detected/supported leagues).

        Returns a list of created file paths (strings).
        """
        if leagues is None:
            detected = self.detect_report_leagues() if use_detected else []
            leagues = detected if detected else self.SUPPORTED_LEAGUES

        created = []
        for league in leagues:
            out = self.historical_dir / f"{league}_results.json"
            if not out.exists():
                try:
                    with open(out, "w", encoding="utf-8") as f:
                        json.dump([], f, indent=2)
                    created.append(str(out))
                except Exception as e:
                    logger.warning(f"Could not create {out}: {e}")
        logger.info(
            f"Initialized historical files for leagues: {', '.join(leagues)} (created {len(created)} files)"
        )
        return created

    def collect_from_reports(self, league: str) -> List[Dict[str, Any]]:
        """
        Collect predictions from generated reports and match them with results

        This creates training data by pairing our predictions with actual outcomes.
        """
        league_dir = self.reports_dir / league / "matches"
        if not league_dir.exists():
            logger.warning(f"No reports found for {league}")
            return []

        results = []

        for match_dir in league_dir.iterdir():
            if not match_dir.is_dir():
                continue

            prediction_file = match_dir / "prediction.json"
            if not prediction_file.exists():
                continue

            try:
                with open(prediction_file, "r", encoding="utf-8") as f:
                    prediction = json.load(f)

                # Check if match has completed (we need actual results)
                # Support 'match_date' or separate 'date' + 'time' fields used in reports
                match_date_str = prediction.get("match_date") or None
                if not match_date_str and prediction.get("date"):
                    dt = prediction.get("date")
                    t = prediction.get("time")
                    if t:
                        match_date_str = f"{dt}T{t}"
                    else:
                        match_date_str = dt

                if match_date_str:
                    try:
                        match_date = datetime.fromisoformat(
                            match_date_str.replace("Z", "+00:00")
                        )
                        if match_date > datetime.now(match_date.tzinfo):
                            # Match hasn't happened yet
                            continue
                    except Exception:
                        # If parse fails, continue and collect anyway
                        pass

                # Extract probabilities robustly (handle different key names)
                def _get_prob(short_key: str, long_key: str):
                    if short_key in prediction:
                        return prediction[short_key]
                    if long_key in prediction:
                        return prediction[long_key]
                    return prediction.get(short_key, prediction.get(long_key, 0))

                home_p = _get_prob("home_win_prob", "home_win_probability")
                draw_p = _get_prob("draw_prob", "draw_probability")
                away_p = _get_prob("away_win_prob", "away_win_probability")

                # Compute predicted outcome if recommendation not present
                reco = prediction.get("recommendation") or ""
                if not reco:
                    try:
                        hp = float(home_p)
                        dp = float(draw_p)
                        ap = float(away_p)
                        if hp > dp and hp > ap:
                            reco = "home_win"
                        elif dp > ap:
                            reco = "draw"
                        else:
                            reco = "away_win"
                    except Exception:
                        reco = ""

                # Extract relevant data
                result_entry = {
                    "match_id": match_dir.name,
                    "league": league,
                    "home_team": prediction.get("home_team", ""),
                    "away_team": prediction.get("away_team", ""),
                    "match_date": match_date_str,
                    "prediction": {
                        "home_win_prob": home_p,
                        "draw_prob": draw_p,
                        "away_win_prob": away_p,
                        "predicted_outcome": reco,
                        "confidence": prediction.get("confidence", 0),
                        "expected_home_goals": prediction.get("expected_home_goals", 0),
                        "expected_away_goals": prediction.get("expected_away_goals", 0),
                    },
                    "actual_result": None,  # To be filled when result is known
                    "parameters_used": {
                        "market_blend_weight": prediction.get(
                            "phase_enhancements", {}
                        ).get("market_blend_weight", 0.18),
                    },
                    "collected_at": datetime.now().isoformat(),
                }

                results.append(result_entry)

            except Exception as e:
                logger.error(f"Error processing {prediction_file}: {e}")
                continue

        return results

    def save_historical_data(self, league: str, results: List[Dict[str, Any]]):
        """Save or update historical results file"""
        output_file = self.historical_dir / f"{league}_results.json"

        # Load existing data
        existing = []
        if output_file.exists():
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except:
                existing = []

        # Merge, avoiding duplicates and ensure 'league' is set
        existing_ids = {r["match_id"] for r in existing}
        for result in results:
            # Ensure 'league' field is present for downstream use
            if "league" not in result or not result.get("league"):
                result["league"] = league
            if result["match_id"] not in existing_ids:
                existing.append(result)
                existing_ids.add(result["match_id"])
            else:
                # Merge new prediction info into existing record but preserve actual_result and provider metadata
                for i, r in enumerate(existing):
                    if r.get("match_id") == result.get("match_id"):
                        preserved = {
                            k: r.get(k)
                            for k in (
                                "actual_result",
                                "provider_ids",
                                "prediction_correct",
                                "exact_score_correct",
                                "score_in_top3",
                            )
                            if r.get(k) is not None
                        }
                        existing[i] = result
                        existing[i].update(preserved)
                        break

        # Sort by date
        existing.sort(key=lambda x: x.get("match_date", ""), reverse=True)

        # Save
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)

        logger.info(f"Saved {len(existing)} records to {output_file}")
        return len(existing)

    def update_actual_results(
        self,
        league: Optional[str],
        match_id: str,
        home_score: int,
        away_score: int,
        provider_id: Optional[Any] = None,
        provider_name: Optional[str] = None,
    ) -> bool:
        """
        Update a historical record with actual match result. If league is None or the
        historical file is missing, search across all available historical files.

        Args:
            league: League name or None to search all leagues
            match_id: Match identifier
            home_score: Actual home goals
            away_score: Actual away goals

        Returns:
            True if updated successfully
        """
        candidates = []
        if league:
            candidates = [self.historical_dir / f"{league}_results.json"]
        else:
            # Search all historical files
            candidates = list(self.historical_dir.glob("*_results.json"))

        for output_file in candidates:
            if not output_file.exists():
                continue
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            # Find and update
            updated = False
            for record in data:
                if record.get("match_id") != match_id:
                    continue

                # Determine actual outcome
                if home_score > away_score:
                    outcome = "home_win"
                elif away_score > home_score:
                    outcome = "away_win"
                else:
                    outcome = "draw"

                record["actual_result"] = {
                    "home_score": int(home_score),
                    "away_score": int(away_score),
                    "outcome": outcome,
                    "updated_at": datetime.now().isoformat(),
                }

                # If a provider id was supplied with the update, persist it for future exact matching
                if provider_id is not None and provider_name:
                    record.setdefault("provider_ids", {})
                    if provider_name == "football-data":
                        record["provider_ids"]["football_data_id"] = provider_id
                    elif provider_name == "api-football":
                        record["provider_ids"]["api_football_fixture_id"] = provider_id
                    else:
                        # Generic provider id storage
                        record["provider_ids"][provider_name + "_id"] = provider_id

                # Compute prediction correctness
                pred = record.get("prediction", {}) or {}

                def norm(x):
                    try:
                        x = float(x)
                        if x > 1:
                            return x / 100.0
                        return x
                    except Exception:
                        return 0.0

                ph = norm(
                    pred.get("home_win_prob", pred.get("home_win_probability", 0))
                )
                pd = norm(pred.get("draw_prob", pred.get("draw_probability", 0)))
                pa = norm(
                    pred.get("away_win_prob", pred.get("away_win_probability", 0))
                )

                predicted = (
                    "home_win"
                    if ph > pd and ph > pa
                    else "draw"
                    if pd > pa
                    else "away_win"
                )
                record["prediction_correct"] = predicted == outcome

                # Exact score correctness and top-3 score check
                try:
                    actual_score_str = f"{int(home_score)}-{int(away_score)}"
                except Exception:
                    actual_score_str = None

                exact = False
                in_top3 = False

                # Check expected final score string if available
                exp_score = None
                for k in ("expected_final_score", "expected_score", "predicted_score"):
                    if k in pred and pred.get(k):
                        exp_score = str(pred.get(k)).strip()
                        break
                if (
                    exp_score
                    and actual_score_str
                    and exp_score.replace(" ", "") == actual_score_str.replace(" ", "")
                ):
                    exact = True

                # Check top N score probabilities (default top 3)
                try:
                    score_probs = pred.get("score_probabilities") or []
                    top_scores = [str(s[0]).strip() for s in score_probs[:3]]
                    if actual_score_str and actual_score_str in [
                        ts.replace(" ", "") for ts in top_scores
                    ]:
                        in_top3 = True
                except Exception:
                    in_top3 = False

                record["exact_score_correct"] = exact
                record["score_in_top3"] = in_top3

                updated = True
                break

            if updated:
                # Save
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                logger.info(
                    f"Updated {match_id} in {output_file.name}: {home_score}-{away_score} ({outcome}), prediction {'correct' if record['prediction_correct'] else 'incorrect'}"
                )
                return True

        logger.warning(f"Match {match_id} not found in any historical files")
        return False

    def backfill_provider_ids(
        self, league: Optional[str] = None, debug: bool = False
    ) -> int:
        """
        Backfill provider IDs for historical records from matching report files (if available).
        Returns number of records updated.
        """
        updated_count = 0
        # Determine target files
        if league:
            files = [self.historical_dir / f"{league}_results.json"]
        else:
            files = list(self.historical_dir.glob("*_results.json"))

        for output_file in files:
            if not output_file.exists():
                continue
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            changed = False
            for record in data:
                if record.get("provider_ids"):
                    continue
                match_id = record.get("match_id")
                rec_league = record.get("league") or output_file.stem.replace(
                    "_results", ""
                )
                report_pred = (
                    self.reports_dir
                    / rec_league
                    / "matches"
                    / match_id
                    / "prediction.json"
                )
                if report_pred.exists():
                    try:
                        with open(report_pred, "r", encoding="utf-8") as f:
                            pred = json.load(f)
                        provs = pred.get("provider_ids") or {}
                        if provs:
                            record["provider_ids"] = provs
                            changed = True
                            updated_count += 1
                            if debug:
                                logger.info(
                                    f"Backfilled provider_ids for {match_id} from {report_pred}"
                                )
                    except Exception:
                        if debug:
                            logger.exception(f"Failed to read or parse {report_pred}")
                        continue

            if changed:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
        return updated_count

    def calculate_accuracy(self, league: str) -> Dict[str, Any]:
        """
        Calculate prediction accuracy from historical data

        Returns accuracy metrics for backtesting validation
        """
        output_file = self.historical_dir / f"{league}_results.json"

        if not output_file.exists():
            return {"error": "No historical data"}

        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Filter to records with actual results
        completed = [r for r in data if r.get("actual_result") is not None]

        if not completed:
            return {"error": "No completed matches with results"}

        # Calculate metrics
        correct = sum(1 for r in completed if r.get("prediction_correct", False))
        total = len(completed)

        # Breakdown by outcome type
        def outcome_of(rec):
            ar = rec.get("actual_result") or {}
            if "outcome" in ar:
                return ar["outcome"]
            # derive from scores
            hs = ar.get("home_score")
            as_ = ar.get("away_score")
            if hs is None or as_ is None:
                return None
            if hs > as_:
                return "home_win"
            if hs == as_:
                return "draw"
            return "away_win"

        home_wins = [r for r in completed if outcome_of(r) == "home_win"]
        draws = [r for r in completed if outcome_of(r) == "draw"]
        away_wins = [r for r in completed if outcome_of(r) == "away_win"]

        home_correct = sum(1 for r in home_wins if r.get("prediction_correct", False))
        draw_correct = sum(1 for r in draws if r.get("prediction_correct", False))
        away_correct = sum(1 for r in away_wins if r.get("prediction_correct", False))

        # Exact score and top-3 score metrics
        exact_correct = sum(1 for r in completed if r.get("exact_score_correct", False))
        top3_matches = sum(1 for r in completed if r.get("score_in_top3", False))

        return {
            "league": league,
            "total_matches": total,
            "overall_accuracy": round(correct / total, 4) if total > 0 else 0,
            "overall_accuracy_pct": (
                f"{100 * correct / total:.1f}%" if total > 0 else "N/A"
            ),
            "exact_score": {
                "total": exact_correct,
                "pct": f"{100 * exact_correct / total:.1f}%" if total > 0 else "N/A",
            },
            "top3_score": {
                "total": top3_matches,
                "pct": f"{100 * top3_matches / total:.1f}%" if total > 0 else "N/A",
            },
            "breakdown": {
                "home_wins": {
                    "total": len(home_wins),
                    "correct": home_correct,
                    "accuracy": (
                        round(home_correct / len(home_wins), 4) if home_wins else 0
                    ),
                },
                "draws": {
                    "total": len(draws),
                    "correct": draw_correct,
                    "accuracy": round(draw_correct / len(draws), 4) if draws else 0,
                },
                "away_wins": {
                    "total": len(away_wins),
                    "correct": away_correct,
                    "accuracy": (
                        round(away_correct / len(away_wins), 4) if away_wins else 0
                    ),
                },
            },
            "calculated_at": datetime.now().isoformat(),
        }

    def generate_summary_report(self, league: str) -> str:
        """Generate a markdown summary report for the league and return the path."""
        output_file = self.historical_dir / f"{league}_results.json"
        if not output_file.exists():
            raise FileNotFoundError(output_file)

        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        total = len(data)
        completed = [r for r in data if r.get("actual_result") is not None]
        completed_count = len(completed)
        accuracy_info = self.calculate_accuracy(league)

        report_lines = [
            f"# Results Summary - {league}",
            f"Generated: {datetime.now().isoformat()}",
            "",
            f"Total predictions collected: **{total}**",
            f"Completed matches: **{completed_count}**",
            "",
            "## Accuracy",
            f"Overall: **{accuracy_info.get('overall_accuracy_pct', 'N/A')}**",
            f"Exact score correct: **{accuracy_info.get('exact_score', {}).get('total', 'N/A')}** ({accuracy_info.get('exact_score', {}).get('pct', 'N/A')})",
            f"Actual score appeared in top-3 predicted scores: **{accuracy_info.get('top3_score', {}).get('total', 'N/A')}** ({accuracy_info.get('top3_score', {}).get('pct', 'N/A')})",
            "",
            "## Recent Results",
        ]

        # Show last 10 completed
        for r in sorted(completed, key=lambda x: x.get("match_date", ""), reverse=True)[
            :10
        ]:
            mdate = r.get("match_date", "")
            home = r.get("home_team")
            away = r.get("away_team")
            ar = r.get("actual_result", {})
            outcome = ar.get("outcome") if ar else "N/A"
            correct = "✅" if r.get("prediction_correct") else "❌"
            report_lines.append(
                f"- {mdate}: **{home}** vs **{away}** → {ar.get('home_score', '?')}-{ar.get('away_score', '?')} ({outcome}) {correct}"
            )

        reports_dir = PROJECT_ROOT / "reports" / "historical"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = (
            reports_dir
            / f"{league}_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        logger.info(f"Summary report generated: {report_path}")
        return str(report_path)

    def fetch_and_update_from_api(
        self, league: str, days_lookback: int = 7, debug: bool = False
    ) -> int:
        """Fetch finished matches from configured APIs and update historical records.

        Returns number of updated records.
        """
        # Attempt Football-Data.org first (preferred)
        updated = 0
        try:
            from app.utils.http import safe_request_get
        except Exception:
            logger.error("HTTP utilities not available; cannot fetch results from API")
            return updated

        # Determine date range
        date_to = datetime.utcnow().date()
        date_from = date_to - timedelta(days=days_lookback)

        # Map league slug to competition code (simple mapping here)
        league_map = {
            "la-liga": "PD",
            "premier-league": "PL",
            "serie-a": "SA",
            "bundesliga": "BL1",
            "ligue-1": "FL1",
        }
        comp = league_map.get(league)
        if not comp:
            logger.error(f"Unknown league mapping for {league}")
            return updated

        # Read API keys from env or .env
        def read_env_file_for_key(key_name: str):
            env_file = PROJECT_ROOT / ".env"
            if not env_file.exists():
                return None
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == key_name and v.strip():
                        return v.strip()
            return None

        # Name normalization and helper fallback functions must be defined before they are used below
        import unicodedata, re

        # canonical_map is built later from team_name_map.yaml; initialize now so helpers can reference safely
        canonical_map = {}

        def canonicalize(name: str) -> str:
            if not name:
                return ""
            n = unicodedata.normalize("NFKD", name.strip().lower())
            n = "".join(ch for ch in n if not unicodedata.combining(ch))
            n = re.sub(r"[^a-z0-9\s]", " ", n)
            n = re.sub(r"\s+", " ", n).strip()
            stop = {"cf", "fc", "club", "futbol", "de"}
            toks = [tok for tok in n.split() if tok not in stop]
            n = " ".join(toks)
            val = canonical_map.get(n, n)
            return (val or "").strip().lower()

        def levenshtein(a: str, b: str) -> int:
            if a == b:
                return 0
            if not a:
                return len(b)
            if not b:
                return len(a)
            prev = list(range(len(b) + 1))
            for i, ca in enumerate(a, start=1):
                curr = [i]
                for j, cb in enumerate(b, start=1):
                    insert = curr[j - 1] + 1
                    delete = prev[j] + 1
                    replace = prev[j - 1] + (0 if ca == cb else 1)
                    curr.append(min(insert, delete, replace))
                prev = curr
            return prev[-1]

        # Helper: try to fetch final score from API-Football (fallback)
        def _fetch_score_from_api_football_local(
            home_name: str,
            away_name: str,
            date_str: str,
            competition: str,
            debug_local: bool = False,
        ):
            """Query API-Football fixtures to find matching finished fixture and return (home_score, away_score, fixture_id)"""
            key = os.environ.get("API_FOOTBALL_KEY") or read_env_file_for_key(
                "API_FOOTBALL_KEY"
            )
            if not key:
                return None
            try:
                headers = {
                    "x-rapidapi-key": key,
                    "x-rapidapi-host": "v3.football.api-sports.io",
                }
                url = f"https://v3.football.api-sports.io/fixtures?league={competition}&season={datetime.utcnow().year}&from={date_str}&to={date_str}"
                resp = safe_request_get(url, headers=headers, logger=logger)
                if resp.status_code != 200:
                    if debug_local:
                        logger.info(f"API-Football lookup failed: {resp.status_code}")
                    return None
                data = resp.json()
                for item in data.get("response", []):
                    teams = item.get("teams", {})
                    fh = teams.get("home", {}).get("name")
                    fa = teams.get("away", {}).get("name")
                    if canonicalize(fh) == canonicalize(home_name) and canonicalize(
                        fa
                    ) == canonicalize(away_name):
                        score = item.get("score", {}).get("fulltime", {})
                        hs = score.get("home")
                        as_ = score.get("away")
                        fixture_id = item.get("fixture", {}).get("id")
                        if hs is not None and as_ is not None:
                            return (hs, as_, fixture_id)
                return None
            except Exception as e:
                if debug_local:
                    logger.error(f"API-Football lookup error: {e}")
                return None

        # Helper: try FlashScore fallback
        def _fetch_score_from_flashscore_local(
            home_name: str,
            away_name: str,
            date_str: str,
            league_slug: str,
            debug_local: bool = False,
        ):
            try:
                from flashscore_scraper import FlashScoreScraper

                fs = FlashScoreScraper()
                html = fs.get_page(
                    fs.BASE_URL + fs.LEAGUE_URLS.get(league_slug, ""), use_cache=True
                )
                if not html:
                    return None
                matches = fs.parse_match_list(html, league_slug)
                for m in matches:
                    if canonicalize(m.get("home_team")) == canonicalize(
                        home_name
                    ) and canonicalize(m.get("away_team")) == canonicalize(away_name):
                        if m.get("status") == "finished" and (
                            m.get("home_score") is not None
                            and m.get("away_score") is not None
                        ):
                            return (
                                m.get("home_score"),
                                m.get("away_score"),
                                m.get("match_id"),
                            )
                return None
            except Exception as e:
                if debug_local:
                    logger.error(f"FlashScore lookup error: {e}")
                return None

        fd_key = os.environ.get("FOOTBALL_DATA_API_KEY") or read_env_file_for_key(
            "FOOTBALL_DATA_API_KEY"
        )
        # Build request
        if fd_key:
            headers = {"X-Auth-Token": fd_key}
            url = f"https://api.football-data.org/v4/competitions/{comp}/matches?status=FINISHED&dateFrom={date_from.isoformat()}&dateTo={date_to.isoformat()}"
            try:
                resp = safe_request_get(url, headers=headers, logger=logger)
                if resp.status_code == 200:
                    data = resp.json()
                    matches = data.get("matches", [])
                    logger.info(
                        f"Football-Data: fetched {len(matches)} finished matches for {league} (date range {date_from}→{date_to})"
                    )
                    if debug:
                        # print sample entries for debugging
                        for m in matches[:5]:
                            logger.info(
                                f"  sample: {m.get('homeTeam', {}).get('name')} vs {m.get('awayTeam', {}).get('name')} @ {m.get('utcDate')} -> {m.get('score', {}).get('fullTime', {})}"
                            )
                    for m in matches:
                        home = m.get("homeTeam", {}).get("name")
                        away = m.get("awayTeam", {}).get("name")
                        date = (m.get("utcDate") or "")[:10]
                        home_score = (
                            m.get("score", {}).get("fullTime", {}).get("homeTeam")
                        )
                        away_score = (
                            m.get("score", {}).get("fullTime", {}).get("awayTeam")
                        )
                        if debug:
                            logger.info(
                                f"Attempting API match: {home} vs {away} on {date} -> {home_score}-{away_score}"
                            )
                        # Football-Data.org match id
                        fd_id = m.get("id")

                        # If FD did not include final scores, attempt API-Football then FlashScore as fallback
                        attempted_fallback = False
                        if home_score is None or away_score is None:
                            attempted_fallback = True
                            # Try API-Football lookup (local wrapper)
                            try:
                                af_score = _fetch_score_from_api_football_local(
                                    home, away, date, comp, debug_local=debug
                                )
                                if af_score:
                                    home_score, away_score, fixture_id = af_score
                                    if debug:
                                        logger.info(
                                            f"Fallback: API-Football provided score {home_score}-{away_score} (fixture_id={fixture_id}) for {home} vs {away} on {date}"
                                        )
                                    matched = self._match_and_update(
                                        league,
                                        date,
                                        home,
                                        away,
                                        home_score,
                                        away_score,
                                        debug=debug,
                                        provider_id=fixture_id,
                                        provider_name="api-football",
                                    )
                                    updated += matched
                                    # continue to next match after successful fallback
                                    continue
                            except Exception as e:
                                if debug:
                                    logger.error(f"API-Football fallback error: {e}")

                            # Try FlashScore as last-resort (local wrapper)
                            try:
                                fs_score = _fetch_score_from_flashscore_local(
                                    home, away, date, league, debug_local=debug
                                )
                                if fs_score:
                                    home_score, away_score, fs_mid = fs_score
                                    if debug:
                                        logger.info(
                                            f"Fallback: FlashScore provided score {home_score}-{away_score} (match_id={fs_mid}) for {home} vs {away} on {date}"
                                        )
                                    matched = self._match_and_update(
                                        league,
                                        date,
                                        home,
                                        away,
                                        home_score,
                                        away_score,
                                        debug=debug,
                                        provider_id=fs_mid,
                                        provider_name="flashscore",
                                    )
                                    updated += matched
                                    continue
                            except Exception as e:
                                if debug:
                                    logger.error(f"FlashScore fallback error: {e}")

                        # If we have scores (from FD or earlier), proceed to normal matching
                        matched = self._match_and_update(
                            league,
                            date,
                            home,
                            away,
                            home_score,
                            away_score,
                            debug=debug,
                            provider_id=fd_id,
                            provider_name="football-data",
                        )
                        if matched == 0 and debug and not attempted_fallback:
                            logger.info(
                                f"No unmatched historical record found for API match: {home} vs {away} on {date} (fd_id={fd_id})"
                            )
                        updated += matched
                else:
                    logger.warning(f"Football-Data fetch failed: {resp.status_code}")
            except Exception as e:
                logger.error(f"Football-Data fetch error: {e}")
        else:
            logger.info(
                "FOOTBALL_DATA_API_KEY not found; skipping Football-Data.org fetch"
            )

        # Try API-Football (RapidAPI) as fallback
        api_football_key = os.environ.get("API_FOOTBALL_KEY") or read_env_file_for_key(
            "API_FOOTBALL_KEY"
        )
        if api_football_key:
            # We try using competitions -> fixtures with date range
            try:
                headers = {
                    "x-rapidapi-key": api_football_key,
                    "x-rapidapi-host": "v3.football.api-sports.io",
                }
                url = f"https://v3.football.api-sports.io/fixtures?league={comp}&season={datetime.utcnow().year}&from={date_from.isoformat()}&to={date_to.isoformat()}"
                resp = safe_request_get(url, headers=headers, logger=logger)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("response", []):
                        fixture = item.get("fixture", {})
                        teams = item.get("teams", {})
                        score = item.get("score", {}).get("fulltime", {})
                        home = teams.get("home", {}).get("name")
                        away = teams.get("away", {}).get("name")
                        date = (fixture.get("date") or "")[:10]
                        home_score = score.get("home")
                        away_score = score.get("away")
                        # API-Football fixture id
                        fixture_id = None
                        try:
                            fixture_id = item.get("fixture", {}).get("id")
                        except Exception:
                            fixture_id = None
                        matched = self._match_and_update(
                            league,
                            date,
                            home,
                            away,
                            home_score,
                            away_score,
                            debug=debug,
                            provider_id=fixture_id,
                            provider_name="api-football",
                        )
                        if matched == 0 and debug:
                            logger.info(
                                f"No unmatched historical record found for API-Football match: {home} vs {away} on {date} (fixture_id={fixture_id})"
                            )
                        updated += matched
                else:
                    logger.warning(f"API-Football fetch failed: {resp.status_code}")
            except Exception as e:
                logger.error(f"API-Football fetch error: {e}")
        else:
            logger.info("API_FOOTBALL_KEY not found; skipping API-Football fetch")

        logger.info(f"Total updated records for {league}: {updated}")
        return updated

    def _match_and_update(
        self,
        league: str,
        date: str,
        home: str,
        away: str,
        home_score: Optional[int],
        away_score: Optional[int],
        debug: bool = False,
        provider_id: Optional[Any] = None,
        provider_name: Optional[str] = None,
    ) -> int:
        """Helper: find a record matching home/away/date and update it with scores."""
        if home_score is None or away_score is None:
            return 0
        output_file = self.historical_dir / f"{league}_results.json"
        if not output_file.exists():
            return 0
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return 0

        # Match heuristic: match_date + home_team + away_team (case-insensitive)
        # Use canonical team mapping if available; fallback to fuzzy matching
        # Build canonical mapping using a normalized key so diacritics and punctuation
        # are handled consistently across data sources.
        canonical_map = {}
        try:
            cfg_path = PROJECT_ROOT / "config" / "team_name_map.yaml"
            if cfg_path.exists():
                import yaml

                cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
                # Helper to normalize map keys the same way we normalize names
                import unicodedata, re

                def _normalize_key(s: str) -> str:
                    if not s:
                        return ""
                    t = unicodedata.normalize("NFKD", s.strip().lower())
                    t = "".join(ch for ch in t if not unicodedata.combining(ch))
                    t = re.sub(r"[^a-z0-9\s]", " ", t)
                    t = re.sub(r"\s+", " ", t).strip()
                    # Remove common stopwords/abbreviations (cf, fc, club, futbol, de)
                    stop = {"cf", "fc", "club", "futbol", "de"}
                    toks = [tok for tok in t.split() if tok not in stop]
                    return " ".join(toks)

                for canonical, variants in (cfg.get("mappings") or {}).items():
                    canonical_map[_normalize_key(canonical)] = canonical
                    for v in variants:
                        canonical_map[_normalize_key(v)] = canonical
        except Exception:
            pass

        # Normalize names by removing diacritics, punctuation and collapsing whitespace
        import unicodedata, re

        def canonicalize(name: str) -> str:
            if not name:
                return ""
            n = unicodedata.normalize("NFKD", name.strip().lower())
            n = "".join(ch for ch in n if not unicodedata.combining(ch))
            n = re.sub(r"[^a-z0-9\s]", " ", n)
            n = re.sub(r"\s+", " ", n).strip()
            # Remove common stopwords/abbreviations to handle CF/Club variants
            stop = {"cf", "fc", "club", "futbol", "de"}
            toks = [tok for tok in n.split() if tok not in stop]
            n = " ".join(toks)
            # Map to known canonical name when possible
            val = canonical_map.get(n, n)
            return (val or "").strip().lower()

        # Fuzzy fallback using basic Levenshtein distance if names differ
        def levenshtein(a: str, b: str) -> int:
            # small implementation to avoid extra deps
            if a == b:
                return 0
            if not a:
                return len(b)
            if not b:
                return len(a)
            prev = list(range(len(b) + 1))
            for i, ca in enumerate(a, start=1):
                curr = [i]
                for j, cb in enumerate(b, start=1):
                    insert = curr[j - 1] + 1
                    delete = prev[j] + 1
                    replace = prev[j - 1] + (0 if ca == cb else 1)
                    curr.append(min(insert, delete, replace))
                prev = curr
            return prev[-1]

        # Parse API date for tolerant matching (allow +/- 1 day for timezone discrepancies)
        try:
            api_date_obj = datetime.fromisoformat(date).date()
        except Exception:
            api_date_obj = None

        for record in data:
            rec_raw = record.get("match_date") or ""
            rec_date = (rec_raw)[:10]
            if debug:
                logger.info(
                    f"Checking record {record.get('match_id')}: rec_date={rec_date} api_date={date}"
                )

            # Skip records without a parsable date
            if not rec_date:
                if debug:
                    logger.info(
                        f"Skipping {record.get('match_id')} because no match_date present"
                    )
                continue

            # If API date parse succeeded, allow +/-1 day tolerance
            if api_date_obj is not None:
                try:
                    rec_date_obj = datetime.fromisoformat(rec_date).date()
                    delta_days = abs((rec_date_obj - api_date_obj).days)
                    if delta_days > 1:
                        if debug:
                            logger.info(
                                f"Skipping {record.get('match_id')} due to date delta {delta_days} days"
                            )
                        continue
                except Exception:
                    # If record date is unparsable, skip
                    if debug:
                        logger.info(
                            f"Skipping {record.get('match_id')} because record date unparsable: {rec_date}"
                        )
                    continue
            else:
                if rec_date != date:
                    continue

            rec_home = canonicalize(record.get("home_team", ""))
            rec_away = canonicalize(record.get("away_team", ""))
            api_home = canonicalize(home or "")
            api_away = canonicalize(away or "")

            # Debug info for this candidate
            if debug:
                logger.info(
                    f"Candidate record {record.get('match_id')}: rec_home='{rec_home}' rec_away='{rec_away}' api_home='{api_home}' api_away='{api_away}' date={rec_date}"
                )

            # Provider ID match (preferred when available)
            provs = record.get("provider_ids", {}) or {}
            try:
                pid = str(provider_id) if provider_id is not None else None
                if pid and provider_name:
                    key = None
                    if provider_name == "football-data":
                        key = "football_data_id"
                    elif provider_name == "api-football":
                        key = "api_football_fixture_id"
                    # Check known keys
                    if key and str(provs.get(key)) == pid:
                        if record.get("actual_result") is not None:
                            if debug:
                                logger.info(
                                    f"Skipping {record.get('match_id')} because it already has actual_result"
                                )
                            return 0
                        if debug:
                            logger.info(
                                f"Provider ID match found for {record.get('match_id')} via {provider_name} id={pid}"
                            )
                        return (
                            1
                            if self.update_actual_results(
                                league,
                                record["match_id"],
                                int(home_score),
                                int(away_score),
                                provider_id=provider_id,
                                provider_name=provider_name,
                            )
                            else 0
                        )
            except Exception:
                pass

            # Exact canonical match
            if rec_home == api_home and rec_away == api_away:
                if record.get("actual_result") is not None:
                    if debug:
                        logger.info(
                            f"Skipping {record.get('match_id')} because it already has actual_result"
                        )
                    return 0
                if debug:
                    logger.info(f"Exact match found for {record.get('match_id')}")
                return (
                    1
                    if self.update_actual_results(
                        league,
                        record["match_id"],
                        int(home_score),
                        int(away_score),
                        provider_id=provider_id,
                        provider_name=provider_name,
                    )
                    else 0
                )
            # Try fuzzy matching threshold
            try:
                dist_home = levenshtein(rec_home, api_home)
                dist_away = levenshtein(rec_away, api_away)
                # Normalize by max length
                len_home = max(1, max(len(rec_home), len(api_home)))
                len_away = max(1, max(len(rec_away), len(api_away)))
                nh = dist_home / len_home
                na = dist_away / len_away
                if debug:
                    logger.info(
                        f"Fuzzy distances: home={dist_home}/{len_home} ({nh:.2f}), away={dist_away}/{len_away} ({na:.2f})"
                    )
                # Slightly relaxed fuzzy threshold to account for different naming conventions across providers
                if (nh) <= 0.30 and (na) <= 0.30:
                    if record.get("actual_result") is not None:
                        if debug:
                            logger.info(
                                f"Skipping {record.get('match_id')} because it already has actual_result"
                            )
                        return 0
                    if debug:
                        logger.info(
                            f"Fuzzy match accepted for {record.get('match_id')} (home_dist={nh:.2f}, away_dist={na:.2f})"
                        )
                    return (
                        1
                        if self.update_actual_results(
                            league,
                            record["match_id"],
                            int(home_score),
                            int(away_score),
                            provider_id=provider_id,
                            provider_name=provider_name,
                        )
                        else 0
                    )
            except Exception as e:
                if debug:
                    logger.error(f"Fuzzy matching error: {e}")
                pass

        return 0


def send_notification_email(league: str, updated: int, summary: dict):
    """Send a simple notification email with the fetch summary if SMTP vars are configured."""
    import smtplib
    from email.message import EmailMessage

    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    email_to = os.environ.get("EMAIL_TO")
    email_from = os.environ.get("EMAIL_FROM", smtp_user)

    if not smtp_host or not smtp_user or not smtp_pass or not email_to:
        logger.info("SMTP config not found; skipping notification email")
        return False

    msg = EmailMessage()
    msg["Subject"] = f"Results Fetch Summary: {league} - {updated} updated"
    msg["From"] = email_from
    msg["To"] = email_to

    body = [
        f"League: {league}",
        f"Updated records: {updated}",
        "",
        "Accuracy summary:",
        json.dumps(summary, indent=2),
    ]
    msg.set_content("\n".join(body))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
        logger.info(f"Notification email sent to {email_to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification email: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Collect historical match results")
    parser.add_argument("--league", type=str, help="League to collect")
    parser.add_argument(
        "--all-leagues", action="store_true", help="Collect all leagues"
    )
    parser.add_argument(
        "--init-historical",
        action="store_true",
        help="Create empty historical files for supported/detected leagues",
    )
    parser.add_argument(
        "--update-result",
        nargs=4,
        metavar=("LEAGUE", "MATCH_ID", "HOME", "AWAY"),
        help="Update actual result: league match_id home_score away_score",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch finished results from API for provided --league",
    )
    parser.add_argument(
        "--fetch-all",
        action="store_true",
        help="Fetch finished results from API for all supported leagues",
    )
    parser.add_argument(
        "--backfill-provider-ids",
        action="store_true",
        help="Backfill provider ids from reports into historical records",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug output during fetch/matching"
    )
    parser.add_argument(
        "--auto-optimize",
        type=int,
        default=0,
        help="If >=1, run optimizer when completed matches for the league >= threshold",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Send notification email summary if SMTP env vars are configured",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate a markdown summary report for the league after fetch",
    )
    parser.add_argument("--accuracy", type=str, help="Calculate accuracy for league")
    parser.add_argument(
        "--accuracy-all",
        action="store_true",
        help="Calculate accuracy for all historical leagues and write summary JSON",
    )

    args = parser.parse_args()
    collector = HistoricalResultsCollector()

    if args.init_historical:
        created = collector.ensure_historical_files()
        if created:
            print("Created historical files:")
            for p in created:
                print(f"  {p}")
        else:
            print("Historical files already present; no files created.")
        return

    if args.update_result:
        league, match_id, home, away = args.update_result
        collector.update_actual_results(league, match_id, int(home), int(away))

    elif args.accuracy:
        result = collector.calculate_accuracy(args.accuracy)
        print(json.dumps(result, indent=2))

    elif args.fetch_all:
        for league in collector.SUPPORTED_LEAGUES:
            logger.info(f"Fetching finished results for {league}...")
            # first ensure we have predictions saved
            results = collector.collect_from_reports(league)
            if results:
                collector.save_historical_data(league, results)
            updated = collector.fetch_and_update_from_api(league, debug=args.debug)
            logger.info(f"Updated {updated} records for {league}")

            # Optional: Auto-optimize
            if args.auto_optimize and args.auto_optimize > 0:
                # Count completed matches
                with open(
                    collector.historical_dir / f"{league}_results.json",
                    "r",
                    encoding="utf-8",
                ) as f:
                    data = json.load(f)
                completed = [r for r in data if r.get("actual_result") is not None]
                if len(completed) >= args.auto_optimize:
                    try:
                        from scripts.optimize_accuracy import AccuracyOptimizer

                        opt = AccuracyOptimizer()
                        logger.info(
                            f"Auto-optimization trigger: running full optimization for {league}"
                        )
                        opt.full_optimization(league=league)
                    except Exception as e:
                        logger.error(f"Auto-optimization failed: {e}")

            # Optional: send notification
            if args.notify:
                try:
                    summary = collector.calculate_accuracy(league)
                    send_notification_email(league, updated, summary)
                except Exception as e:
                    logger.error(f"Notification failed: {e}")

    elif args.fetch and args.league:
        # fetch for a single league
        league = args.league
        logger.info(f"Fetching finished results for {league}...")
        results = collector.collect_from_reports(league)
        if results:
            collector.save_historical_data(league, results)
        updated = collector.fetch_and_update_from_api(league, debug=args.debug)
        logger.info(f"Updated {updated} records for {league}")

        # Optional: report generation for this single league
        if args.report:
            try:
                report_path = collector.generate_summary_report(league)
                logger.info(f"Report generated: {report_path}")
            except Exception as e:
                logger.error(f"Report generation failed: {e}")

        # Optional: Auto-optimize for this single league
        if args.auto_optimize and args.auto_optimize > 0:
            with open(
                collector.historical_dir / f"{league}_results.json",
                "r",
                encoding="utf-8",
            ) as f:
                data = json.load(f)
            completed = [r for r in data if r.get("actual_result") is not None]
            if len(completed) >= args.auto_optimize:
                try:
                    from scripts.optimize_accuracy import AccuracyOptimizer

                    opt = AccuracyOptimizer()
                    logger.info(
                        f"Auto-optimization trigger: running full optimization for {league}"
                    )
                    opt.full_optimization(league=league)
                except Exception as e:
                    logger.error(f"Auto-optimization failed: {e}")

        if args.notify:
            try:
                summary = collector.calculate_accuracy(league)
                send_notification_email(league, updated, summary)
            except Exception as e:
                logger.error(f"Notification failed: {e}")

    elif args.backfill_provider_ids:
        leagues = [args.league] if args.league else collector.detect_report_leagues()
        total_backfilled = 0
        for l in leagues:
            total_backfilled += collector.backfill_provider_ids(l, debug=args.debug)
        logger.info(
            f"Backfilled {total_backfilled} provider ids for leagues: {', '.join(leagues)}"
        )

    elif args.accuracy_all:
        # Calculate accuracy for all historical files and write a summary
        summary = {}
        for f in collector.historical_dir.glob("*_results.json"):
            league = f.stem.replace("_results", "")
            try:
                acc = collector.calculate_accuracy(league)
                summary[league] = acc
            except Exception as e:
                logger.error(f"Failed to calculate accuracy for {league}: {e}")
        out_dir = PROJECT_ROOT / "reports" / "historical"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = (
            out_dir
            / f"accuracy_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(out_file, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)
        logger.info(f"Wrote accuracy summary to {out_file}")

    elif args.all_leagues:
        # Detect leagues from the reports folder so new leagues are automatically handled
        detected = collector.detect_report_leagues()
        if not detected:
            logger.info(
                "No league folders detected under reports/leagues; falling back to SUPPORTED_LEAGUES"
            )
            detected = collector.SUPPORTED_LEAGUES
        for league in detected:
            logger.info(f"Collecting {league}...")
            results = collector.collect_from_reports(league)
            if results:
                collector.save_historical_data(league, results)

    elif args.league:
        results = collector.collect_from_reports(args.league)
        if results:
            collector.save_historical_data(args.league, results)
        else:
            print(f"No results found for {args.league}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
