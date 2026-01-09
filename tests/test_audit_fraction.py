from pathlib import Path
from scripts import audit_synthetic_reports as audit


def test_audit_fraction(tmp_path):
    base = tmp_path / "reports" / "simulated"
    (base / "premier-league" / "matches" / "m1").mkdir(parents=True)
    (base / "premier-league" / "matches" / "m1" / "prediction.json").write_text('{}')

    # Create a public report to compare against
    public = tmp_path / "reports" / "leagues" / "premier-league" / "matches" / "m2"
    public.mkdir(parents=True)
    (public / "prediction.json").write_text('{}')

    # Run scan_simulated_reports directly
    summary = audit.scan_simulated_reports(base)
    # write out to out path
    out = tmp_path / "summary.json"
    # Run CLI emulation
    import subprocess, sys
    cmd = [sys.executable, str(Path(__file__).parent.parent / 'scripts' / 'audit_synthetic_reports.py'), '--out', str(out), '--fail-if-fraction-more-than', '0.4']
    # set cwd to tmp_path so script finds simulated and reports directories
    try:
        subprocess.check_call(cmd, cwd=str(tmp_path))
        assert False, 'Should have failed because fraction 0.5 > 0.4'
    except subprocess.CalledProcessError as e:
        assert e.returncode != 0
