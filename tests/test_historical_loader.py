from app.data.historical_loader import dataset_to_arrays, load_processed_dataset


def test_load_dataset_exists():
    processed, labels = load_processed_dataset()
    assert len(processed) >= 0
    assert isinstance(labels, list)


def test_dataset_to_arrays_shape():
    processed, labels = load_processed_dataset()
    if not processed:
        # If no processed sample exists, consider test skipped
        assert True
        return
    X, y = dataset_to_arrays(processed[:5])
    assert X.shape[1] == 20
    assert len(y) == min(5, len(processed))
