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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class HistoricalResultsCollector:
    """Collects and stores historical match results for backtesting"""
    
    SUPPORTED_LEAGUES = [
        'la-liga', 'premier-league', 'serie-a', 'bundesliga', 'ligue-1'
    ]
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.historical_dir = PROJECT_ROOT / 'data' / 'historical'
        self.historical_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir = PROJECT_ROOT / 'reports' / 'leagues'
        
    def collect_from_reports(self, league: str) -> List[Dict[str, Any]]:
        """
        Collect predictions from generated reports and match them with results
        
        This creates training data by pairing our predictions with actual outcomes.
        """
        league_dir = self.reports_dir / league / 'matches'
        if not league_dir.exists():
            logger.warning(f"No reports found for {league}")
            return []
        
        results = []
        
        for match_dir in league_dir.iterdir():
            if not match_dir.is_dir():
                continue
                
            prediction_file = match_dir / 'prediction.json'
            if not prediction_file.exists():
                continue
            
            try:
                with open(prediction_file, 'r', encoding='utf-8') as f:
                    prediction = json.load(f)
                
                # Check if match has completed (we need actual results)
                match_date_str = prediction.get('match_date', '')
                if match_date_str:
                    try:
                        match_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                        if match_date > datetime.now(match_date.tzinfo):
                            # Match hasn't happened yet
                            continue
                    except:
                        pass
                
                # Extract relevant data
                result_entry = {
                    'match_id': match_dir.name,
                    'league': league,
                    'home_team': prediction.get('home_team', ''),
                    'away_team': prediction.get('away_team', ''),
                    'match_date': match_date_str,
                    'prediction': {
                        'home_win_prob': prediction.get('home_win_prob', 0),
                        'draw_prob': prediction.get('draw_prob', 0),
                        'away_win_prob': prediction.get('away_win_prob', 0),
                        'predicted_outcome': prediction.get('recommendation', ''),
                        'confidence': prediction.get('confidence', 0),
                        'expected_home_goals': prediction.get('expected_home_goals', 0),
                        'expected_away_goals': prediction.get('expected_away_goals', 0),
                    },
                    'actual_result': None,  # To be filled when result is known
                    'parameters_used': {
                        'market_blend_weight': prediction.get('phase_enhancements', {}).get('market_blend_weight', 0.18),
                    },
                    'collected_at': datetime.now().isoformat()
                }
                
                results.append(result_entry)
                
            except Exception as e:
                logger.error(f"Error processing {prediction_file}: {e}")
                continue
        
        return results
    
    def save_historical_data(self, league: str, results: List[Dict[str, Any]]):
        """Save or update historical results file"""
        output_file = self.historical_dir / f'{league}_results.json'
        
        # Load existing data
        existing = []
        if output_file.exists():
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except:
                existing = []
        
        # Merge, avoiding duplicates
        existing_ids = {r['match_id'] for r in existing}
        for result in results:
            if result['match_id'] not in existing_ids:
                existing.append(result)
                existing_ids.add(result['match_id'])
        
        # Sort by date
        existing.sort(key=lambda x: x.get('match_date', ''), reverse=True)
        
        # Save
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=2)
        
        logger.info(f"Saved {len(existing)} records to {output_file}")
        return len(existing)
    
    def update_actual_results(self, league: str, match_id: str, 
                             home_score: int, away_score: int) -> bool:
        """
        Update a historical record with actual match result
        
        Args:
            league: League name
            match_id: Match identifier  
            home_score: Actual home goals
            away_score: Actual away goals
            
        Returns:
            True if updated successfully
        """
        output_file = self.historical_dir / f'{league}_results.json'
        
        if not output_file.exists():
            logger.error(f"No historical file for {league}")
            return False
        
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Find and update
        for record in data:
            if record['match_id'] == match_id:
                # Determine actual outcome
                if home_score > away_score:
                    outcome = 'home_win'
                elif away_score > home_score:
                    outcome = 'away_win'
                else:
                    outcome = 'draw'
                
                record['actual_result'] = {
                    'home_score': home_score,
                    'away_score': away_score,
                    'outcome': outcome,
                    'updated_at': datetime.now().isoformat()
                }
                
                # Calculate if prediction was correct
                pred = record.get('prediction', {})
                # Be robust to different key names and missing values
                ph = pred.get('home_win_prob', pred.get('home_win_probability', 0))
                pd = pred.get('draw_prob', pred.get('draw_probability', 0))
                pa = pred.get('away_win_prob', pred.get('away_win_probability', 0))
                # Normalize values if given in percentages (>1)
                def norm(x):
                    try:
                        x = float(x)
                        if x > 1:
                            return x / 100.0
                        return x
                    except Exception:
                        return 0.0
                ph, pd, pa = norm(ph), norm(pd), norm(pa)
                predicted = 'home_win' if ph > pd and ph > pa else 'draw' if pd > pa else 'away_win'
                record['prediction_correct'] = (predicted == outcome)
                
                # Save
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                
                logger.info(f"Updated {match_id}: {home_score}-{away_score} ({outcome}), prediction {'correct' if record['prediction_correct'] else 'incorrect'}")
                return True
        
        logger.warning(f"Match {match_id} not found in {league}")
        return False
    
    def calculate_accuracy(self, league: str) -> Dict[str, Any]:
        """
        Calculate prediction accuracy from historical data
        
        Returns accuracy metrics for backtesting validation
        """
        output_file = self.historical_dir / f'{league}_results.json'
        
        if not output_file.exists():
            return {'error': 'No historical data'}
        
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Filter to records with actual results
        completed = [r for r in data if r.get('actual_result') is not None]
        
        if not completed:
            return {'error': 'No completed matches with results'}
        
        # Calculate metrics
        correct = sum(1 for r in completed if r.get('prediction_correct', False))
        total = len(completed)
        
        # Breakdown by outcome type
        def outcome_of(rec):
            ar = rec.get('actual_result') or {}
            if 'outcome' in ar:
                return ar['outcome']
            # derive from scores
            hs = ar.get('home_score')
            as_ = ar.get('away_score')
            if hs is None or as_ is None:
                return None
            if hs > as_:
                return 'home_win'
            if hs == as_:
                return 'draw'
            return 'away_win'

        home_wins = [r for r in completed if outcome_of(r) == 'home_win']
        draws = [r for r in completed if outcome_of(r) == 'draw']
        away_wins = [r for r in completed if outcome_of(r) == 'away_win']
        
        home_correct = sum(1 for r in home_wins if r.get('prediction_correct', False))
        draw_correct = sum(1 for r in draws if r.get('prediction_correct', False))
        away_correct = sum(1 for r in away_wins if r.get('prediction_correct', False))
        
        return {
            'league': league,
            'total_matches': total,
            'overall_accuracy': round(correct / total, 4) if total > 0 else 0,
            'overall_accuracy_pct': f"{100 * correct / total:.1f}%" if total > 0 else "N/A",
            'breakdown': {
                'home_wins': {
                    'total': len(home_wins),
                    'correct': home_correct,
                    'accuracy': round(home_correct / len(home_wins), 4) if home_wins else 0
                },
                'draws': {
                    'total': len(draws),
                    'correct': draw_correct,
                    'accuracy': round(draw_correct / len(draws), 4) if draws else 0
                },
                'away_wins': {
                    'total': len(away_wins),
                    'correct': away_correct,
                    'accuracy': round(away_correct / len(away_wins), 4) if away_wins else 0
                }
            },
            'calculated_at': datetime.now().isoformat()
        }

    def generate_summary_report(self, league: str) -> str:
        """Generate a markdown summary report for the league and return the path."""
        output_file = self.historical_dir / f'{league}_results.json'
        if not output_file.exists():
            raise FileNotFoundError(output_file)

        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        total = len(data)
        completed = [r for r in data if r.get('actual_result') is not None]
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
            "",
            "## Recent Results",
        ]

        # Show last 10 completed
        for r in sorted(completed, key=lambda x: x.get('match_date', ''), reverse=True)[:10]:
            mdate = r.get('match_date', '')
            home = r.get('home_team')
            away = r.get('away_team')
            ar = r.get('actual_result', {})
            outcome = ar.get('outcome') if ar else 'N/A'
            correct = '✅' if r.get('prediction_correct') else '❌'
            report_lines.append(f"- {mdate}: **{home}** vs **{away}** → {ar.get('home_score','?')}-{ar.get('away_score','?')} ({outcome}) {correct}")

        reports_dir = PROJECT_ROOT / 'reports' / 'historical'
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f'{league}_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        logger.info(f"Summary report generated: {report_path}")
        return str(report_path)

    def fetch_and_update_from_api(self, league: str, days_lookback: int = 7) -> int:
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
            'la-liga': 'PD',
            'premier-league': 'PL',
            'serie-a': 'SA',
            'bundesliga': 'BL1',
            'ligue-1': 'FL1'
        }
        comp = league_map.get(league)
        if not comp:
            logger.error(f"Unknown league mapping for {league}")
            return updated

        # Read API keys from env or .env
        def read_env_file_for_key(key_name: str):
            env_file = PROJECT_ROOT / '.env'
            if not env_file.exists():
                return None
            for line in env_file.read_text(encoding='utf-8').splitlines():
                if '=' in line:
                    k, v = line.split('=', 1)
                    if k.strip() == key_name and v.strip():
                        return v.strip()
            return None

        fd_key = os.environ.get('FOOTBALL_DATA_API_KEY') or read_env_file_for_key('FOOTBALL_DATA_API_KEY')
        # Build request
        if fd_key:
            headers = {'X-Auth-Token': fd_key}
            url = f"https://api.football-data.org/v4/competitions/{comp}/matches?status=FINISHED&dateFrom={date_from.isoformat()}&dateTo={date_to.isoformat()}"
            try:
                resp = safe_request_get(url, headers=headers, logger=logger)
                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get('matches', []):
                        home = m.get('homeTeam', {}).get('name')
                        away = m.get('awayTeam', {}).get('name')
                        date = (m.get('utcDate') or '')[:10]
                        home_score = m.get('score', {}).get('fullTime', {}).get('homeTeam')
                        away_score = m.get('score', {}).get('fullTime', {}).get('awayTeam')
                        # Find matching record in historical file
                        updated += self._match_and_update(league, date, home, away, home_score, away_score)
                else:
                    logger.warning(f"Football-Data fetch failed: {resp.status_code}")
            except Exception as e:
                logger.error(f"Football-Data fetch error: {e}")
        else:
            logger.info("FOOTBALL_DATA_API_KEY not found; skipping Football-Data.org fetch")

        # Try API-Football (RapidAPI) as fallback
        api_football_key = os.environ.get('API_FOOTBALL_KEY') or read_env_file_for_key('API_FOOTBALL_KEY')
        if api_football_key:
            # We try using competitions -> fixtures with date range
            try:
                headers = {'x-rapidapi-key': api_football_key, 'x-rapidapi-host': 'v3.football.api-sports.io'}
                url = f"https://v3.football.api-sports.io/fixtures?league={comp}&season={datetime.utcnow().year}&from={date_from.isoformat()}&to={date_to.isoformat()}"
                resp = safe_request_get(url, headers=headers, logger=logger)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get('response', []):
                        fixture = item.get('fixture', {})
                        teams = item.get('teams', {})
                        score = item.get('score', {}).get('fulltime', {})
                        home = teams.get('home', {}).get('name')
                        away = teams.get('away', {}).get('name')
                        date = (fixture.get('date') or '')[:10]
                        home_score = score.get('home')
                        away_score = score.get('away')
                        updated += self._match_and_update(league, date, home, away, home_score, away_score)
                else:
                    logger.warning(f"API-Football fetch failed: {resp.status_code}")
            except Exception as e:
                logger.error(f"API-Football fetch error: {e}")
        else:
            logger.info("API_FOOTBALL_KEY not found; skipping API-Football fetch")

        logger.info(f"Total updated records for {league}: {updated}")
        return updated

    def _match_and_update(self, league: str, date: str, home: str, away: str, home_score: Optional[int], away_score: Optional[int]) -> int:
        """Helper: find a record matching home/away/date and update it with scores."""
        if home_score is None or away_score is None:
            return 0
        output_file = self.historical_dir / f'{league}_results.json'
        if not output_file.exists():
            return 0
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return 0

        # Match heuristic: match_date + home_team + away_team (case-insensitive)
        # Use canonical team mapping if available; fallback to fuzzy matching
        canonical_map = {}
        try:
            cfg_path = PROJECT_ROOT / 'config' / 'team_name_map.yaml'
            if cfg_path.exists():
                import yaml
                cfg = yaml.safe_load(cfg_path.read_text(encoding='utf-8')) or {}
                for canonical, variants in (cfg.get('mappings') or {}).items():
                    canonical_map[canonical.lower()] = canonical
                    for v in variants:
                        canonical_map[v.lower()] = canonical
        except Exception:
            pass

        def canonicalize(name: str) -> str:
            if not name:
                return ''
            n = name.strip().lower()
            # Return canonical lowercased name for consistent comparisons
            val = canonical_map.get(n, n)
            return (val or '').strip().lower()

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
                    insert = curr[j-1] + 1
                    delete = prev[j] + 1
                    replace = prev[j-1] + (0 if ca == cb else 1)
                    curr.append(min(insert, delete, replace))
                prev = curr
            return prev[-1]

        for record in data:
            rec_date = (record.get('match_date') or '')[:10]
            if rec_date != date:
                continue

            rec_home = canonicalize(record.get('home_team', ''))
            rec_away = canonicalize(record.get('away_team', ''))
            api_home = canonicalize(home or '')
            api_away = canonicalize(away or '')

            # Exact canonical match
            if rec_home == api_home and rec_away == api_away:
                if record.get('actual_result') is not None:
                    return 0
                return 1 if self.update_actual_results(league, record['match_id'], int(home_score), int(away_score)) else 0

            # Try fuzzy matching threshold
            try:
                dist_home = levenshtein(rec_home, api_home)
                dist_away = levenshtein(rec_away, api_away)
                # Normalize by max length
                len_home = max(1, max(len(rec_home), len(api_home)))
                len_away = max(1, max(len(rec_away), len(api_away)))
                if (dist_home / len_home) <= 0.25 and (dist_away / len_away) <= 0.25:
                    if record.get('actual_result') is not None:
                        return 0
                    return 1 if self.update_actual_results(league, record['match_id'], int(home_score), int(away_score)) else 0
            except Exception:
                pass

        return 0


def send_notification_email(league: str, updated: int, summary: dict):
    """Send a simple notification email with the fetch summary if SMTP vars are configured."""
    import smtplib
    from email.message import EmailMessage

    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    email_to = os.environ.get('EMAIL_TO')
    email_from = os.environ.get('EMAIL_FROM', smtp_user)

    if not smtp_host or not smtp_user or not smtp_pass or not email_to:
        logger.info('SMTP config not found; skipping notification email')
        return False

    msg = EmailMessage()
    msg['Subject'] = f"Results Fetch Summary: {league} - {updated} updated"
    msg['From'] = email_from
    msg['To'] = email_to

    body = [f"League: {league}", f"Updated records: {updated}", "", "Accuracy summary:", json.dumps(summary, indent=2)]
    msg.set_content('\n'.join(body))

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
    parser = argparse.ArgumentParser(description='Collect historical match results')
    parser.add_argument('--league', type=str, help='League to collect')
    parser.add_argument('--all-leagues', action='store_true', help='Collect all leagues')
    parser.add_argument('--update-result', nargs=4, metavar=('LEAGUE', 'MATCH_ID', 'HOME', 'AWAY'),
                       help='Update actual result: league match_id home_score away_score')
    parser.add_argument('--fetch', action='store_true', help='Fetch finished results from API for provided --league')
    parser.add_argument('--fetch-all', action='store_true', help='Fetch finished results from API for all supported leagues')
    parser.add_argument('--auto-optimize', type=int, default=0, help='If >=1, run optimizer when completed matches for the league >= threshold')
    parser.add_argument('--notify', action='store_true', help='Send notification email summary if SMTP env vars are configured')
    parser.add_argument('--report', action='store_true', help='Generate a markdown summary report for the league after fetch')
    parser.add_argument('--accuracy', type=str, help='Calculate accuracy for league')
    
    args = parser.parse_args()
    collector = HistoricalResultsCollector()
    
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
            updated = collector.fetch_and_update_from_api(league)
            logger.info(f"Updated {updated} records for {league}")

            # Optional: Auto-optimize
            if args.auto_optimize and args.auto_optimize > 0:
                # Count completed matches
                with open(collector.historical_dir / f"{league}_results.json", 'r', encoding='utf-8') as f:
                    data = json.load(f)
                completed = [r for r in data if r.get('actual_result') is not None]
                if len(completed) >= args.auto_optimize:
                    try:
                        from scripts.optimize_accuracy import AccuracyOptimizer
                        opt = AccuracyOptimizer()
                        logger.info(f"Auto-optimization trigger: running full optimization for {league}")
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
        updated = collector.fetch_and_update_from_api(league)
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
            with open(collector.historical_dir / f"{league}_results.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
            completed = [r for r in data if r.get('actual_result') is not None]
            if len(completed) >= args.auto_optimize:
                try:
                    from scripts.optimize_accuracy import AccuracyOptimizer
                    opt = AccuracyOptimizer()
                    logger.info(f"Auto-optimization trigger: running full optimization for {league}")
                    opt.full_optimization(league=league)
                except Exception as e:
                    logger.error(f"Auto-optimization failed: {e}")

        if args.notify:
            try:
                summary = collector.calculate_accuracy(league)
                send_notification_email(league, updated, summary)
            except Exception as e:
                logger.error(f"Notification failed: {e}")

    elif args.all_leagues:
        for league in collector.SUPPORTED_LEAGUES:
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


if __name__ == '__main__':
    main()
