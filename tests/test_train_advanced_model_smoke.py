import pytest
from pathlib import Path


def test_train_script_exists():
    p = Path("scripts/train_advanced_model.py")
    assert p.exists(), "Training script is missing"


@pytest.mark.skip(reason="Full training requires processed data; run manually")
def test_train_small_sample():
    # This smoke test is intentionally skipped in CI; use local runs to validate
    from scripts.train_advanced_model import train_baseline

    model_path, metrics = train_baseline(
        Path("data/processed/advanced_model/sample_train.csv"),
        Path("models/advanced"),
        seed=42,
    )
    assert model_path.exists()
    assert "val_loss" in metrics
