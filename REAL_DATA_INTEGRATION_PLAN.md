# Real Data Sources Integration Plan

## 🚑 Player Injury Data Sources

### Injury Data Options

1. **Transfermarkt API** (Community/Unofficial)
   - URL: `https://transfermarkt-api.vercel.app/`
   - Data: Real-time injuries, suspensions, player availability
   - Cost: Free (rate limited)
   - Coverage: Global leagues

2. **Football API (RapidAPI)**
   - URL: `https://rapidapi.com/api-sports/api/api-football`
   - Endpoint: `/injuries` - Live injury reports
   - Cost: Free tier available
   - Coverage: Major European leagues

3. **SportsRadar** (Premium)
   - URL: `https://developer.sportradar.com/`
   - Data: Official injury reports, player status
   - Cost: Paid (high accuracy)

### Injury Data Implementation

```python
# New file: app/data/injury_connector.py
class InjuryDataConnector:
    def get_team_injuries(self, team_id: int, league: str) -> Dict:
        # Query transfermarkt or football-api
        # Return real injury list with dates, severity
```

## 👨‍⚽ Referee Data Sources

### Referee Data Options

1. **Football-Data.org Extended**
   - Already has referee assignments for upcoming matches
   - Need to extract referee names from fixture data

2. **Referee Statistics Database**
   - URL: `https://www.worldfootball.net/referees/`
   - Data: Historical referee statistics
   - Cost: Web scraping (free)

3. **UEFA/FIFA Official Data**
   - URL: Various official sources
   - Data: Referee appointments, statistics
   - Cost: Free but complex parsing

### Implementation Strategy — Referee Data

```python
# Enhanced: app/data/referee_connector.py
class RefereeDataConnector:
    def get_referee_stats(self, referee_name: str) -> Dict:
        # Scrape worldfootball.net or similar
        # Return real stats: cards/game, bias, experience
```

## 📰 Team News Data Sources

### News Data Options

1. **NewsAPI**
   - URL: `https://newsapi.org/`
   - Data: Team news, press conferences, lineup leaks
   - Cost: Free tier (1000 requests/day)

2. **Football News Aggregators**
   - ESPN API, Sky Sports, BBC Sport
   - Data: Team news, injury updates, tactical analysis
   - Cost: Free with rate limits

3. **Social Media Integration**
   - Twitter API for official team accounts
   - Data: Real-time lineup announcements
   - Cost: Free tier available

### Implementation Strategy — Team News

```python
# New file: app/data/news_connector.py
class TeamNewsConnector:
    def get_team_news(self, team_name: str, match_date: str) -> Dict:
        # Query NewsAPI + social media
        # Parse for injuries, lineups, formations
```

## 🏃‍♂️ Lineup Prediction Sources

### Lineup Data Options

1. **Predicted Lineups Websites**
   - URL: `https://www.footballlineups.com/`
   - Data: Crowd-sourced lineup predictions
   - Cost: Free (web scraping)

2. **Fantasy Football APIs**
   - URL: Fantasy Premier League API, etc.
   - Data: Player availability, expected minutes
   - Cost: Free

3. **Football Statistics APIs**
   - URL: Footystats, Understat
   - Data: Player rotation patterns, form
   - Cost: Freemium models

### Implementation Strategy — Lineup Prediction

```python
# New file: app/data/lineup_predictor.py
class LineupPredictor:
    def predict_lineup_strength(self, team_id: int, injuries: List, news: Dict) -> float:
        # Combine injury data + news + historical patterns
        # Return realistic strength percentage
```
