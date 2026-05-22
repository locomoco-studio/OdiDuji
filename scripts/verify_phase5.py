import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


REPORT_PATH = Path("database/test_report.json")
BACKUP_PATH = Path("database/backup_demo_results.json")
DB_PATH = Path("database/odiduji.sqlite")


def run_report() -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/phase5_qa_report.py",
            "--db",
            str(DB_PATH),
            "--output",
            str(REPORT_PATH),
            "--backup-output",
            str(BACKUP_PATH),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def verify_files() -> dict:
    if not REPORT_PATH.exists() or not BACKUP_PATH.exists():
        return {"ok": False, "report_exists": REPORT_PATH.exists(), "backup_exists": BACKUP_PATH.exists()}
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    backup = json.loads(BACKUP_PATH.read_text(encoding="utf-8"))
    metrics = report.get("metrics", {})
    acceptance = report.get("acceptance", {})
    checks = {
        "dataset_size_81": report.get("dataset_size") == 81,
        "backup_demo_count_3": len(backup) == 3,
        "metric_count_at_least_10": len(metrics) >= 10,
        "threshold_sweep_3": set(metrics.get("threshold_sweep", {}).keys()) == {"0.6", "0.7", "0.8"},
        "ambiguous_rate_present": "ambiguous_activation_rate" in metrics,
        "acceptance_all_true": all(acceptance.values()),
    }
    return {"ok": all(checks.values()), "checks": checks}


def verify_sqlite_report() -> dict:
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            """
            SELECT report_id, dataset_size, ambiguous_sample_count, threshold_sweep_json, raw_report_json
            FROM test_report
            ORDER BY generated_at DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return {"ok": False, "error": "missing test_report row"}
    sweep = json.loads(row[3])
    raw = json.loads(row[4])
    checks = {
        "dataset_size_81": row[1] == 81,
        "ambiguous_sample_count_3": row[2] == 3,
        "threshold_sweep_3": set(sweep.keys()) == {"0.6", "0.7", "0.8"},
        "raw_report_has_acceptance": "acceptance" in raw,
    }
    return {"ok": all(checks.values()), "report_id": row[0], "checks": checks}


def main() -> None:
    run = run_report()
    files = verify_files()
    sqlite = verify_sqlite_report()
    result = {
        "ok": run["ok"] and files["ok"] and sqlite["ok"],
        "run_report": {"ok": run["ok"], "returncode": run["returncode"], "stderr": run["stderr"]},
        "files": files,
        "sqlite": sqlite,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
