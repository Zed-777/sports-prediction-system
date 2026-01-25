from scripts import export_metrics


def test_export_metrics_creates_files(tmp_path):
    out_dir = tmp_path / "metrics"
    # Ensure directory not exists
    assert not out_dir.exists()
    export_metrics.main(str(out_dir))
    assert out_dir.exists()
    files = list(out_dir.iterdir())
    assert any(p.suffix == ".json" for p in files)
    assert any(p.suffix == ".csv" for p in files)
