from pathlib import Path


def test_run_daily_fetch_exists():
    path = Path("scripts/run_daily_fetch.ps1")
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "collect_historical_results.py" in content
    assert "regenerate_reports.py" in content


def test_log_dir_default(tmp_path, monkeypatch):
    # Ensure script log directory can be resolved: we won't execute the script here
    script = Path("scripts/run_daily_fetch.ps1")
    assert script.exists()
    # Ensure logs directory path appears in script
    s = script.read_text(encoding="utf-8")
    assert "logs/daily" in s.replace("\\", "/")
