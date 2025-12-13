from enhanced_predictor import EnhancedPredictor
p = EnhancedPredictor('FAKEKEY')
p._settings['data_sources'] = {'cache_ttl_by_endpoint':{'api.football-data.org':{'/v4/matches/':3600,'/v4/teams/':7200}}}
print('get cache duration:', p._get_intelligent_cache_duration('h2h_1_2', {}))
print('get cache duration for home_away_x:', p._get_intelligent_cache_duration('home_away_1_2', {}))
print('get cache duration for matches_x:', p._get_intelligent_cache_duration('matches_1_2', {}))
