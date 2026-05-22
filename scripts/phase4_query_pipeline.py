import argparse
import hashlib
import json
import sqlite3
import time
from pathlib import Path


DOC_TYPES = {"notice", "assignment", "scholarship", "receipt", "place_link", "noise"}
RELAXATION_OPTIONS = ["date_range_expand_7d", "search_all_doc_type", "include_needs_review"]


def plan_query(raw_query: str) -> dict:
    query = raw_query.strip()
    lowered = query.lower()
    plan = {
        "query_intent": "search_cards",
        "target_doc_type": None,
        "filters": {},
        "sort_rule": "confidence_desc",
        "requested_fields": ["title", "deadline", "amount", "required_submission", "location_name"],
        "answer_policy": {
            "mode": "evidence_bound",
            "allow_free_generation": False,
            "require_evidence_text": True,
        },
    }

    if "영수증" in query or "금액" in query or "원" in query:
        plan["target_doc_type"] = "receipt"
        plan["sort_rule"] = "amount_desc"
        if "2만" in query:
            plan["filters"]["amount_min"] = 20000
        elif "만원" in query:
            plan["filters"]["amount_min"] = 10000
        plan["requested_fields"] = ["title", "amount", "currency", "location_name"]
    elif "장학" in query:
        plan["target_doc_type"] = "scholarship"
        plan["sort_rule"] = "deadline_asc"
        plan["requested_fields"] = ["title", "deadline", "amount", "required_submission", "location_name"]
    elif "과제" in query or "제출" in query or "마감" in query:
        plan["target_doc_type"] = "assignment"
        plan["sort_rule"] = "deadline_asc"
        plan["requested_fields"] = ["title", "deadline", "required_submission"]
        if "이번 주" in query or "this week" in lowered:
            plan["filters"]["deadline_bucket"] = "this_week"
    elif "장소" in query or "주소" in query:
        plan["target_doc_type"] = "place_link"
        plan["requested_fields"] = ["title", "location_name", "address"]
    else:
        plan["query_intent"] = "unsupported_query"

    return plan


def validate_plan(plan: dict) -> tuple[bool, str | None]:
    doc_type = plan.get("target_doc_type")
    if doc_type is not None and doc_type not in DOC_TYPES:
        return False, "invalid_doc_type"
    if plan.get("sort_rule") not in {"deadline_asc", "amount_desc", "confidence_desc"}:
        return False, "invalid_sort_rule"
    for key in plan.get("filters", {}):
        if key not in {"amount_min", "deadline_bucket", "include_needs_review"}:
            return False, "invalid_filter_key"
    return True, None


def build_where(plan: dict, include_fallback: bool = False) -> tuple[str, list[object]]:
    clauses = ["1 = 1"]
    params: list[object] = []
    doc_type = plan.get("target_doc_type")
    filters = plan.get("filters", {})

    if doc_type and not include_fallback:
        clauses.append("mi.doc_type = ?")
        params.append(doc_type)
    elif doc_type and include_fallback:
        clauses.append("(mi.doc_type = ? OR mi.doc_type != 'noise')")
        params.append(doc_type)

    if "amount_min" in filters:
        clauses.append("mi.amount >= ?")
        params.append(filters["amount_min"])

    if filters.get("deadline_bucket") and not include_fallback:
        clauses.append("(mi.deadline_bucket = ? OR mi.deadline IS NOT NULL)")
        params.append(filters["deadline_bucket"])

    return " AND ".join(clauses), params


def order_by(sort_rule: str) -> str:
    if sort_rule == "deadline_asc":
        return "mi.deadline IS NULL ASC, mi.deadline ASC, mi.confidence DESC"
    if sort_rule == "amount_desc":
        return "mi.amount IS NULL ASC, mi.amount DESC, mi.confidence DESC"
    return "mi.confidence DESC, mi.index_record_id ASC"


def fetch_candidates(conn: sqlite3.Connection, plan: dict, limit: int, offset: int = 0) -> list[sqlite3.Row]:
    where_sql, params = build_where(plan, include_fallback=offset > 0)
    sql = f"""
        SELECT
          mi.*,
          cr.source_image_path,
          cr.file_name
        FROM metadata_index mi
        JOIN capture_records cr ON cr.capture_id = mi.capture_id
        WHERE {where_sql}
        ORDER BY {order_by(plan["sort_rule"])}
        LIMIT ? OFFSET ?
    """
    return list(conn.execute(sql, (*params, limit, offset)))


def evidence_for(row: sqlite3.Row) -> dict:
    try:
        return json.loads(row["evidence_text_json"] or "{}")
    except json.JSONDecodeError:
        return {}


def card_from_row(row: sqlite3.Row) -> dict:
    evidence = evidence_for(row)
    fields = {}
    for field in [
        "deadline",
        "amount",
        "currency",
        "required_submission",
        "source",
        "location_name",
        "address",
    ]:
        value = row[field] if field in row.keys() else None
        if value is not None:
            fields[field] = value

    cited_fields = {
        field: evidence[field]
        for field in evidence
        if evidence.get(field) not in (None, "")
    }

    return {
        "capture_id": row["capture_id"],
        "source_image_path": row["source_image_path"],
        "doc_type": row["doc_type"],
        "title": row["title"] or row["file_name"],
        "fields": fields,
        "confidence": row["confidence"],
        "needs_review": bool(row["needs_review"]),
        "classification_state": row["classification_state"],
        "evidence_text": cited_fields,
    }


def has_evidence(card: dict, requested_fields: list[str]) -> bool:
    evidence = card.get("evidence_text", {})
    return any(field in evidence for field in requested_fields) or bool(evidence.get("title"))


def answer_from_cards(cards: list[dict], requested_fields: list[str]) -> tuple[str, list[str]]:
    snippets = []
    cited = []
    for card in cards:
        title = card["title"]
        fields = card["fields"]
        evidence = card["evidence_text"]
        parts = []
        for field in requested_fields:
            if field in fields and (field in evidence or field == "currency"):
                parts.append(f"{field}={fields[field]}")
                cited.append(f"{card['capture_id']}.{field}")
        if parts:
            snippets.append(f"{title}: " + ", ".join(parts))
        elif evidence:
            snippets.append(f"{title}: 근거 문장 있음")
            cited.append(f"{card['capture_id']}.evidence_text")
    return " / ".join(snippets), cited


def write_correction(conn: sqlite3.Connection, payload: dict) -> dict:
    correction_id = f"COR-{int(time.time() * 1000)}"
    before_hash = hashlib.sha256(str(payload.get("before_value", "")).encode()).hexdigest()
    after_hash = hashlib.sha256(str(payload.get("after_value", "")).encode()).hexdigest()
    with conn:
        conn.execute(
            """
            INSERT INTO correction_log (
              correction_id,
              query_id,
              selected_capture_id,
              previous_rank,
              corrected_field,
              before_value_hash,
              after_value_hash,
              action,
              note_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                correction_id,
                payload.get("query_id"),
                payload.get("selected_capture_id"),
                payload.get("previous_rank"),
                payload.get("corrected_field"),
                before_hash,
                after_hash,
                payload.get("action", "correction"),
                json.dumps({"stored": "hash_only"}, ensure_ascii=False),
            ),
        )
    return {"status": "accepted", "correction_id": correction_id}


def qa_report(conn: sqlite3.Connection) -> dict:
    row = conn.execute(
        """
        SELECT *
        FROM test_report
        ORDER BY generated_at DESC
        LIMIT 1
        """
    ).fetchone()
    return dict(row) if row else {"status": "missing", "report_id": None}


def handle_query(conn: sqlite3.Connection, raw_query: str) -> dict:
    query_id = f"Q-{int(time.time() * 1000)}"
    plan = plan_query(raw_query)
    if plan["query_intent"] == "unsupported_query":
        return {
            "query_id": query_id,
            "raw_query": raw_query,
            "query_plan": plan,
            "query_plan_valid": True,
            "answer": "",
            "cards": [],
            "no_answer": True,
            "no_answer_reason": "unsupported_query_intent",
            "relaxation_options": RELAXATION_OPTIONS,
            "fallback_candidates": [],
            "processing_log": ["received", "planned", "no_answer"],
        }
    valid, error = validate_plan(plan)
    if not valid:
        return {
            "query_id": query_id,
            "raw_query": raw_query,
            "query_plan": plan,
            "query_plan_valid": False,
            "validation_error": error,
            "no_answer": True,
            "no_answer_reason": "query_plan_invalid",
        }

    rows = fetch_candidates(conn, plan, limit=3)
    cards = [card_from_row(row) for row in rows]
    evidence_cards = [card for card in cards if has_evidence(card, plan["requested_fields"])]
    fallback_rows = fetch_candidates(conn, plan, limit=7, offset=3)
    fallback_cards = [card_from_row(row) for row in fallback_rows]

    if not evidence_cards:
        return {
            "query_id": query_id,
            "raw_query": raw_query,
            "query_plan": plan,
            "query_plan_valid": True,
            "answer": "",
            "cards": cards,
            "no_answer": True,
            "no_answer_reason": "missing_evidence_text" if cards else "no_candidate",
            "relaxation_options": RELAXATION_OPTIONS,
            "fallback_candidates": fallback_cards,
            "processing_log": ["received", "planned", "searched", "no_answer"],
        }

    answer, cited = answer_from_cards(evidence_cards, plan["requested_fields"])
    return {
        "query_id": query_id,
        "raw_query": raw_query,
        "query_plan": plan,
        "query_plan_valid": True,
        "answer": answer,
        "cards": evidence_cards,
        "cited_fields": cited,
        "no_answer": False,
        "relaxation_options": [],
        "fallback_candidates": fallback_cards,
        "processing_log": ["received", "planned", "searched", "answered"],
    }


def process(db_path: Path, payload: dict) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        action = payload.get("action", "query")
        if action == "correction" or action == "fallback_select":
            return write_correction(conn, payload)
        if action == "qa_report":
            return qa_report(conn)
        if action == "status":
            capture_id = payload.get("selected_capture_id") or payload.get("capture_id")
            row = conn.execute(
                "SELECT capture_id, status, source_image_path FROM capture_records WHERE capture_id = ?",
                (capture_id,),
            ).fetchone()
            return dict(row) if row else {"status": "not_found", "capture_id": capture_id}
        return handle_query(conn, payload.get("raw_query") or payload.get("query") or "")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 4 question-submit locally.")
    parser.add_argument("raw_query", nargs="?", default="")
    parser.add_argument("--db", default="database/odiduji.sqlite")
    parser.add_argument("--payload-json")
    args = parser.parse_args()

    payload = json.loads(args.payload_json) if args.payload_json else {"raw_query": args.raw_query}
    result = process(Path(args.db), payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.get("query_plan_valid", True) else 2)


if __name__ == "__main__":
    main()
