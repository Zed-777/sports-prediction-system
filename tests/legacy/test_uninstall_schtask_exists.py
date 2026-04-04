from pathlib import Path


def test_uninstall_exists():
    p = Path("scripts/uninstall_schtask.ps1")
    assert p.exists()
    s = p.read_text(encoding="utf-8")
    assert "schtasks /Delete" in s
