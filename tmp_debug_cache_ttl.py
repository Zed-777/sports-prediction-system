from enhanced_predictor import EnhancedPredictor
p = EnhancedPredictor('FAKEKEY')
p._settings['data_sources'] = {'cache_ttl_by_endpoint':{'api.football-data.org':{'/v4/matches/':3600,'/v4/teams/':7200}}}
print('mapping keys:', list(p._settings['data_sources']['cache_ttl_by_endpoint'].keys()))
# Let's simulate loop logic from function
mapping = {
    'h2h': '/v4/matches/',
    'home_away': '/v4/teams/',
    'weather': '/v1/forecast',
    'odds': '/v4/odds',
    'matches': '/v4/matches/'
}
endpoint_ttls = p._settings['data_sources'].get('cache_ttl_by_endpoint', {})
for key_prefix, endpoint in mapping.items():
    if 'h2h_1_2'.startswith(key_prefix):
        print('Key prefix match:', key_prefix, endpoint)
        for host, paths in endpoint_ttls.items():
            for path_prefix, ttl in (paths or {}).items():
                print('Comparing', endpoint.rstrip('/'), 'vs', str(path_prefix).rstrip('/'), '->', ttl)
                normalized_ep = endpoint.rstrip('/')
                normalized_prefix = str(path_prefix).rstrip('/')
                if normalized_ep.endswith(normalized_prefix) or normalized_ep.startswith(normalized_prefix) or normalized_ep == normalized_prefix:
                    print('MATCH found:', path_prefix, ttl)
                    raise SystemExit
print('No match')
