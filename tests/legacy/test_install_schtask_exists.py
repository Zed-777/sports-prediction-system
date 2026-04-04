from pathlib import Path


def test_install_schtask_exists():
    path = Path("scripts/install_schtask.ps1")
    assert path.exists()
    s = path.read_text(encoding="utf-8")
    assert "schtasks /Create" in s
    assert "Replace" in s
