from pathlib import Path
import tempfile
from scripts.train_advanced_model import train_baseline
from app.data.advanced_model_features import build_sample_dataset


def test_train_writes_manifest(tmp_path):
    # create small sample CSV
    outdir = tmp_path / "models"
    data_dir = tmp_path / "data"
    processed = data_dir / "processed" / "advanced_model"
    processed.mkdir(parents=True)
    csv_path = processed / "smoke_train.csv"
    build_sample_dataset(csv_path, augment_per_match=2, seed=123)

    model_path, metrics = train_baseline(csv_path, outdir, seed=123)
    manifest_path = outdir / "manifest.json"
    assert manifest_path.exists()
    m = manifest_path.read_text(encoding="utf-8")
    assert "artifact" in m and "metrics" in m
