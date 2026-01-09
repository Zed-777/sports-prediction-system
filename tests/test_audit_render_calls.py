import subprocess
from pathlib import Path


def test_audit_render_calls_no_duplicates():
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "audit_render_calls.py"
    assert script.exists(), "audit_render_calls.py script missing"
    res = subprocess.run(["python", str(script)], capture_output=True, text=True)
    # Non-zero exit code indicates duplicates found
    assert res.returncode == 0, (
        f"audit_render_calls.py reported duplicates or errors:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    )
