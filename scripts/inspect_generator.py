import importlib
m = importlib.import_module('generate_fast_reports')
cls = m.SingleMatchGenerator
print('methods count:', len([n for n in dir(cls) if callable(getattr(cls,n)) and not n.startswith('__')]))
print('has get_confidence_description?', hasattr(cls,'get_confidence_description'))
print('has get_recommendation?', hasattr(cls,'get_recommendation'))
print('has _safe_float?', hasattr(cls,'_safe_float'))
print('has normalize_team_name?', hasattr(cls,'normalize_team_name'))
print('sample methods:', [n for n in dir(cls) if n.startswith('get_') or n.startswith('format')][:20])
