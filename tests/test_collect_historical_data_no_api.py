import os
from importlib import import_module
from pathlib import Path


def test_collect_historical_data_no_api_runs(tmp_path):
    # Ensure no API env vars are set
    os.environ.pop('FOOTBALL_DATA_API_KEY', None)
    os.environ.pop('API_FOOTBALL_KEY', None)
    os.environ.pop('COLLECT_SEASONS', None)

    # Run the collector
    module = import_module('scripts.collect_historical_data')
    module.main()

    # Check output file
    out_path = Path('data/processed/historical/historical_dataset.json')
    assert out_path.exists()
    data = out_path.read_text(encoding='utf-8')
    assert 'processed' in data
