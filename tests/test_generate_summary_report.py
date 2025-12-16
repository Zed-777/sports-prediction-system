import json
from pathlib import Path
from scripts.collect_historical_results import HistoricalResultsCollector


def test_generate_summary_report(tmp_path):
    proj_root = Path(__file__).resolve().parents[1]
    hist_dir = proj_root / 'data' / 'historical'
    hist_dir.mkdir(parents=True, exist_ok=True)
    league = 'la-liga'
    out_file = hist_dir / f'{league}_results.json'
    record = {
        'match_id': 'm1',
        'match_date': '2025-01-01',
        'home_team': 'A',
        'away_team': 'B',
        'prediction': {},
        'actual_result': {'home_score': 1, 'away_score': 0},
        'prediction_correct': True
    }
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump([record], f, indent=2)

    collector = HistoricalResultsCollector()
    path = collector.generate_summary_report(league)
    assert path.endswith('.md')
    p = Path(path)
    assert p.exists()
    txt = p.read_text(encoding='utf-8')
    assert 'Total predictions collected' in txt
    assert 'Overall' in txt
