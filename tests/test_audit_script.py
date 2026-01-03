import json
from pathlib import Path
import tempfile
import os
from scripts import audit_synthetic_reports as audit


def test_scan_simulated_reports_counts(tmp_path):
    # create simulated directory with two leagues and files
    base = tmp_path / "simulated"
    (base / "premier-league" / "matches" / "m1").mkdir(parents=True)
    (base / "premier-league" / "matches" / "m1" / "prediction.json").write_text('{}')
    (base / "la-liga" / "matches" / "m2").mkdir(parents=True)
    (base / "la-liga" / "matches" / "m2" / "prediction.json").write_text('{}')

    summary = audit.scan_simulated_reports(base)
    assert summary["total"] == 2
    assert summary["by_league"]["premier-league"] == 1
    assert summary["by_league"]["la-liga"] == 1


def test_audit_fail_if_more_than(tmp_path):
    base = tmp_path / "simulated"
    (base / "premier-league" / "matches" / "m1").mkdir(parents=True)
    (base / "premier-league" / "matches" / "m1" / "prediction.json").write_text('{}')

    out = tmp_path / "summary.json"
    # emulate CLI behavior
    import subprocess, sys
    cmd = [sys.executable, str(Path(__file__).parent.parent / 'scripts' / 'audit_synthetic_reports.py'), '--out', str(out), '--fail-if-more-than', '0']
    try:
        subprocess.check_call(cmd)
        assert False, "Should have failed with non-zero exit"
    except subprocess.CalledProcessError as e:
        assert e.returncode != 0
