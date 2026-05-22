import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = Path("database/odiduji.sqlite")
WORKFLOW_PATH = Path("workflows/odiduji.json")

DEMO_QUERIES = [
    "이번 주 마감 과제 공지",
    "2만 원 넘는 영수증",
    "장학금 신청 기간",
]


def run_query(raw_query: str) -> dict:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/phase4_query_pipeline.py",
            raw_query,
            "--db",
            str(DB_PATH),
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
        "payload": json.loads(completed.stdout),
    }


def verify_demo_queries() -> dict:
    results = {query: run_query(query) for query in DEMO_QUERIES}
    ok = all(
        result["ok"]
        and result["payload"].get("query_plan_valid") is True
        and isinstance(result["payload"].get("cards"), list)
        and len(result["payload"]["cards"]) <= 3
        for result in results.values()
    )
    return {"ok": ok, "results": results}


def verify_no_answer() -> dict:
    result = run_query("기숙사 택배 보관함 비밀번호 알려줘")
    payload = result["payload"]
    return {
        "ok": result["ok"]
        and payload.get("no_answer") is True
        and bool(payload.get("relaxation_options")),
        "payload": payload,
    }


def verify_correction_log() -> dict:
    conn = sqlite3.connect(DB_PATH)
    before = conn.execute("SELECT COUNT(*) FROM correction_log").fetchone()[0]
    conn.close()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/phase4_query_pipeline.py",
            "--db",
            str(DB_PATH),
            "--payload-json",
            json.dumps(
                {
                    "action": "correction",
                    "query_id": "Q-VERIFY",
                    "selected_capture_id": "CAP-001",
                    "previous_rank": 4,
                    "corrected_field": "deadline",
                    "before_value": "raw date",
                    "after_value": "2026-05-07",
                },
                ensure_ascii=False,
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    conn = sqlite3.connect(DB_PATH)
    after = conn.execute("SELECT COUNT(*) FROM correction_log").fetchone()[0]
    conn.close()
    payload = json.loads(completed.stdout)
    return {
        "ok": completed.returncode == 0 and after == before + 1 and payload.get("status") == "accepted",
        "before": before,
        "after": after,
        "payload": payload,
    }


def verify_workflow() -> dict:
    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    webhooks = [
        node
        for node in workflow.get("nodes", [])
        if node.get("type") == "n8n-nodes-base.webhook"
    ]
    route_node = next(
        (node for node in workflow.get("nodes", []) if node.get("name") == "Route question action"),
        None,
    )
    js_code = route_node.get("parameters", {}).get("jsCode", "") if route_node else ""
    checks = {
        "two_webhooks": sorted(node.get("parameters", {}).get("path") for node in webhooks)
        == ["image-upload", "question-submit"],
        "sqlite_query": "FROM metadata_index" in js_code,
        "correction_log": "correction_log" in js_code,
        "fallback": "fallback_candidates" in js_code,
        "no_answer": "no_answer_reason" in js_code,
    }
    return {"ok": all(checks.values()), "checks": checks}


def main() -> None:
    result = {
        "workflow": verify_workflow(),
        "demo_queries": verify_demo_queries(),
        "no_answer": verify_no_answer(),
        "correction_log": verify_correction_log(),
    }
    result["ok"] = all(section["ok"] for section in result.values())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
