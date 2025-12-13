from scripts.fetch_historical_api import _filter_incremental


def test_filter_incremental_no_last_date():
    matches = [{'date': '2023-01-01'}, {'date': '2023-02-01'}]
    out = _filter_incremental(matches, None)
    assert out == matches


def test_filter_incremental_with_last_date():
    matches = [{'date': '2023-01-01'}, {'date': '2023-02-01'}, {'date': '2023-03-01'}]
    out = _filter_incremental(matches, '2023-02-01')
    assert out == [{'date': '2023-03-01'}]
