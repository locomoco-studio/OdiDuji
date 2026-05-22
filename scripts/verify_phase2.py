import json
import sqlite3
from pathlib import Path


DB_PATH = Path("database/odiduji.sqlite")
WORKFLOW_PATH = Path("workflows/odiduji.json")

REQUIRED_TABLES = {
    "capture_records",
    "metadata_index",
    "cache_entries",
    "golden_dataset",
    "test_report",
    "correction_log",
}


def verify_sqlite() -> dict:
    if not DB_PATH.exists():
        return {"ok": False, "error": f"missing {DB_PATH}"}

    conn = sqlite3.connect(DB_PATH)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        missing = sorted(REQUIRED_TABLES - tables)
        counts = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in sorted(REQUIRED_TABLES)
            if table in tables
        }
        invalid_paths = conn.execute(
            """
            SELECT COUNT(*)
            FROM capture_records
            WHERE source_image_path NOT GLOB '/static/captures/CAP-[0-9][0-9][0-9].*'
              AND source_image_path NOT GLOB '/static/captures/CAP-LIVE-[0-9]*.*'
            """
        ).fetchone()[0]
    finally:
        conn.close()

    return {
        "ok": not missing and invalid_paths == 0,
        "missing_tables": missing,
        "counts": counts,
        "invalid_static_paths": invalid_paths,
    }


def verify_workflow() -> dict:
    if not WORKFLOW_PATH.exists():
        return {"ok": False, "error": f"missing {WORKFLOW_PATH}"}

    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    webhooks = [
        node
        for node in workflow.get("nodes", [])
        if node.get("type") == "n8n-nodes-base.webhook"
    ]
    paths = sorted(node.get("parameters", {}).get("path") for node in webhooks)
    return {
        "ok": paths == ["image-upload", "question-submit"],
        "trigger_webhook_count": len(webhooks),
        "paths": paths,
    }


def main() -> None:
    sqlite_result = verify_sqlite()
    workflow_result = verify_workflow()
    ok = sqlite_result["ok"] and workflow_result["ok"]
    print(
        json.dumps(
            {
                "ok": ok,
                "sqlite": sqlite_result,
                "workflow": workflow_result,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
