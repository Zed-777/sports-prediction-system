#!/usr/bin/env python3
"""
Collect Historical Data
- Reads CSV files in data/backup_csv
- Computes rolling team stats and H2H for each match (using prior matches only)
- Outputs processed JSON dataset for training in data/processed/historical/
"""

import json
import math
import os
from collections import defaultdict, deque
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
BACKUP_CSV = ROOT / 'data' / 'backup_csv'
PROCESSED_DIR = ROOT / 'data' / 'processed' / 'historical'
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Parameters
RECENT_FORM_WINDOW = 5


def parse_match_row(row: dict[str, str]) -> dict:
    """Parse a CSV row into match dictionary"""
    # Normalize and parse fields
    match = {}
    match['id'] = int(row.get('id') or 0)
    match['home_team'] = row.get('home_team')
    match['away_team'] = row.get('away_team')
    match['date'] = row.get('date')
    match['status'] = row.get('status') or 'finished'
    home_score = row.get('home_score')
    away_score = row.get('away_score')
    # pandas may return floats or NaN; handle robustly
    def to_int_optional(val):
        try:
            if val is None:
                return None
            if isinstance(val, float) and math.isnan(val):
                return None
            if isinstance(val, str) and val.strip() == '':
                return None
            return int(val)
        except Exception:
            return None

    match['home_score'] = to_int_optional(home_score)
    match['away_score'] = to_int_optional(away_score)
    return match


def outcome_label(home_score: int, away_score: int) -> int:
    """Return label: 2 = home win, 1 = draw, 0 = away win"""
    if home_score > away_score:
        return 2
    if home_score == away_score:
        return 1
    return 0


class TeamStats:
    def __init__(self):
        self.home_matches = 0
        self.away_matches = 0
        self.home_goals_for = 0
        self.home_goals_against = 0
        self.away_goals_for = 0
        self.away_goals_against = 0
        self.home_wins = 0
        self.home_draws = 0
        self.home_losses = 0
        self.away_wins = 0
        self.away_draws = 0
        self.away_losses = 0
        self.recent_results = deque(maxlen=RECENT_FORM_WINDOW)

    def update_from_result(self, is_home: bool, goals_for: int, goals_against: int):
        if is_home:
            self.home_matches += 1
            self.home_goals_for += goals_for
            self.home_goals_against += goals_against
            if goals_for > goals_against:
                self.home_wins += 1
                self.recent_results.append(2)
            elif goals_for == goals_against:
                self.home_draws += 1
                self.recent_results.append(1)
            else:
                self.home_losses += 1
                self.recent_results.append(0)
        else:
            self.away_matches += 1
            self.away_goals_for += goals_for
            self.away_goals_against += goals_against
            if goals_for > goals_against:
                self.away_wins += 1
                self.recent_results.append(2)
            elif goals_for == goals_against:
                self.away_draws += 1
                self.recent_results.append(1)
            else:
                self.away_losses += 1
                self.recent_results.append(0)

    def home_win_rate(self) -> float:
        if self.home_matches == 0:
            return 0.0
        return self.home_wins / max(1, self.home_matches)

    def away_win_rate(self) -> float:
        if self.away_matches == 0:
            return 0.0
        return self.away_wins / max(1, self.away_matches)

    def avg_goals_for_home(self) -> float:
        return self.home_goals_for / max(1, self.home_matches)

    def avg_goals_for_away(self) -> float:
        return self.away_goals_for / max(1, self.away_matches)

    def recent_form_score(self) -> float:
        if not self.recent_results:
            return 0.5
        # Weighted score: 2=win, 1=draw, 0=loss -> normalize
        return sum(self.recent_results) / (2.0 * len(self.recent_results))


def compute_h2h_stats(match_list: list[dict], home: str, away: str, match_date: str) -> dict:
    """Compute head-to-head stats prior to match_date"""
    home_wins = 0
    away_wins = 0
    draws = 0
    total = 0
    for m in match_list:
        if m['date'] >= match_date:
            continue
        if (m['home_team'] == home and m['away_team'] == away) or (m['home_team'] == away and m['away_team'] == home):
            if m['home_score'] is None or m['away_score'] is None:
                continue
            total += 1
            # Determine winner from home perspective
            if m['home_team'] == home:
                if m['home_score'] > m['away_score']:
                    home_wins += 1
                elif m['home_score'] == m['away_score']:
                    draws += 1
                else:
                    away_wins += 1
            else:
                # match home_team == away
                if m['away_score'] > m['home_score']:
                    home_wins += 1
                elif m['away_score'] == m['home_score']:
                    draws += 1
                else:
                    away_wins += 1
    return {
        'total_meetings': total,
        'home_wins': int(home_wins),
        'away_wins': int(away_wins),
        'draws': int(draws)
    }


def process_matches(matches: list[dict]) -> tuple[list[dict], list[int]]:
    """Create feature vector and labels for matches using prior history only"""
    # Sort by date ascending to simulate time series
    matches_sorted = sorted(matches, key=lambda x: x['date'])

    team_stats_map: dict[str, TeamStats] = defaultdict(TeamStats)

    processed = []
    labels = []

    for m in matches_sorted:
        if m['status'] != 'finished' or m['home_score'] is None or m['away_score'] is None:
            # skip scheduled or incomplete matches
            # But still update team_stats based on future matches? No. We only update after a match is processed.
            continue

        home = m['home_team']
        away = m['away_team']
        date = m['date']

        # Compute team-level features from prior matches
        home_stats = team_stats_map[home]
        away_stats = team_stats_map[away]

        # Features
        features = {
            'home_strength': (home_stats.home_wins + home_stats.home_matches) / max(1, home_stats.home_matches + 1),
            'away_strength': (away_stats.away_wins + away_stats.away_matches) / max(1, away_stats.away_matches + 1),
            'strength_diff': (home_stats.home_wins - away_stats.away_wins),
            'home_win_rate': home_stats.home_win_rate(),
            'away_win_rate': away_stats.away_win_rate(),
            'home_avg_goals': home_stats.avg_goals_for_home(),
            'away_avg_goals': away_stats.avg_goals_for_away(),
            'home_recent_form': home_stats.recent_form_score(),
            'away_recent_form': away_stats.recent_form_score(),
            'h2h': compute_h2h_stats(matches_sorted, home, away, date),
            'is_derby': 0,
            'league_position_diff': 0,
            'weather': {'temperature': 18.0, 'precipitation': 0.0},
            'league': 'la-liga'
        }

        label = outcome_label(m['home_score'], m['away_score'])

        processed.append({
            'match_id': m['id'],
            'date': date,
            'home_team': home,
            'away_team': away,
            'features': features,
            'label': label
        })

        labels.append(label)

        # Now update team_stats given this match
        home_stats.update_from_result(True, m['home_score'], m['away_score'])
        away_stats.update_from_result(False, m['away_score'], m['home_score'])

    return processed, labels


def collect_from_csv(csv_path: Path) -> tuple[list[dict], list[int]]:
    df = pd.read_csv(csv_path)
    matches = []
    for _, row in df.iterrows():
        match = parse_match_row(row.to_dict())
        matches.append(match)
    processed, labels = process_matches(matches)
    return processed, labels


def save_processed(processed: list[dict], labels: list[int], out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({'processed': processed, 'labels': labels}, f, indent=2)


def main():
    print("Collecting historical data from CSVs...")
    csv_files = list(BACKUP_CSV.glob('*.csv'))
    all_processed = []
    all_labels = []

    for csv_file in csv_files:
        print(f"Processing {csv_file.name}...")
        # Only process files that look like match data (have date/home_team columns)
        try:
            sample_df = pd.read_csv(csv_file, nrows=1)
            if 'date' not in sample_df.columns or 'home_team' not in sample_df.columns:
                print(f"  -> Skipping {csv_file.name}: not a match data CSV")
                continue
        except Exception:
            print(f"  -> Skipping {csv_file.name}: could not read header")
            continue
        processed, labels = collect_from_csv(csv_file)
        print(f"  -> processed {len(processed)} finished matches")
        all_processed.extend(processed)
        all_labels.extend(labels)

    # Optionally collect from API if API key provided
    # You can set COLLECT_SEASONS env variable to comma-separated years e.g. "2018,2019,2020"
    seasons_env = os.environ.get('COLLECT_SEASONS', '2018,2019,2020,2021,2022,2023,2024')
    seasons = [s.strip() for s in seasons_env.split(',') if s.strip()]
    # Football-Data.org: collect per season optionally for a competition
    fd_competition = os.environ.get('FD_COMPETITION', 'PD')
    # Try environment, then .env for convenience
    def read_env_file_for_key(key_name: str):
        env_file = ROOT / '.env'
        if not env_file.exists():
            return None
        for line in env_file.read_text(encoding='utf-8').splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                if k.strip() == key_name and v.strip():
                    return v.strip()
        return None

    api_key = os.environ.get('FOOTBALL_DATA_API_KEY') or read_env_file_for_key('FOOTBALL_DATA_API_KEY')
    if api_key:
        for season in seasons:
            try:
                print(f"Collecting from Football-Data.org API for competition {fd_competition} season {season}...")
                processed_api, labels_api = collect_from_api(api_key, competition_code=fd_competition, season=season)
                print(f"  -> processed {len(processed_api)} matches from Football-Data.org API ({season})")
                all_processed.extend(processed_api)
                all_labels.extend(labels_api)
            except Exception as e:
                print(f"  -> Football-Data API collection failed for {season}: {e}")
    # Optional: API-Football integration via fetch script
    api_football_key = os.environ.get('API_FOOTBALL_KEY') or read_env_file_for_key('API_FOOTBALL_KEY')
    api_football_league = os.environ.get('API_FOOTBALL_LEAGUE')
    api_football_seasons = os.environ.get('API_FOOTBALL_SEASONS')
    if api_football_key and api_football_league and api_football_seasons:
        try:
            import subprocess
            seasons = api_football_seasons
            # Use the new API-Football fetcher script
            cmd = f"python scripts/fetch_api_football.py --leagues {api_football_league} --seasons {seasons} --outfile {BACKUP_CSV}/api_football_{api_football_league}_seasons.csv"
            print(f"Fetching API-Football data using: {cmd}")
            subprocess.run(cmd, shell=True, check=True)
            # read the generated CSV into processed dataset
            csv_file = BACKUP_CSV / f"api_football_{api_football_league}_seasons.csv"
            if csv_file.exists():
                processed_api, labels_api = collect_from_csv(csv_file)
                all_processed.extend(processed_api)
                all_labels.extend(labels_api)
                print(f"  -> processed {len(processed_api)} matches from API-Football")
        except Exception as e:
            print(f"  -> API-Football collection failed: {e}")

    # Deduplicate matches by `match_id` when saving consolidated dataset
    unique = {}
    deduped_processed = []
    deduped_labels = []
    for sample, label in zip(all_processed, all_labels, strict=True):
        key = sample.get('match_id') or f"{sample.get('date')}_{sample.get('home_team')}_{sample.get('away_team')}"
        if key in unique:
            # skip duplicates
            continue
        unique[key] = True
        deduped_processed.append(sample)
        deduped_labels.append(label)

    # Save consolidated dataset
    out_path = PROCESSED_DIR / 'historical_dataset.json'
    save_processed(deduped_processed, deduped_labels, out_path)

    print(f"Saved processed historical dataset to {out_path}")
    print(f"Total matches processed: {len(deduped_processed)}")


def collect_from_api(api_key: str, competition_code: str = 'PD', season: str = '2024') -> tuple[list[dict], list[int]]:
    """Collect historical matches from Football-Data.org API for a competition and season
    Requires env var FOOTBALL_DATA_API_KEY or passed api_key
    """
    import requests
    from app.utils.http import safe_request_get
    headers = {'X-Auth-Token': api_key}
    url = f'https://api.football-data.org/v4/competitions/{competition_code}/matches?season={season}'
    resp = safe_request_get(url, headers=headers, logger=None)
    if resp.status_code != 200:
        raise Exception(f"Football-Data API error: {resp.status_code} - {resp.text}")
    data = resp.json()
    # Save raw API response
    raw_dir = ROOT / 'data' / 'raw' / 'api' / 'football-data.org'
    raw_dir.mkdir(parents=True, exist_ok=True)
    with open(raw_dir / f'{competition_code}_{season}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    matches = []
    for m in data.get('matches', []):
        match = {
            'id': m.get('id'),
            'home_team': m.get('homeTeam', {}).get('name'),
            'away_team': m.get('awayTeam', {}).get('name'),
            'date': m.get('utcDate', '')[:10],
            'status': m.get('status', 'FINISHED').lower(),
            'home_score': m.get('score', {}).get('fullTime', {}).get('homeTeam'),
            'away_score': m.get('score', {}).get('fullTime', {}).get('awayTeam'),
            'league': competition_code
        }
        matches.append(match)
    processed, labels = process_matches(matches)
    return processed, labels


def collect_api_football(api_key: str, league_id: int = 140, season: str = '2024') -> tuple[list[dict], list[int]]:
    """Collect historical matches from API-Football for a league and season.
    Requires env var API_FOOTBALL_KEY or passed api_key.
    """
    import requests
    from app.utils.http import safe_request_get
    headers = {
        'x-rapidapi-key': api_key,
        'x-rapidapi-host': 'v3.football.api-sports.io'
    }
    url = f'https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}'
    resp = safe_request_get(url, headers=headers, logger=None)
    if resp.status_code != 200:
        raise Exception(f"API-Football error: {resp.status_code} - {resp.text}")
    data = resp.json()
    # Save raw API response
    raw_dir = ROOT / 'data' / 'raw' / 'api' / 'api-football'
    raw_dir.mkdir(parents=True, exist_ok=True)
    with open(raw_dir / f'league_{league_id}_{season}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    matches = []
    for item in data.get('response', []):
        fixture = item.get('fixture', {})
        teams = item.get('teams', {})
        score_obj = item.get('score', {}).get('fulltime', {})
        match = {
            'id': fixture.get('id'),
            'home_team': teams.get('home', {}).get('name'),
            'away_team': teams.get('away', {}).get('name'),
            'date': fixture.get('date', '')[:10],
            'status': fixture.get('status', {}).get('short', 'FT').lower(),
            'home_score': score_obj.get('home'),
            'away_score': score_obj.get('away'),
            'league': league_id
        }
        matches.append(match)
    processed, labels = process_matches(matches)
    return processed, labels




if __name__ == '__main__':
    main()
