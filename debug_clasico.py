#!/usr/bin/env python3
"""Test H2H with teams that definitely have history - Real Madrid vs Barcelona"""

import requests
import os

def test_clasico_h2h():
    api_key = os.getenv('FOOTBALL_DATA_API_KEY', '17405508d1774f46a368390ff07f8a31')
    headers = {'X-Auth-Token': api_key}
    
    # Get La Liga teams to find Real Madrid and Barcelona IDs
    print("=== Finding Real Madrid and Barcelona IDs ===")
    teams_response = requests.get(
        'https://api.football-data.org/v4/competitions/PD/teams',
        headers=headers
    )
    
    real_madrid_id = None
    barcelona_id = None
    
    if teams_response.status_code == 200:
        teams = teams_response.json().get('teams', [])
        for team in teams:
            if 'real madrid' in team['name'].lower():
                real_madrid_id = team['id']
                print(f"Real Madrid: {team['name']} (ID: {team['id']})")
            elif 'barcelona' in team['name'].lower():
                barcelona_id = team['id']
                print(f"Barcelona: {team['name']} (ID: {team['id']})")
    
    if not real_madrid_id or not barcelona_id:
        print("Could not find team IDs")
        return
    
    print(f"\n=== Testing El Clasico H2H (Real Madrid {real_madrid_id} vs Barcelona {barcelona_id}) ===")
    
    # Get Real Madrid matches and look for Barcelona encounters
    response = requests.get(
        f'https://api.football-data.org/v4/teams/{real_madrid_id}/matches?status=FINISHED&limit=50',
        headers=headers
    )
    
    if response.status_code == 200:
        matches = response.json().get('matches', [])
        h2h_matches = []
        
        for match in matches:
            home_id = match['homeTeam']['id']
            away_id = match['awayTeam']['id']
            
            # Check if Barcelona was involved
            if (home_id == real_madrid_id and away_id == barcelona_id) or \
               (home_id == barcelona_id and away_id == real_madrid_id):
                h2h_matches.append(match)
        
        print(f"Found {len(h2h_matches)} El Clasico encounters in recent history:")
        for match in h2h_matches[:10]:  # Show last 10
            home = match['homeTeam']['name']
            away = match['awayTeam']['name']
            date = match['utcDate'][:10]
            home_score = match['score']['fullTime']['home']
            away_score = match['score']['fullTime']['away']
            print(f"  {home} {home_score}-{away_score} {away} ({date})")
        
        if len(h2h_matches) == 0:
            print("❌ PROBLEM: No El Clasico matches found - this indicates an issue!")
            print("Recent Real Madrid matches:")
            for match in matches[:5]:
                home = match['homeTeam']['name']
                away = match['awayTeam']['name']
                date = match['utcDate'][:10]
                print(f"  {home} vs {away} ({date})")
    else:
        print(f"API Error: {response.status_code}")

if __name__ == '__main__':
    test_clasico_h2h()