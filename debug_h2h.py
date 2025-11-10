#!/usr/bin/env python3
"""Test H2H data retrieval to debug why teams show no history"""

import requests
import os

def test_h2h_retrieval():
    api_key = os.getenv('FOOTBALL_DATA_API_KEY', '17405508d1774f46a368390ff07f8a31')
    headers = {'X-Auth-Token': api_key}
    
    # Test Real Sociedad (ID: 92) matches
    print("=== Testing Real Sociedad (ID: 92) Recent Matches ===")
    response = requests.get(
        'https://api.football-data.org/v4/teams/92/matches?status=FINISHED&limit=10',
        headers=headers
    )
    
    print(f"Response status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        matches = data.get('matches', [])
        print(f"Total matches found: {len(matches)}")
        
        print("\nRecent matches:")
        for match in matches[:5]:
            home = match['homeTeam']['name']
            away = match['awayTeam']['name']
            date = match['utcDate'][:10]
            home_score = match['score']['fullTime']['home']
            away_score = match['score']['fullTime']['away']
            print(f"  {home} {home_score}-{away_score} {away} ({date})")
    else:
        print(f"API Error: {response.status_code}")
        print(response.text)
    
    print("\n=== Testing Elche (ID: 285) Recent Matches ===")
    response = requests.get(
        'https://api.football-data.org/v4/teams/285/matches?status=FINISHED&limit=10',
        headers=headers
    )
    
    print(f"Response status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        matches = data.get('matches', [])
        print(f"Total matches found: {len(matches)}")
        
        print("\nRecent matches:")
        for match in matches[:5]:
            home = match['homeTeam']['name']
            away = match['awayTeam']['name']
            date = match['utcDate'][:10]
            home_score = match['score']['fullTime']['home']
            away_score = match['score']['fullTime']['away']
            print(f"  {home} {home_score}-{away_score} {away} ({date})")
    else:
        print(f"API Error: {response.status_code}")
        print(response.text)
    
    print("\n=== Manual H2H Search ===")
    # Check if these teams have played historically by looking at each team's matches
    # and filtering for encounters
    
    print("Searching for Elche vs Real Sociedad encounters...")
    elche_response = requests.get(
        'https://api.football-data.org/v4/teams/285/matches?status=FINISHED&limit=50',
        headers=headers
    )
    
    if elche_response.status_code == 200:
        elche_matches = elche_response.json().get('matches', [])
        h2h_matches = []
        
        for match in elche_matches:
            home_id = match['homeTeam']['id']
            away_id = match['awayTeam']['id']
            
            # Check if Real Sociedad (92) was involved
            if (home_id == 285 and away_id == 92) or (home_id == 92 and away_id == 285):
                h2h_matches.append(match)
        
        print(f"Found {len(h2h_matches)} direct encounters:")
        for match in h2h_matches:
            home = match['homeTeam']['name']
            away = match['awayTeam']['name']
            date = match['utcDate'][:10]
            home_score = match['score']['fullTime']['home']
            away_score = match['score']['fullTime']['away']
            print(f"  {home} {home_score}-{away_score} {away} ({date})")
    
    print("\n=== Checking Team IDs ===")
    # Verify the team IDs are correct
    teams_response = requests.get(
        'https://api.football-data.org/v4/competitions/PD/teams',
        headers=headers
    )
    
    if teams_response.status_code == 200:
        teams_data = teams_response.json()
        teams = teams_data.get('teams', [])
        
        print("La Liga teams and IDs:")
        for team in teams:
            if 'elche' in team['name'].lower() or 'sociedad' in team['name'].lower():
                print(f"  {team['name']} (ID: {team['id']})")

if __name__ == '__main__':
    test_h2h_retrieval()