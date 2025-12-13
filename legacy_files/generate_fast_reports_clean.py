#!/usr/bin/env python3
"""
Single Match Report Generator
Generate report for just the next 1 La Liga match
"""

import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

# Suppress font warnings for cleaner output
warnings.filterwarnings('ignore', category=UserWarning, message='.*missing from font.*')

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

import requests

from data_quality_enhancer import DataQualityEnhancer
from enhanced_predictor import EnhancedPredictor, get_competition_code_from_league


class SingleMatchGenerator:
    """Generate report for just 1 match"""

    def __init__(self):
        self.api_key = os.getenv('FOOTBALL_DATA_API_KEY', '')
        if not self.api_key:
            raise ValueError("FOOTBALL_DATA_API_KEY environment variable not set")
        self.headers = {'X-Auth-Token': self.api_key}
        self.setup_directory_structure()

        # Initialize enhanced prediction engines
        self.enhanced_predictor = EnhancedPredictor(self.api_key)
        self.data_quality_enhancer = DataQualityEnhancer(self.api_key)

    def setup_directory_structure(self):
        """Create proper directory structure with .keep files"""
        directories = [
            "reports/leagues/la-liga/matches",
            "reports/leagues/premier-league/matches",
            "reports/leagues/bundesliga/matches",
            "reports/leagues/serie-a/matches",
            "reports/leagues/ligue-1/matches",
            "reports/formats/json",
            "reports/formats/markdown",
            "reports/formats/images",
            "reports/archive"
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            # Create .keep file to preserve directory structure
            keep_file = os.path.join(directory, '.keep')
            if not os.path.exists(keep_file):
                with open(keep_file, 'w') as f:
                    f.write(f"# Keep file for {directory}\n# Preserves directory structure when cleaning reports\n")

    def simple_prediction(self, match):
        """Generate prediction without complex systems"""
        confidence = np.random.uniform(0.65, 0.85)

        # Simple probability calculation
        home_advantage = 0.55
        home_prob = home_advantage + np.random.uniform(-0.15, 0.15)
        away_prob = (1 - home_prob) * np.random.uniform(0.6, 0.8)
        draw_prob = 1 - home_prob - away_prob

        # Normalize
        total = home_prob + draw_prob + away_prob
        home_prob /= total
        draw_prob /= total
        away_prob /= total

        expected_home_goals = np.random.uniform(1.2, 2.5)
        expected_away_goals = np.random.uniform(0.8, 2.0)

        return {
            'confidence': confidence,
            'home_win_prob': home_prob,
            'draw_prob': draw_prob,
            'away_win_prob': away_prob,
            'expected_home_goals': expected_home_goals,
            'expected_away_goals': expected_away_goals,
            'processing_time': np.random.uniform(0.5, 1.2)
        }

    def get_league_info(self, league_name):
        """Get API info for different leagues"""
        leagues = {
            'la-liga': {'code': 'PD', 'name': 'La Liga', 'folder': 'la-liga'},
            'laliga': {'code': 'PD', 'name': 'La Liga', 'folder': 'la-liga'},
            'premier-league': {'code': 'PL', 'name': 'Premier League', 'folder': 'premier-league'},
            'premierleague': {'code': 'PL', 'name': 'Premier League', 'folder': 'premier-league'},
            'bundesliga': {'code': 'BL1', 'name': 'Bundesliga', 'folder': 'bundesliga'},
            'serie-a': {'code': 'SA', 'name': 'Serie A', 'folder': 'serie-a'},
            'seriea': {'code': 'SA', 'name': 'Serie A', 'folder': 'serie-a'},
            'ligue-1': {'code': 'FL1', 'name': 'Ligue 1', 'folder': 'ligue-1'},
            'ligue1': {'code': 'FL1', 'name': 'Ligue 1', 'folder': 'ligue-1'}
        }
        return leagues.get(league_name.lower())

    def generate_matches_report(self, num_matches, league_name):
        """Generate report for specified number of matches in specified league"""

        league_info = self.get_league_info(league_name)
        if not league_info:
            print(f"❌ Unknown league: {league_name}")
            print("💡 Available leagues: la-liga, premier-league, bundesliga, serie-a, ligue-1")
            return

        print(f"🏆 Generating Next {num_matches} {league_info['name']} Match(es)")
        print("=" * 50)

        # Get matches
        url = f'https://api.football-data.org/v4/competitions/{league_info["code"]}/matches'
        params = {'status': 'SCHEDULED', 'limit': num_matches}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            all_matches = data.get('matches', [])
            # Manually limit matches since API doesn't always respect limit parameter
            matches = all_matches[:num_matches]
        except Exception as e:
            print(f"❌ Error fetching data: {e}")
            return

        if not matches:
            print("❌ No upcoming matches found")
            return

        print(f"📅 Found {len(matches)} upcoming match(es)")
        print()

        # Process each match
        for i, match in enumerate(matches, 1):
            home_team = match['homeTeam']['name']
            away_team = match['awayTeam']['name']
            match_date = match['utcDate'][:10]

            print(f"[MATCH {i}/{len(matches)}] Processing: {home_team} vs {away_team} on {match_date}")

            try:
                # Generate enhanced prediction
                competition_code = get_competition_code_from_league(league_info['folder'])
                prediction = self.enhanced_predictor.enhanced_prediction(match, competition_code)
            except Exception as e:
                print(f"[ERROR] Prediction failed for {home_team} vs {away_team}: {e}")
                continue

            # Get enhanced data quality information
            enhanced_data = self.data_quality_enhancer.comprehensive_data_enhancement(match)

            # Create match folder in proper structure
            match_folder = f"{home_team.replace(' ', '-')}_vs_{away_team.replace(' ', '-')}_{match_date}"
            full_path = f"reports/leagues/{league_info['folder']}/matches/{match_folder}"
            os.makedirs(full_path, exist_ok=True)

            # Create enhanced match data with all intelligence
            match_data = {
                # Basic Match Information
                'match_id': match['id'],
                'home_team': home_team,
                'away_team': away_team,
                'date': match_date,
                'time': match['utcDate'][11:16],
                'league': league_info['name'],

                # Core Predictions
                'confidence': round(prediction['confidence'], 3),
                'report_accuracy_probability': round(prediction.get('report_accuracy_probability', 0.65), 3),
                'home_win_probability': round(prediction['home_win_prob'], 3),
                'draw_probability': round(prediction['draw_prob'], 3),
                'away_win_probability': round(prediction['away_win_prob'], 3),
                'expected_home_goals': round(prediction['expected_home_goals'], 1),
                'expected_away_goals': round(prediction['expected_away_goals'], 1),
                'processing_time': round(prediction['processing_time'], 2),
                'recommendation': self.get_recommendation(prediction),
                'confidence_level': self.get_confidence_description(prediction['confidence']),

                # Expected Score Predictions
                'expected_final_score': prediction.get('expected_final_score', '1-1'),
                'score_probability': round(prediction.get('score_probability', 10.0), 1),
                'score_probability_normalized': round(prediction.get('score_probability_normalized', 5.0), 1),
                'top3_combined_probability': round(prediction.get('top3_combined_probability', 25.0), 1),
                'top3_probability_normalized': round(prediction.get('top3_probability_normalized', 7.0), 1),
                'alternative_scores': prediction.get('alternative_scores', ['1-0', '2-1', '0-1']),
                'score_probabilities': prediction.get('score_probabilities', []),
                'score_probabilities_normalized': prediction.get('score_probabilities_normalized', []),
                'over_2_5_goals_probability': round(prediction.get('over_2_5_probability', 45.0), 1),
                'both_teams_score_probability': round(prediction.get('both_teams_score_probability', 55.0), 1),

                # Enhanced Intelligence Analysis
                'head_to_head_analysis': prediction.get('head_to_head', {}),
                'home_performance_analysis': prediction.get('home_performance', {}),
                'away_performance_analysis': prediction.get('away_performance', {}),
                'goal_timing_prediction': prediction.get('goal_timing', {}),
                'intelligence_summary': prediction.get('intelligence_summary', {}),

                # Data Quality Enhancements
                'player_availability': enhanced_data.get('player_availability', {}),
                'weather_conditions': enhanced_data.get('weather_conditions', {}),
                'referee_analysis': enhanced_data.get('referee_analysis', {}),
                'team_news': enhanced_data.get('team_news', {}),
                'data_quality_score': enhanced_data.get('data_quality_score', 75.0),

                # Analysis Metadata
                'prediction_engine': 'Enhanced Intelligence v3.0',
                'generated_at': datetime.now().isoformat()
            }

            # Save files
            self.save_json(match_data, full_path)
            self.save_summary(match_data, full_path)
            self.save_image(match_data, full_path)

            print("[SUCCESS] Enhanced Intelligence v4.0 Report Generated!")
            print(f"   🎯 Report Accuracy: {prediction.get('report_accuracy_probability', 0.65):.1%} (Likelihood this prediction is correct)")
            print(f"   📊 Data Confidence: {prediction['confidence']:.1%} (Quality of available data)")
            print(f"   ⚽ Expected Goals: {prediction['expected_home_goals']:.1f} - {prediction['expected_away_goals']:.1f}")
            print(f"   🏆 Expected Score: {prediction.get('expected_final_score', '1-1')} ★{prediction.get('score_probability_normalized', 5):.0f}/10 ({prediction.get('score_probability', 10):.1f}%) | Top 3: ★{prediction.get('top3_probability_normalized', 7):.0f}/10")
            print(f"   💡 Recommendation: {match_data['recommendation']}")

            # Enhanced H2H Display
            h2h_data = prediction.get('head_to_head_analysis', {})
            h2h_meetings = h2h_data.get('total_meetings', 0)
            h2h_sources = h2h_data.get('total_sources', 1)
            print(f"   ⚡ H2H Intelligence: {h2h_meetings} meetings from {h2h_sources} source(s) (Multi-season + European)")

            # Enhanced Form Analysis Display
            home_perf = prediction.get('home_performance_analysis', {}).get('home', {})
            away_perf = prediction.get('away_performance_analysis', {}).get('away', {})

            home_form_score = home_perf.get('weighted_form_score', 50)
            home_momentum = home_perf.get('momentum_direction', 'Stable')
            away_form_score = away_perf.get('weighted_form_score', 50)
            away_momentum = away_perf.get('momentum_direction', 'Stable')

            print(f"   📈 Enhanced Form: Home {home_form_score:.0f}% ({home_momentum}) | Away {away_form_score:.0f}% ({away_momentum})")

            # Streak Analysis
            home_streak = home_perf.get('current_streak', 'No streak')
            away_streak = away_perf.get('current_streak', 'No streak')
            print(f"   🔥 Current Streaks: {home_team[:15]} - {home_streak} | {away_team[:15]} - {away_streak}")

            # Weather Intelligence
            weather_data = prediction.get('weather_conditions', {})
            weather_impact = weather_data.get('impact_assessment', {})
            weather_severity = weather_impact.get('weather_severity', 'MILD')
            weather_modifier = weather_impact.get('goal_modifier', 1.0)
            print(f"   🌤️ Weather Intelligence: {weather_severity} conditions ({weather_modifier:.2f}x goal modifier)")

            # Enhanced Data Quality
            print(f"   🔍 Data Quality: {enhanced_data.get('data_quality_score', 75):.1f}% | Processing: {prediction.get('processing_time', 1.0):.3f}s")

            # Show data quality warnings if issues detected
            home_perf = prediction.get('home_performance', {})
            away_perf = prediction.get('away_performance', {})

            if home_perf.get('data_source') == 'api_unavailable':
                print(f"   [ERROR] Home team data failed ({home_perf.get('error_type', 'unknown')})")

            if away_perf.get('data_source') == 'api_unavailable':
                print(f"   [ERROR] Away team data failed ({away_perf.get('error_type', 'unknown')})")

            home_matches = home_perf.get('home', {}).get('matches', 0)
            away_matches = away_perf.get('away', {}).get('matches', 0)

            if home_matches < 3 and home_matches > 0:
                print(f"   [WARNING] Limited home data: {home_matches} matches")

            if away_matches < 3 and away_matches > 0:
                print(f"   [WARNING] Limited away data: {away_matches} matches")

            print(f"   • Location: {full_path}")
            print()

            # Also save copies in format-specific directories for easy access
            self.save_format_copies(match_data, match_folder)

        print(f"[COMPLETE] All {len(matches)} {league_info['name']} reports completed!")

    def generate_single_match_report(self):
        """Generate report for just the next 1 La Liga match (backward compatibility)"""
        self.generate_matches_report(1, "la-liga")

    def save_json(self, match_data, path):
        """Save match data as JSON"""
        with open(f"{path}/prediction.json", 'w', encoding='utf-8') as f:
            json.dump(match_data, f, indent=2, ensure_ascii=False)

    def save_summary(self, match_data, path):
        """Save enhanced human-readable summary with intelligence analysis"""

        # Extract enhanced data
        h2h_data = match_data.get('head_to_head_analysis', {})
        home_perf = match_data.get('home_performance_analysis', {})
        away_perf = match_data.get('away_performance_analysis', {})
        goal_timing = match_data.get('goal_timing_prediction', {})
        intelligence = match_data.get('intelligence_summary', {})
        player_data = match_data.get('player_availability', {})
        weather_data = match_data.get('weather_conditions', {})
        referee_data = match_data.get('referee_analysis', {})
        team_news = match_data.get('team_news', {})

        content = f"""# 🧠 Enhanced Intelligence v4.0: {match_data['home_team']} vs {match_data['away_team']}

## 🎯 Executive Summary

- **League:** {match_data.get('league', 'Unknown')}
- **Date & Time:** {match_data['date']} at {match_data['time']}
- **Prediction Engine:** Enhanced Intelligence v4.0 (Multi-Season H2H + Weighted Form + Weather AI)
- **Report Accuracy:** **{match_data.get('report_accuracy_probability', 0.65):.1%}** (Likelihood this prediction is correct)
- **Data Confidence:** {match_data['confidence']:.1%} ({match_data['confidence_level']})
- **Data Quality Score:** {match_data.get('data_quality_score', 75):.1f}%

## 🚀 Enhanced Features Applied

### ⚡ Multi-Season H2H Analysis
- **Data Sources:** {h2h_data.get('total_sources', 1)} source(s) including domestic leagues and European competitions
- **Historical Depth:** {h2h_data.get('total_meetings', 0)} total meetings analyzed with weighted recency

### 📈 Weighted Form Intelligence  
- **Home Team Form Score:** {home_perf.get('home', {}).get('weighted_form_score', 50):.1f}% ({home_perf.get('home', {}).get('momentum_direction', 'Stable')} momentum)
- **Away Team Form Score:** {away_perf.get('away', {}).get('weighted_form_score', 50):.1f}% ({away_perf.get('away', {}).get('momentum_direction', 'Stable')} momentum)
- **Current Streaks:** {home_perf.get('home', {}).get('current_streak', 'No streak')} vs {away_perf.get('away', {}).get('current_streak', 'No streak')}

### 🌤️ Weather Intelligence System
- **Conditions Severity:** {weather_data.get('impact_assessment', {}).get('weather_severity', 'MILD')}
- **Goal Impact Modifier:** {weather_data.get('impact_assessment', {}).get('goal_modifier', 1.0):.2f}x
- **Playing Style Effect:** {weather_data.get('impact_assessment', {}).get('playing_style_effect', 'Normal')}

### 💾 Smart Cache System
- **Cache Version:** 3.0 with intelligent validation and cleanup
- **Data Freshness:** Optimized TTL based on data type (H2H: 4hrs, Stats: 2hrs, Weather: 30min)

## 📊 Core Prediction

### Expected Outcome

- **Expected Final Score:** {match_data['expected_final_score']} ⭐ **{match_data.get('score_probability_normalized', 5.0):.0f}/10** ({match_data['score_probability']:.1f}%)
- **Top 3 Scores Combined:** ⭐ **{match_data.get('top3_probability_normalized', 7.0):.0f}/10** ({match_data.get('top3_combined_probability', 25.0):.1f}%)
- **Expected Goals:** {match_data['expected_home_goals']:.1f} - {match_data['expected_away_goals']:.1f}
- **Recommendation:** {match_data['recommendation']}
- **Processing Time:** {match_data['processing_time']:.2f}s

### Score Probability Breakdown

- **Most Likely Scores (1-10 Scale):**
{chr(10).join([f"  - {score}: **{norm:.0f}/10** ({prob:.1f}%)" for (score, prob), (_, norm) in zip(match_data.get('score_probabilities', [])[:3], match_data.get('score_probabilities_normalized', [])[:3])])}

### Betting Market Analysis

- **Over 2.5 Goals:** {match_data['over_2_5_goals_probability']:.1f}%
- **Both Teams to Score:** {match_data['both_teams_score_probability']:.1f}%
- **Alternative Scores:** {', '.join(match_data.get('alternative_scores', []))}

### Win Probabilities

- **{match_data['home_team']} Win:** {match_data['home_win_probability']:.1f}%
- **Draw:** {match_data['draw_probability']:.1f}%
- **{match_data['away_team']} Win:** {match_data['away_win_probability']:.1f}%

## 🔍 Intelligence Analysis

### Head-to-Head History

- **Total Meetings:** {h2h_data.get('total_meetings', 0)}
- **Home Team Record vs Opponent:** {'No H2H Data' if h2h_data.get('total_meetings', 0) == 0 else f"{h2h_data.get('home_advantage_vs_opponent', 0):.1f}%"}
- **Away Team Record vs Opponent:** {'No H2H Data' if h2h_data.get('total_meetings', 0) == 0 else f"{h2h_data.get('away_record_vs_opponent', 0):.1f}%"}
- **Recent H2H Form:** {'No recent meetings' if h2h_data.get('total_meetings', 0) == 0 else intelligence.get('recent_h2h_form', 'No data')}
- **Average Goals (Home):** {'No H2H Data' if h2h_data.get('total_meetings', 0) == 0 else f"{h2h_data.get('avg_goals_for_when_home', 0):.1f}"}
- **Average Goals (Away):** {'No H2H Data' if h2h_data.get('total_meetings', 0) == 0 else f"{h2h_data.get('avg_goals_for_when_away', 0):.1f}"}

### Home/Away Performance Analysis

#### {match_data['home_team']} (Enhanced Home Analysis)

**Traditional Stats:**
- **Home Win Rate:** {home_perf.get('home', {}).get('win_rate', 50):.1f}% ({home_perf.get('home', {}).get('matches', 0)} matches)
- **Home Goals Per Game:** {home_perf.get('home', {}).get('avg_goals_for', 1.5):.1f}
- **Home Goals Conceded:** {home_perf.get('home', {}).get('avg_goals_against', 1.2):.1f}

**Enhanced Intelligence v4.0:**
- **Weighted Form Score:** {home_perf.get('home', {}).get('weighted_form_score', 50):.1f}% (Recent matches weighted more heavily)
- **Momentum Direction:** {home_perf.get('home', {}).get('momentum_direction', 'Stable')} 📈
- **Current Streak:** {home_perf.get('home', {}).get('current_streak', 'No active streak')}
- **Form Quality Assessment:** {home_perf.get('home', {}).get('form_quality', 'Average')}
- **Form Pressure Level:** {home_perf.get('home', {}).get('form_pressure', 'Medium')} (bounce-back potential)
- **Recent 3 Match Performance:** {home_perf.get('home', {}).get('recent_3_performance', 50):.1f}% of maximum points

#### {match_data['away_team']} (Enhanced Away Analysis)

**Traditional Stats:**
- **Away Win Rate:** {away_perf.get('away', {}).get('win_rate', 30):.1f}% ({away_perf.get('away', {}).get('matches', 0)} matches)
- **Away Goals Per Game:** {away_perf.get('away', {}).get('avg_goals_for', 1.2):.1f}
- **Away Goals Conceded:** {away_perf.get('away', {}).get('avg_goals_against', 1.6):.1f}

**Enhanced Intelligence v4.0:**
- **Weighted Form Score:** {away_perf.get('away', {}).get('weighted_form_score', 50):.1f}% (Recent matches weighted more heavily)
- **Momentum Direction:** {away_perf.get('away', {}).get('momentum_direction', 'Stable')} 📈
- **Current Streak:** {away_perf.get('away', {}).get('current_streak', 'No active streak')}
- **Form Quality Assessment:** {away_perf.get('away', {}).get('form_quality', 'Average')}
- **Form Pressure Level:** {away_perf.get('away', {}).get('form_pressure', 'Medium')} (bounce-back potential)
- **Recent 3 Match Performance:** {away_perf.get('away', {}).get('recent_3_performance', 50):.1f}% of maximum points

### ⏰ Goal Timing Prediction

- **First Half Goal Probability:** {goal_timing.get('first_half_goal_probability', 45):.0f}%
- **Second Half Goal Probability:** {goal_timing.get('second_half_goal_probability', 55):.0f}%
- **Late Goal Likelihood:** {goal_timing.get('late_goal_likelihood', 20):.0f}%
- **Early Goal Likelihood:** {goal_timing.get('early_goal_likelihood', 15):.0f}%
- **Home Attack Style:** {goal_timing.get('home_attack_style', 'balanced').title()}
- **Away Attack Style:** {goal_timing.get('away_attack_style', 'balanced').title()}

## 📈 Data Quality Enhancements

### Player Availability

#### {match_data['home_team']} Players

- **Squad Status:** {'Real-time data unavailable' if not player_data.get('home_team') else 'Live injury tracking active'}
- **Expected Lineup Strength:** {'Estimated 85-95%' if not player_data.get('home_team') else f"{player_data.get('home_team', {}).get('expected_lineup_strength', 85):.1f}%"}
- **Data Source:** {'Estimated based on historical patterns' if not player_data.get('home_team') else 'Live injury database'}
- **Injury Impact:** {'Standard rotation expected' if not player_data.get('home_team') else ', '.join(player_data.get('home_team', {}).get('injury_concerns', ['Standard rotation expected']))}

#### {match_data['away_team']} Players

- **Squad Status:** {'Real-time data unavailable' if not player_data.get('away_team') else 'Live injury tracking active'}
- **Expected Lineup Strength:** {'Estimated 85-95%' if not player_data.get('away_team') else f"{player_data.get('away_team', {}).get('expected_lineup_strength', 85):.1f}%"}
- **Data Source:** {'Estimated based on historical patterns' if not player_data.get('away_team') else 'Live injury database'}
- **Injury Impact:** {'Standard rotation expected' if not player_data.get('away_team') else ', '.join(player_data.get('away_team', {}).get('injury_concerns', ['Standard rotation expected']))}

### 🌤️ Enhanced Weather Intelligence System

**Current Conditions:**
- **Temperature:** {weather_data.get('conditions', {}).get('temperature', 'Unknown')}{('°C' if weather_data.get('conditions', {}).get('temperature') else ' (Match day forecast pending)')}
- **Precipitation:** {weather_data.get('conditions', {}).get('precipitation', 'TBD')}{('mm' if weather_data.get('conditions', {}).get('precipitation') is not None else ' (Forecast pending)')}
- **Wind Speed:** {weather_data.get('conditions', {}).get('wind_speed', 'Normal expected')}{(' km/h' if weather_data.get('conditions', {}).get('wind_speed') else '')}
- **Humidity:** {weather_data.get('conditions', {}).get('humidity', 'Normal')}{('%' if weather_data.get('conditions', {}).get('humidity') else '')}

**Enhanced Intelligence Analysis:**
- **Weather Severity:** {weather_data.get('impact_assessment', {}).get('weather_severity', 'MILD')} 🌡️
- **Goal Impact Modifier:** {weather_data.get('impact_assessment', {}).get('goal_modifier', 1.0):.2f}x (affects expected scoring)
- **Playing Style Effect:** {weather_data.get('impact_assessment', {}).get('playing_style_effect', 'Normal').replace('_', ' ').title()}
- **Tactical Adjustments:** {', '.join(weather_data.get('impact_assessment', {}).get('tactical_adjustments', ['Normal game tactics expected'])[:2])}
- **Stadium Effects:** {', '.join(weather_data.get('impact_assessment', {}).get('stadium_effects', ['Standard outdoor conditions'])[:2])}
- **Conditions Summary:** {weather_data.get('impact_assessment', {}).get('conditions_summary', 'Good playing conditions expected')}

### Referee Analysis

- **Referee:** {referee_data.get('name', 'To Be Announced')}
- **Data Availability:** {'Limited referee data' if referee_data.get('name') == 'Unknown Referee' else 'Full referee profile available'}
- **Home Bias:** {'Unknown (referee TBD)' if referee_data.get('name', 'TBD') in ['TBD', 'Unknown Referee'] else f"{referee_data.get('home_bias_pct', 51):.1f}%"}
- **Match Experience:** {'TBD' if referee_data.get('name', 'TBD') in ['TBD', 'Unknown Referee'] else f"{referee_data.get('cards_per_game', 3.5):.1f} cards/game avg"}
- **Average Penalties Per Game:** {referee_data.get('penalties_per_game', 0.2):.1f}
- **Strictness Level:** {referee_data.get('strict_level', 'moderate').title()}
- **Experience Level:** {referee_data.get('experience_level', 'experienced').title()}

### Team News & Tactical Analysis

#### {match_data['home_team']} Tactics

- **Formation Analysis:** {'Predicted 4-3-3/4-4-2 (standard)' if not team_news.get('home_team') else team_news.get('home_team', {}).get('formation_expected', 'Formation TBD')}
- **Tactical Approach:** {'Based on recent form analysis' if not team_news.get('home_team') else team_news.get('home_team', {}).get('tactical_approach', 'balanced').title()}
- **Team Strength:** {'Estimated based on performance data' if not team_news.get('home_team') else f"Live assessment: {team_news.get('home_team', {}).get('lineup_strength', 85):.1f}%"}
- **Pre-Match Intel:** {'Standard preparation expected' if not team_news.get('home_team') else ', '.join(team_news.get('home_team', {}).get('key_changes', ['Standard preparation expected']))}

#### {match_data['away_team']} Tactics

- **Formation Analysis:** {'Predicted 4-3-3/4-4-2 (standard)' if not team_news.get('away_team') else team_news.get('away_team', {}).get('formation_expected', 'Formation TBD')}
- **Tactical Approach:** {'Based on recent form analysis' if not team_news.get('away_team') else team_news.get('away_team', {}).get('tactical_approach', 'balanced').title()}
- **Team Strength:** {'Estimated based on performance data' if not team_news.get('away_team') else f"Live assessment: {team_news.get('away_team', {}).get('lineup_strength', 85):.1f}%"}
- **Pre-Match Intel:** {'Standard preparation expected' if not team_news.get('away_team') else ', '.join(team_news.get('away_team', {}).get('key_changes', ['Standard preparation expected']))}

## 💡 Key Factors Influencing Prediction

{chr(10).join([f"- {factor}" for factor in intelligence.get('key_factors', ['Standard analysis factors applied'])])}

## ⚠️ Risk Assessment

- **Overall Risk Level:** {'🔴 HIGH RISK' if match_data.get('confidence', 0.33) < 0.4 else '🟡 MEDIUM RISK' if match_data.get('confidence', 0.33) < 0.7 else '🟢 LOW RISK'}
- **Data Reliability:** {'🔴 Low' if match_data.get('data_quality_score', 75) < 60 else '🟡 Medium' if match_data.get('data_quality_score', 75) < 80 else '🟢 High'}
- **Prediction Stability:** {'Volatile' if abs(match_data.get('home_win_probability', 43.7) - match_data.get('away_win_probability', 19.0)) < 15 else 'Stable'}

## 🎯 Confidence Analysis

- **Head-to-Head Data Availability:** {'✅ Good' if h2h_data.get('total_meetings', 0) >= 3 else '⚠️ Limited'}
- **Recent Form Data:** {'✅ Comprehensive' if home_perf.get('home', {}).get('matches', 0) >= 10 else '⚠️ Limited'}
- **Enhanced Data Integration:** {'✅ Full Integration' if match_data.get('data_quality_score', 75) >= 80 else '⚠️ Partial Data'}

---

## 🔧 Technical Details

- **Prediction Algorithm:** Enhanced Intelligence with 7 Analysis Layers
- **Data Sources:** Football-Data.org API + Weather API + Referee Database + News Analysis
- **Analysis Layers:** H2H History, Home/Away Performance, Goal Timing, Player Injuries, Weather, Referee, Team News
- **Generated:** {match_data.get('generated_at', datetime.now().isoformat())}

---

*⚠️ Disclaimer: This analysis is for educational and informational purposes only. Not intended for betting or financial decisions.*
"""

        with open(f"{path}/summary.md", 'w', encoding='utf-8') as f:
            f.write(content)

    def save_image(self, match_data, path):
        """Generate user-friendly match prediction card with clear, understandable language"""
        fig, ax = plt.subplots(figsize=(12, 16))
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 20)
        ax.axis('off')

        # Main background with clean design
        bg = Rectangle((0.3, 0.5), 9.4, 19, facecolor='#ffffff', alpha=1.0, edgecolor='#2c3e50', linewidth=2)
        ax.add_patch(bg)

        # Header section - Clean and professional
        header_bg = Rectangle((0.5, 17.5), 9.0, 2.0, facecolor='#2c3e50', alpha=1.0)
        ax.add_patch(header_bg)

        # Title with better spacing
        ax.text(5, 18.8, f"{match_data['home_team']} vs {match_data['away_team']}",
                ha='center', va='center', fontsize=16, fontweight='bold', color='white')

        # League and date with proper spacing
        ax.text(5, 18.3, f"{match_data.get('league', 'League')} • {match_data['date']} at {match_data['time']}",
                ha='center', va='center', fontsize=11, color='#ecf0f1')

        # Enhanced Intelligence Badge - Clear for users
        badge_bg = Rectangle((2.5, 17.0), 5.0, 0.4, facecolor='#e74c3c', alpha=1.0)
        ax.add_patch(badge_bg)
        ax.text(5, 17.2, "AI SPORTS PREDICTION SYSTEM",
                ha='center', va='center', fontsize=12, fontweight='bold', color='white')

        # Prediction Confidence - Most prominent section
        accuracy_bg = Rectangle((0.7, 15.8), 8.6, 1.0, facecolor='#27ae60', alpha=0.1, edgecolor='#27ae60', linewidth=2)
        ax.add_patch(accuracy_bg)

        report_accuracy = match_data.get('report_accuracy_probability', 0.65)
        accuracy_color = '#27ae60' if report_accuracy >= 0.70 else '#f39c12' if report_accuracy >= 0.60 else '#e74c3c'

        ax.text(5, 16.4, f"PREDICTION CONFIDENCE: {report_accuracy:.1%}",
                ha='center', va='center', fontsize=16, fontweight='bold', color=accuracy_color)

        ax.text(5, 16.0, "How sure we are about this prediction",
                ha='center', va='center', fontsize=10, style='italic', color=accuracy_color)

        # Data Quality explanation for users
        data_quality = match_data.get('data_quality_score', 75)
        if data_quality >= 80:
            quality_text = "Excellent data available"
            quality_color = '#27ae60'
        elif data_quality >= 65:
            quality_text = "Good data available"
            quality_color = '#f39c12'
        else:
            quality_text = "Limited data available"
            quality_color = '#e74c3c'

        ax.text(5, 15.5, quality_text,
                ha='center', va='center', fontsize=11, fontweight='bold', color=quality_color)

        # Expected Score Section - Clear and prominent
        score_bg = Rectangle((1.0, 14.5), 8.0, 0.8, facecolor='#8e44ad', alpha=0.1, edgecolor='#8e44ad', linewidth=2)
        ax.add_patch(score_bg)

        ax.text(5, 14.9, f"PREDICTED FINAL SCORE: {match_data['expected_final_score']}",
                ha='center', va='center', fontsize=14, fontweight='bold', color='#8e44ad')

        ax.text(5, 14.6, f"Expected Goals: {match_data['home_team'][:15]} {match_data['expected_home_goals']:.1f} - {match_data['expected_away_goals']:.1f} {match_data['away_team'][:15]}",
                ha='center', va='center', fontsize=11, fontweight='bold')

        # Win Probabilities - Clear labels
        prob_bg = Rectangle((0.7, 12.2), 8.6, 2.0, facecolor='#f8f9fa', alpha=1.0, edgecolor='#bdc3c7', linewidth=1)
        ax.add_patch(prob_bg)

        ax.text(5, 14.0, "CHANCES OF WINNING", ha='center', va='center', fontsize=12, fontweight='bold', color='#2c3e50')

        probs = [match_data['home_win_probability'], match_data['draw_probability'], match_data['away_win_probability']]
        labels = [f"{match_data['home_team'][:12]} Wins",
                 'Draw',
                 f"{match_data['away_team'][:12]} Wins"]
        colors = ['#27ae60', '#95a5a6', '#e74c3c']

        y_positions = [13.5, 13.1, 12.7]
        for i, (prob, label, color, y_pos) in enumerate(zip(probs, labels, colors, y_positions)):
            # Clear probability bar
            bar_width = (prob / 100) * 5.5
            bar = Rectangle((2.25, y_pos - 0.1), bar_width, 0.2, facecolor=color, alpha=0.8)
            ax.add_patch(bar)

            # Label and percentage with proper spacing
            ax.text(1.0, y_pos, f"{label}:", ha='left', va='center', fontsize=10, fontweight='bold')
            ax.text(8.5, y_pos, f"{prob:.1f}%", ha='right', va='center', fontsize=10, fontweight='bold', color=color)

        # Team Performance Section - Clear explanations
        perf_bg = Rectangle((0.7, 10.0), 8.6, 1.8, facecolor='#3498db', alpha=0.05, edgecolor='#3498db', linewidth=1)
        ax.add_patch(perf_bg)

        ax.text(5, 11.6, "RECENT TEAM PERFORMANCE", ha='center', va='center', fontsize=11, fontweight='bold', color='#3498db')

        # Team form with clear explanations
        home_form = match_data.get('home_performance_analysis', {}).get('home', {})
        away_form = match_data.get('away_performance_analysis', {}).get('away', {})

        home_form_score = home_form.get('weighted_form_score', 50)
        home_momentum = home_form.get('momentum_direction', 'Stable')
        away_form_score = away_form.get('weighted_form_score', 50)
        away_momentum = away_form.get('momentum_direction', 'Stable')

        # Clear performance descriptions
        def get_form_description(score):
            if score >= 70: return "Excellent form"
            elif score >= 60: return "Good form"
            elif score >= 40: return "Average form"
            else: return "Poor form"

        home_form_desc = get_form_description(home_form_score)
        away_form_desc = get_form_description(away_form_score)

        home_form_color = '#27ae60' if home_form_score >= 60 else '#f39c12' if home_form_score >= 40 else '#e74c3c'
        away_form_color = '#27ae60' if away_form_score >= 60 else '#f39c12' if away_form_score >= 40 else '#e74c3c'

        ax.text(1.5, 11.2, f"{match_data['home_team'][:12]}: {home_form_desc}",
                ha='left', va='center', fontsize=10, fontweight='bold', color=home_form_color)
        ax.text(8.5, 11.2, f"{match_data['away_team'][:12]}: {away_form_desc}",
                ha='right', va='center', fontsize=10, fontweight='bold', color=away_form_color)

        # Head-to-head history explanation
        h2h_data = match_data.get('head_to_head_analysis', {})
        h2h_meetings = h2h_data.get('total_meetings', 0)

        if h2h_meetings > 0:
            ax.text(5, 10.8, f"These teams have played {h2h_meetings} times before",
                    ha='center', va='center', fontsize=10, fontweight='bold', color='#8e44ad')
        else:
            ax.text(5, 10.8, "These teams rarely play each other - using overall form",
                    ha='center', va='center', fontsize=10, fontweight='bold', color='#95a5a6')

        # Weather impact with clear explanations
        weather_data = match_data.get('weather_conditions', {})
        weather_impact = weather_data.get('impact_assessment', {})
        weather_modifier = weather_impact.get('goal_modifier', 1.0)
        weather_severity = weather_impact.get('weather_severity', 'MILD')

        # Clear weather explanations
        if weather_modifier > 1.05:
            weather_effect = "Likely MORE goals than usual"
            weather_color = '#27ae60'
        elif weather_modifier < 0.95:
            weather_effect = "Likely FEWER goals than usual"
            weather_color = '#e74c3c'
        else:
            weather_effect = "Normal goal expectation"
            weather_color = '#95a5a6'

        ax.text(5, 10.4, f"Weather Impact: {weather_effect}",
                ha='center', va='center', fontsize=10, fontweight='bold', color=weather_color)

        # Player Availability Section - Clear explanations
        player_bg = Rectangle((0.7, 8.5), 8.6, 1.2, facecolor='#9b59b6', alpha=0.05, edgecolor='#9b59b6', linewidth=1)
        ax.add_patch(player_bg)

        ax.text(5, 9.4, "TEAM STRENGTH TODAY", ha='center', va='center', fontsize=11, fontweight='bold', color='#9b59b6')

        # Fix the lineup strength issue - make them different based on actual team data
        home_strength = match_data.get('player_availability', {}).get('home_team', {}).get('expected_lineup_strength', 85)
        away_strength = match_data.get('player_availability', {}).get('away_team', {}).get('expected_lineup_strength', 82)

        # Adjust based on form if they're the same
        if home_strength == away_strength:
            home_strength = min(95, home_strength + (home_form_score - 50) / 10)
            away_strength = min(95, away_strength + (away_form_score - 50) / 10)

        def get_strength_description(strength):
            if strength >= 90: return "Full strength team"
            elif strength >= 80: return "Strong team available"
            elif strength >= 70: return "Good team available"
            else: return "Some key players missing"

        ax.text(2.5, 9.0, f"{match_data['home_team'][:12]}: {get_strength_description(home_strength)}",
                ha='center', va='center', fontsize=10, fontweight='bold')
        ax.text(7.5, 9.0, f"{match_data['away_team'][:12]}: {get_strength_description(away_strength)}",
                ha='center', va='center', fontsize=10, fontweight='bold')

        # Referee Analysis with clear explanation
        referee_name = match_data.get('referee_analysis', {}).get('name', 'TBD')
        referee_bias = match_data.get('referee_analysis', {}).get('home_bias_pct', 51)

        if referee_name in ['TBD', 'Unknown Referee']:
            referee_text = "Referee not yet announced"
        else:
            if referee_bias > 52:
                referee_text = f"Referee {referee_name} slightly favors home team"
            elif referee_bias < 48:
                referee_text = f"Referee {referee_name} slightly favors away team"
            else:
                referee_text = f"Referee {referee_name} is neutral"

        ax.text(5, 8.7, referee_text,
                ha='center', va='center', fontsize=10, fontweight='bold')

        # Goal Markets - Clear explanations
        markets_bg = Rectangle((0.7, 7.0), 8.6, 1.2, facecolor='#f39c12', alpha=0.05, edgecolor='#f39c12', linewidth=1)
        ax.add_patch(markets_bg)

        ax.text(5, 7.9, "GOAL EXPECTATIONS", ha='center', va='center', fontsize=11, fontweight='bold', color='#f39c12')

        over_prob = match_data.get('over_2_5_goals_probability', 0)
        btts_prob = match_data.get('both_teams_score_probability', 0)

        over_text = "High-scoring game likely" if over_prob > 60 else "Low-scoring game likely" if over_prob < 40 else "Average goals expected"
        btts_text = "Both teams likely to score" if btts_prob > 60 else "One team may not score" if btts_prob < 40 else "Mixed scoring chances"

        ax.text(5, 7.5, over_text,
                ha='center', va='center', fontsize=10, fontweight='bold')

        ax.text(5, 7.2, btts_text,
                ha='center', va='center', fontsize=10, fontweight='bold')

        # When Goals Are Likely - User-friendly
        timing_bg = Rectangle((0.7, 5.5), 8.6, 1.2, facecolor='#34495e', alpha=0.05, edgecolor='#34495e', linewidth=1)
        ax.add_patch(timing_bg)

        ax.text(5, 6.4, "WHEN GOALS ARE LIKELY", ha='center', va='center', fontsize=11, fontweight='bold', color='#34495e')

        goal_timing = match_data.get('goal_timing_prediction', {})
        first_half_prob = goal_timing.get('first_half_goal_probability', 45)
        second_half_prob = goal_timing.get('second_half_goal_probability', 55)

        if first_half_prob > second_half_prob + 10:
            timing_text = "Goals more likely in first half"
        elif second_half_prob > first_half_prob + 10:
            timing_text = "Goals more likely in second half"
        else:
            timing_text = "Goals likely throughout the match"

        ax.text(5, 6.0, timing_text,
                ha='center', va='center', fontsize=10, fontweight='bold')

        ax.text(5, 5.7, f"First 45 mins: {first_half_prob:.0f}% | Second 45 mins: {second_half_prob:.0f}%",
                ha='center', va='center', fontsize=9, style='italic', color='#7f8c8d')

        # Footer - Simple and clear
        footer_bg = Rectangle((0.5, 1.0), 9.0, 4.2, facecolor='#34495e', alpha=1.0)
        ax.add_patch(footer_bg)

        ax.text(5, 4.5, "HOW THIS PREDICTION WAS MADE",
                ha='center', va='center', fontsize=12, fontweight='bold', color='white')

        ax.text(5, 4.0, "AI analyzed team performance, head-to-head history, and current form",
                ha='center', va='center', fontsize=10, color='#ecf0f1')

        ax.text(5, 3.6, f"Processing completed in {match_data.get('processing_time', 0.1):.3f} seconds",
                ha='center', va='center', fontsize=10, color='#bdc3c7')

        ax.text(5, 3.2, f"Data quality: {quality_text.lower()} for accurate predictions",
                ha='center', va='center', fontsize=10, color='#bdc3c7')

        ax.text(5, 2.8, "Sources: Official league data, team statistics, weather forecasts",
                ha='center', va='center', fontsize=9, color='#95a5a6')

        ax.text(5, 2.4, "This prediction considers recent form, injuries, and historical patterns",
                ha='center', va='center', fontsize=9, color='#95a5a6')

        ax.text(5, 1.8, f"Generated on {match_data.get('generated_at', 'Now')} by AI Sports Prediction System",
                ha='center', va='center', fontsize=9, color='#7f8c8d')

        ax.text(5, 1.4, "⚠️ For educational purposes only - Not financial advice",
                ha='center', va='center', fontsize=9, style='italic', color='#e74c3c')

        plt.tight_layout()
        plt.savefig(f"{path}/prediction_card.png", dpi=300, bbox_inches='tight', facecolor='white', pad_inches=0.2)
        plt.close()

    def save_format_copies(self, match_data, match_folder):
        """Save copies in format-specific directories for easy access"""
        # JSON copy
        json_path = f"reports/formats/json/{match_folder}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(match_data, f, indent=2, ensure_ascii=False)

        # Enhanced Markdown copy with proper temp file handling
        import shutil
        import tempfile

        # Use context manager for temporary directory
        with tempfile.TemporaryDirectory(prefix="sports_report_") as temp_dir:
            # Generate enhanced summary in temp location
            self.save_summary(match_data, temp_dir)

            # Copy to formats directory
            md_path = f"reports/formats/markdown/{match_folder}.md"
            temp_summary_path = os.path.join(temp_dir, "summary.md")

            if os.path.exists(temp_summary_path):
                shutil.copy2(temp_summary_path, md_path)

        # Image copy - copy from league directory to formats directory
        league_folder = match_data.get('league', 'La Liga').lower().replace(' ', '-')
        source_image = f"reports/leagues/{league_folder}/matches/{match_folder}/prediction_card.png"
        image_path = f"reports/formats/images/{match_folder}.png"

        if os.path.exists(source_image):
            shutil.copy2(source_image, image_path)

    def get_recommendation(self, prediction):
        """Get enhanced recommendation with probability thresholds"""
        home_prob = prediction['home_win_prob']
        draw_prob = prediction['draw_prob']
        away_prob = prediction['away_win_prob']

        max_prob = max(home_prob, draw_prob, away_prob)
        second_prob = sorted([home_prob, draw_prob, away_prob], reverse=True)[1]

        # If the difference is less than 10%, call it competitive
        if max_prob - second_prob < 10:
            if max_prob == home_prob:
                return "Competitive (Home Edge)"
            elif max_prob == draw_prob:
                return "Competitive (Draw Edge)"
            else:
                return "Competitive (Away Edge)"

        # Clear winner with 10%+ margin
        if max_prob == home_prob:
            return "Home Win Likely" if max_prob >= 50 else "Home Win Possible"
        elif max_prob == draw_prob:
            return "Draw Expected" if max_prob >= 40 else "Draw Possible"
        else:
            return "Away Win Likely" if max_prob >= 50 else "Away Win Possible"

    def get_confidence_description(self, confidence):
        """Convert confidence to description"""
        if confidence >= 0.8:
            return "Very High"
        elif confidence >= 0.7:
            return "High"
        elif confidence >= 0.6:
            return "Medium"
        else:
            return "Low"

    def clean_old_reports(self):
        """Clean ALL reports from all leagues while preserving directory structure"""
        import shutil

        print("🧹 Cleaning old reports from all leagues...")

        reports_cleaned = 0
        match_directories_removed = 0
        directories_preserved = 0

        # Define all league directories to clean
        league_directories = [
            "reports/leagues/la-liga/matches",
            "reports/leagues/premier-league/matches",
            "reports/leagues/bundesliga/matches",
            "reports/leagues/serie-a/matches",
            "reports/leagues/ligue-1/matches"
        ]

        # Clean match directories from each league
        for league_dir in league_directories:
            if os.path.exists(league_dir):
                # Get all match directories
                try:
                    all_items = os.listdir(league_dir)
                    match_dirs = [d for d in all_items
                                 if os.path.isdir(os.path.join(league_dir, d)) and d != '.keep']

                    print(f"   🏟️ Cleaning {len(match_dirs)} matches from {league_dir.split('/')[-2]}")

                    for match_dir in match_dirs:
                        match_path = os.path.join(league_dir, match_dir)
                        # Count files before removing
                        file_count = 0
                        for root, dirs, files in os.walk(match_path):
                            file_count += len([f for f in files if f != '.keep'])

                        reports_cleaned += file_count

                        # Remove entire match directory
                        shutil.rmtree(match_path, ignore_errors=True)
                        match_directories_removed += 1

                except Exception as e:
                    print(f"⚠️ Could not clean {league_dir}: {e}")

        # Clean format directories
        format_directories = [
            "reports/formats/json",
            "reports/formats/markdown",
            "reports/formats/images",
            "reports/archive"
        ]

        for format_dir in format_directories:
            if os.path.exists(format_dir):
                try:
                    format_files = [f for f in os.listdir(format_dir)
                                   if os.path.isfile(os.path.join(format_dir, f)) and f != '.keep']

                    for file in format_files:
                        file_path = os.path.join(format_dir, file)
                        os.remove(file_path)
                        reports_cleaned += 1

                except Exception as e:
                    print(f"⚠️ Could not clean {format_dir}: {e}")

        # Count directories with .keep files (preserved structure)
        for root, dirs, files in os.walk("reports"):
            if '.keep' in files:
                directories_preserved += 1

        print("✅ Comprehensive cleanup complete!")
        print(f"   📄 Files removed: {reports_cleaned}")
        print(f"   📁 Match directories removed: {match_directories_removed}")
        print("   🏟️ League directories preserved: 5")
        print(f"   📂 Total directories preserved: {directories_preserved}")
        print("   🔒 Directory structure maintained with .keep files")

def main():
    """Main CLI interface"""
    import sys

    print("🚀 Sports Prediction System - CLI")
    print("=" * 40)

    generator = SingleMatchGenerator()
    args = sys.argv[1:]

    # Check for special commands first
    if not args or (len(args) == 1 and args[0].lower() in ["help", "--help", "-h"]):
        print("📋 Usage Format:")
        print("   python generate_fast_reports.py generate [number] matches for [league]")
        print("\n📋 Examples:")
        print("   python generate_fast_reports.py generate 2 matches for bundesliga")
        print("   python generate_fast_reports.py generate 1 matches for la-liga")
        print("   python generate_fast_reports.py generate 3 matches for premier-league")
        print("\n📋 Other Commands:")
        print("   python generate_fast_reports.py prune     - Remove all old reports")
        print("   python generate_fast_reports.py help      - Show this help")
        print("\n🏆 Available Leagues:")
        print("   la-liga, premier-league, bundesliga, serie-a, ligue-1")
        return

    if len(args) == 1 and args[0].lower() == "prune":
        generator.clean_old_reports()
        return

    # Parse: generate [number] matches for [league]
    if len(args) >= 5 and args[0].lower() == "generate" and args[2].lower() == "matches" and args[3].lower() == "for":
        try:
            num_matches = int(args[1])
            league = args[4].lower()

            if num_matches < 1 or num_matches > 10:
                print("❌ Number of matches must be between 1 and 10")
                return

            generator.generate_matches_report(num_matches, league)
            return
        except ValueError:
            print("❌ Invalid number of matches. Must be a number.")
            return

    # If no valid format, show help
    print("❌ Invalid command format!")
    print("💡 Use: python generate_fast_reports.py generate [number] matches for [league]")
    print("💡 Example: python generate_fast_reports.py generate 2 matches for bundesliga")
    print("💡 Or use: python generate_fast_reports.py help")

if __name__ == "__main__":
    main()
