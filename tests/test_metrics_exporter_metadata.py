import json
from pathlib import Path
from app.utils.metrics import reset_metrics, increment_metric, get_metrics
from scripts import export_metrics


def test_metrics_exporter_writes_metadata_and_metrics(tmp_path: Path):
    # Reset collector
    reset_metrics()
    # Add sample metrics
    increment_metric('api', 'calls', 5)
    increment_metric('api', 'errors', 1)

    out_dir = tmp_path / 'metrics_out'
    out_dir = str(out_dir)
    # Call exporter
    json_file = export_metrics.export_metrics_to_json(out_dir)
    assert Path(json_file).exists()

    with open(json_file, 'r', encoding='utf-8') as f:
        obj = json.load(f)
    assert 'metadata' in obj
    assert 'metrics' in obj
    assert obj['metrics'].get('api', {}).get('calls') == 5
    assert obj['metrics'].get('api', {}).get('errors') == 1
    assert 'run_id' in obj['metadata']
    assert 'timestamp_utc' in obj['metadata']


def test_metrics_exporter_idempotent(tmp_path: Path):
    from scripts import export_metrics
    from pathlib import Path

    out_dir = str(tmp_path / 'metrics_out')
    # Run exporter twice
    file1 = export_metrics.export_metrics_to_json(out_dir)
    file2 = export_metrics.export_metrics_to_json(out_dir)
    assert Path(file1).exists()
    assert Path(file2).exists()
    assert file1 != file2