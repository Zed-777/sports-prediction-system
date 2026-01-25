"""Export in-memory metrics to a JSON or CSV file for run-level persistence."""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
import subprocess
import uuid
import os

from app.utils.metrics import get_metrics


def export_metrics_to_json(out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    metrics = get_metrics()
    metadata = collect_run_metadata()
    filename = os.path.join(
        out_dir, f"metrics_{datetime.utcnow().strftime('%Y%m%dT%H%M%S%fZ')}.json"
    )
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({"metadata": metadata, "metrics": metrics}, f, indent=2)
    return filename


def export_metrics_to_csv(out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    metrics = get_metrics()
    filename = os.path.join(
        out_dir, f"metrics_{datetime.utcnow().strftime('%Y%m%dT%H%M%S%fZ')}.csv"
    )
    # Flatten metrics for CSV
    rows = []
    for k, v in metrics.items():
        row = {"key": k}
        row.update(v)
        rows.append(row)

    # Write header from union of all fields
    header = set()
    for r in rows:
        header.update(r.keys())
    header = sorted(list(header))

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return filename


def main(out_dir: str = "reports/metrics") -> None:
    json_file = export_metrics_to_json(out_dir)
    csv_file = export_metrics_to_csv(out_dir)
    print(f"Metrics exported: {json_file}, {csv_file}")
    # Optional S3 upload
    s3_bucket = os.getenv("METRICS_S3_BUCKET")
    if s3_bucket:
        success = _maybe_upload_to_s3(s3_bucket, json_file, csv_file)
        if success:
            print(f"Metrics uploaded to S3 bucket {s3_bucket}")


if __name__ == "__main__":
    main()


def collect_run_metadata() -> dict:
    """Collect run metadata (commit SHA, branch, timestamp, env vars) for export.

    Returns a dictionary with keys like commit_sha, branch, timestamp, run_id and environment info.
    """
    meta = {}
    meta["timestamp_utc"] = datetime.utcnow().isoformat() + "Z"
    # Commit SHA and branch (best effort)
    try:
        meta["commit_sha"] = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:
        meta["commit_sha"] = None
    try:
        meta["git_branch"] = (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:
        meta["git_branch"] = None
    # Run id: prefer CI variables if present, otherwise generate a UUID
    meta["run_id"] = (
        os.getenv("GITHUB_RUN_ID") or os.getenv("CI_RUN_ID") or str(uuid.uuid4())
    )
    # Optional useful environment variables to include
    meta["ci"] = bool(os.getenv("CI"))
    meta["user"] = os.getenv("USER") or os.getenv("USERNAME")
    meta["hostname"] = os.getenv("HOSTNAME")
    # Record the exporter version or name
    meta["exporter"] = "scripts/export_metrics.py"
    return meta


def _maybe_upload_to_s3(bucket: str, json_file: str, csv_file: str) -> bool:
    """Try to upload files to S3 if boto3 is present and configured.
    This is best-effort (no hard failure) and returns True if upload succeeded.
    """
    try:
        import boto3
    except Exception:
        print("⚠️ boto3 not installed, skipping S3 upload for metrics")
        return False
    prefix = os.getenv("METRICS_S3_PREFIX", "metrics")
    s3 = boto3.client("s3")
    try:
        s3.upload_file(json_file, bucket, f"{prefix}/{os.path.basename(json_file)}")
        s3.upload_file(csv_file, bucket, f"{prefix}/{os.path.basename(csv_file)}")
        return True
    except Exception as e:
        print(f"⚠️ Failed to upload metrics to S3: {e}")
        return False
