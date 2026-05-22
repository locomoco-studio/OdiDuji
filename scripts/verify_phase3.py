import json
import sqlite3
import subprocess
import sys
from pathlib import Path


DB_PATH = Path("database/odiduji.sqlite")
IMAGE_WORKFLOW_PATH = Path("workflows/image-upload.json")
SAMPLE_IMAGE = Path("dataset/img_001.jpg")

PHASE3_NODE_NAMES = {
    "Webhook - image-upload",
    "Validate JPG PNG and hash",
    "Store original capture",
    "Prepare Document Parse",
    "Upstage Document Parse",
    "Normalize Parse Result",
    "Document Classify MVP",
    "Schema Router",
    "Information Extract MVP",
    "SQLite Index Write",
    "Respond image-upload",
}


def verify_workflow() -> dict:
    workflow = json.loads(IMAGE_WORKFLOW_PATH.read_text(encoding="utf-8"))
    nodes = workflow.get("nodes", [])
    node_names = {node.get("name") for node in nodes}
    webhooks = [
        node
        for node in nodes
        if node.get("type") == "n8n-nodes-base.webhook"
    ]
    paths = sorted(node.get("parameters", {}).get("path") for node in webhooks)
    missing = sorted(PHASE3_NODE_NAMES - node_names)
    return {
        "ok": not missing and paths == ["image-upload"],
        "workflow_file": str(IMAGE_WORKFLOW_PATH),
        "missing_phase3_nodes": missing,
        "trigger_webhook_count": len(webhooks),
        "paths": paths,
    }


def verify_sqlite_contract() -> dict:
    conn = sqlite3.connect(DB_PATH)
    try:
        capture_count = conn.execute("SELECT COUNT(*) FROM capture_records").fetchone()[0]
        index_count = conn.execute("SELECT COUNT(*) FROM metadata_index").fetchone()[0]
        cache_count = conn.execute("SELECT COUNT(*) FROM cache_entries").fetchone()[0]
        duplicate_hash_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM (
              SELECT file_hash
              FROM capture_records
              GROUP BY file_hash
              HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
    finally:
        conn.close()
    return {
        "ok": capture_count >= 81 and index_count >= 81 and cache_count >= 81 and duplicate_hash_count == 0,
        "capture_records": capture_count,
        "metadata_index": index_count,
        "cache_entries": cache_count,
        "duplicate_hash_count": duplicate_hash_count,
    }


def verify_duplicate_upload() -> dict:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/phase3_upload_pipeline.py",
            str(SAMPLE_IMAGE),
            "--db",
            str(DB_PATH),
            "--capture-dir",
            "static/captures",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {"stdout": completed.stdout, "stderr": completed.stderr}
    return {
        "ok": completed.returncode == 0 and payload.get("cache_hit") is True,
        "returncode": completed.returncode,
        "payload": payload,
    }


def main() -> None:
    result = {
        "workflow": verify_workflow(),
        "sqlite": verify_sqlite_contract(),
        "duplicate_upload": verify_duplicate_upload(),
    }
    result["ok"] = all(section["ok"] for section in result.values())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
