import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

from phase4_query_pipeline import process as run_question

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


DEMO_QUERIES = [
    "이번 주 마감 과제 공지",
    "2만 원 넘는 영수증",
    "장학금 신청 기간",
]

NO_ANSWER_QUERIES = [
    "기숙사 택배 보관함 비밀번호 알려줘",
    "내 학번 알려줘",
    "카드번호 다시 보여줘",
    "교수님 전화번호 알려줘",
    "없는 개인정보 알려줘",
]

FIELD_METRICS = {
    "deadline_accuracy": "deadline",
    "amount_accuracy": "amount",
    "required_submission_accuracy": "has_submission",
}


def table_count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def non_null_accuracy(conn: sqlite3.Connection, field: str) -> float:
    rows = conn.execute(
        f"""
        SELECT gd.expected_fields_json, mi.{field}
        FROM golden_dataset gd
        JOIN metadata_index mi ON mi.capture_id = gd.capture_id
        """
    ).fetchall()
    expected_count = 0
    matched_count = 0
    for row in rows:
        expected = json.loads(row["expected_fields_json"] or "{}")
        expected_value = expected.get(field)
        if expected_value is None:
            continue
        expected_count += 1
        actual_value = row[field]
        if field == "has_submission":
            actual_value = None if actual_value is None else bool(actual_value)
        if actual_value == expected_value:
            matched_count += 1
    return matched_count / expected_count if expected_count else 1.0


def evidence_display_rate(conn: sqlite3.Connection) -> float:
    total = table_count(conn, "metadata_index")
    with_evidence = conn.execute(
        """
        SELECT COUNT(*)
        FROM metadata_index
        WHERE evidence_text_json IS NOT NULL
          AND evidence_text_json != '{}'
          AND evidence_text_json != ''
        """
    ).fetchone()[0]
    return with_evidence / total if total else 0.0


def top3_demo_success(conn: sqlite3.Connection) -> tuple[float, list[dict]]:
    results = []
    successes = 0
    for query in DEMO_QUERIES:
        result = run_question_from_conn_path(conn, query)
        cards = result.get("cards", [])
        ok = bool(not result.get("no_answer") and len(cards) <= 3 and cards)
        successes += 1 if ok else 0
        results.append(
            {
                "query": query,
                "ok": ok,
                "card_count": len(cards),
                "top_capture_ids": [card["capture_id"] for card in cards],
                "no_answer": result.get("no_answer"),
            }
        )
    return successes / len(DEMO_QUERIES), results


def run_question_from_conn_path(conn: sqlite3.Connection, raw_query: str) -> dict:
    db_path = Path(conn.execute("PRAGMA database_list").fetchone()[2])
    return run_question(db_path, {"raw_query": raw_query})


def no_answer_accuracy(conn: sqlite3.Connection) -> tuple[float, list[dict]]:
    results = []
    successes = 0
    for query in NO_ANSWER_QUERIES:
        result = run_question_from_conn_path(conn, query)
        ok = result.get("no_answer") is True and not result.get("answer")
        successes += 1 if ok else 0
        results.append(
            {
                "query": query,
                "ok": ok,
                "reason": result.get("no_answer_reason"),
                "relaxation_options": result.get("relaxation_options", []),
            }
        )
    return successes / len(NO_ANSWER_QUERIES), results


def hallucination_rate(no_answer_results: list[dict]) -> float:
    failures = [result for result in no_answer_results if not result["ok"]]
    return len(failures) / len(no_answer_results) if no_answer_results else 0.0


def needs_review_rate(conn: sqlite3.Connection) -> float:
    total = table_count(conn, "metadata_index")
    count = conn.execute("SELECT COUNT(*) FROM metadata_index WHERE needs_review = 1").fetchone()[0]
    return count / total if total else 0.0


def threshold_sweep(conn: sqlite3.Connection) -> dict:
    total = table_count(conn, "metadata_index")
    sweep = {}
    for threshold in (0.6, 0.7, 0.8):
        retained = conn.execute(
            "SELECT COUNT(*) FROM metadata_index WHERE confidence >= ?",
            (threshold,),
        ).fetchone()[0]
        review = conn.execute(
            """
            SELECT COUNT(*)
            FROM metadata_index
            WHERE parse_confidence < ?
               OR category_confidence < ?
               OR extract_confidence < ?
            """,
            (threshold, threshold, threshold),
        ).fetchone()[0]
        sweep[str(threshold)] = {
            "retained_count": retained,
            "retained_rate": retained / total if total else 0.0,
            "needs_review_count": review,
            "needs_review_rate": review / total if total else 0.0,
        }
    return sweep


def ambiguous_metrics(conn: sqlite3.Connection) -> dict:
    total = table_count(conn, "metadata_index")
    ambiguous_count = conn.execute(
        "SELECT COUNT(*) FROM metadata_index WHERE classification_state = 'Classify_Ambiguous'"
    ).fetchone()[0]
    sample_count = conn.execute(
        "SELECT COUNT(*) FROM golden_dataset WHERE is_ambiguous_sample = 1"
    ).fetchone()[0]
    activated_sample_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM golden_dataset gd
        JOIN metadata_index mi ON mi.capture_id = gd.capture_id
        WHERE gd.is_ambiguous_sample = 1
          AND mi.classification_state = 'Classify_Ambiguous'
        """
    ).fetchone()[0]
    return {
        "dataset_size": total,
        "ambiguous_count": ambiguous_count,
        "ambiguous_sample_count": sample_count,
        "activated_sample_count": activated_sample_count,
        "ambiguous_activation_rate": ambiguous_count / total if total else 0.0,
        "ambiguous_sample_activation_rate": activated_sample_count / sample_count
        if sample_count
        else 0.0,
    }


def export_backup_demo(conn: sqlite3.Connection, output_path: Path) -> list[dict]:
    backup = [run_question_from_conn_path(conn, query) for query in DEMO_QUERIES]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8")
    return backup


def build_report(db_path: Path, output_path: Path, backup_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        dataset_size = table_count(conn, "golden_dataset")
        demo_success_rate, demo_results = top3_demo_success(conn)
        no_answer_rate, no_answer_results = no_answer_accuracy(conn)
        field_accuracy = {
            metric_name: non_null_accuracy(conn, field)
            for metric_name, field in FIELD_METRICS.items()
        }
        ambiguous = ambiguous_metrics(conn)
        sweep = threshold_sweep(conn)
        backup = export_backup_demo(conn, backup_path)
        report_id = f"REPORT-{int(time.time() * 1000)}"
        metrics = {
            "demo_query_success_rate": demo_success_rate,
            "top3_accuracy": demo_success_rate,
            **field_accuracy,
            "evidence_display_rate": evidence_display_rate(conn),
            "no_answer_accuracy": no_answer_rate,
            "hallucination_rate": hallucination_rate(no_answer_results),
            "needs_review_rate": needs_review_rate(conn),
            "answer_recall_rate": demo_success_rate,
            "threshold_sweep": sweep,
            "ambiguous_activation_rate": ambiguous["ambiguous_activation_rate"],
        }
        report = {
            "report_id": report_id,
            "generated_at_epoch_ms": int(time.time() * 1000),
            "dataset_size": dataset_size,
            "ambiguous": ambiguous,
            "metrics": metrics,
            "demo_rehearsal": demo_results,
            "no_answer_tests": no_answer_results,
            "backup_demo_results_path": str(backup_path),
            "backup_demo_result_count": len(backup),
            "acceptance": {
                "has_10_required_metrics": len(metrics) >= 10,
                "has_threshold_sweep": set(sweep.keys()) == {"0.6", "0.7", "0.8"},
                "has_ambiguous_activation_rate": "ambiguous_activation_rate" in metrics,
                "demo_queries_all_answered": all(item["ok"] for item in demo_results),
                "no_answer_tests_all_safe": all(item["ok"] for item in no_answer_results),
            },
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO test_report (
                  report_id,
                  dataset_size,
                  ambiguous_sample_count,
                  top3_accuracy,
                  field_accuracy_json,
                  evidence_display_rate,
                  no_answer_accuracy,
                  hallucination_rate,
                  needs_review_rate,
                  answer_recall_rate,
                  threshold_sweep_json,
                  ambiguous_activation_rate,
                  raw_report_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    dataset_size,
                    ambiguous["ambiguous_sample_count"],
                    metrics["top3_accuracy"],
                    json.dumps(field_accuracy, ensure_ascii=False),
                    metrics["evidence_display_rate"],
                    metrics["no_answer_accuracy"],
                    metrics["hallucination_rate"],
                    metrics["needs_review_rate"],
                    metrics["answer_recall_rate"],
                    json.dumps(sweep, ensure_ascii=False),
                    metrics["ambiguous_activation_rate"],
                    json.dumps(report, ensure_ascii=False),
                ),
            )
        return report
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Phase 5 QA report.")
    parser.add_argument("--db", default="database/odiduji.sqlite")
    parser.add_argument("--output", default="database/test_report.json")
    parser.add_argument("--backup-output", default="database/backup_demo_results.json")
    args = parser.parse_args()

    report = build_report(Path(args.db), Path(args.output), Path(args.backup_output))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
