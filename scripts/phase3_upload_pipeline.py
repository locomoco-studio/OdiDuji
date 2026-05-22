import argparse
import hashlib
import json
import mimetypes
import shutil
import sqlite3
import time
from pathlib import Path


MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}
DOC_TYPES = {"notice", "assignment", "scholarship", "receipt", "place_link", "noise"}


def normalize_ext(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    return "jpg" if ext == "jpeg" else ext


def detect_mime(path: Path) -> str:
    detected = mimetypes.guess_type(path.name)[0]
    if detected in ALLOWED_MIME_TYPES:
        return detected
    return "application/octet-stream"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reject(reason: str, **extra: object) -> dict:
    return {
        "status": "rejected",
        "validation_status": "rejected",
        "reject_reason": reason,
        **extra,
    }


def validate_image(path: Path) -> dict:
    if not path.exists() or not path.is_file():
        return reject("file_not_found")

    ext = normalize_ext(path)
    mime_type = detect_mime(path)
    size = path.stat().st_size

    if ext not in ALLOWED_EXTENSIONS or mime_type not in ALLOWED_MIME_TYPES:
        return reject(
            "unsupported_file_type",
            file_ext=ext,
            mime_type=mime_type,
            allowed_extensions=sorted(ALLOWED_EXTENSIONS),
        )

    if size > MAX_FILE_SIZE_BYTES:
        return reject(
            "file_too_large",
            file_size_bytes=size,
            max_file_size_bytes=MAX_FILE_SIZE_BYTES,
        )

    return {
        "validation_status": "accepted",
        "file_ext": ext,
        "mime_type": mime_type,
        "file_size_bytes": size,
    }


def next_live_capture_id(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        """
        SELECT capture_id
        FROM capture_records
        WHERE capture_id LIKE 'CAP-LIVE-%'
        ORDER BY CAST(substr(capture_id, 10) AS INTEGER) DESC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        return "CAP-LIVE-001"
    number = int(row[0].rsplit("-", 1)[1]) + 1
    return f"CAP-LIVE-{number:03d}"


def find_cached_capture(conn: sqlite3.Connection, file_hash: str) -> dict | None:
    row = conn.execute(
        """
        SELECT capture_id
        FROM capture_records
        WHERE file_hash = ?
        """,
        (file_hash,),
    ).fetchone()
    if row is None:
        return None
    return {"capture_id": row[0], "status": "ready", "cache_hit": True}


def fallback_extract(file_name: str, file_hash: str) -> dict:
    title = Path(file_name).stem
    parsed_markdown = f"# {title}\n\nLive upload pending Upstage extraction."
    evidence = {
        "title": title,
        "doc_type": "Fallback classification used because Upstage output is not available.",
    }
    return {
        "parsed_markdown": parsed_markdown,
        "layout_blocks": [],
        "doc_type": "noise",
        "title": title,
        "source": "live_upload",
        "created_date": None,
        "event_date": None,
        "deadline": None,
        "deadline_bucket": None,
        "has_submission": None,
        "amount": None,
        "currency": "KRW",
        "location_name": None,
        "address": None,
        "required_submission": None,
        "evidence_text": evidence,
        "category_candidates": [
            {"doc_type": "noise", "confidence": 0.5},
            {"doc_type": "notice", "confidence": 0.3},
            {"doc_type": "assignment", "confidence": 0.2},
        ],
        "parse_confidence": 0.5,
        "category_confidence": 0.5,
        "extract_confidence": 0.5,
        "confidence": 0.5,
        "classification_state": "Classify_Ambiguous",
        "needs_review": 1,
        "api_version": "fallback-no-upstage",
        "file_hash": file_hash,
    }


def normalize_pipeline_result(result: dict) -> dict:
    doc_type = result.get("doc_type") or "noise"
    if doc_type not in DOC_TYPES:
        doc_type = "noise"
    confidence = float(result.get("confidence") or 0.0)
    parse_confidence = float(result.get("parse_confidence") or confidence)
    category_confidence = float(result.get("category_confidence") or confidence)
    extract_confidence = float(result.get("extract_confidence") or confidence)
    needs_review = any(
        value < 0.7 for value in (parse_confidence, category_confidence, extract_confidence)
    )
    needs_review = needs_review or bool(result.get("needs_review"))
    classification_state = result.get("classification_state")
    if classification_state not in {"Classified", "Classify_Ambiguous"}:
        classification_state = "Classify_Ambiguous" if category_confidence < 0.7 else "Classified"

    return {
        **result,
        "doc_type": doc_type,
        "confidence": confidence,
        "parse_confidence": parse_confidence,
        "category_confidence": category_confidence,
        "extract_confidence": extract_confidence,
        "needs_review": 1 if needs_review else 0,
        "classification_state": classification_state,
    }


def store_capture(
    conn: sqlite3.Connection,
    input_path: Path,
    capture_dir: Path,
    validation: dict,
    pipeline_result: dict,
    file_hash: str,
) -> dict:
    capture_id = next_live_capture_id(conn)
    ext = validation["file_ext"]
    source_path = f"/static/captures/{capture_id}.{ext}"
    disk_path = capture_dir / f"{capture_id}.{ext}"
    capture_dir.mkdir(parents=True, exist_ok=True)

    normalized = normalize_pipeline_result(pipeline_result)
    file_meta = {
        "original_file_name": input_path.name,
        "upload_source": "phase3_upload_pipeline",
    }

    with conn:
        shutil.copy2(input_path, disk_path)
        conn.execute(
            """
            INSERT INTO capture_records (
              capture_id,
              source_image_path,
              file_hash,
              file_name,
              file_ext,
              mime_type,
              file_size_bytes,
              file_meta_json,
              status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ready')
            """,
            (
                capture_id,
                source_path,
                file_hash,
                input_path.name,
                ext,
                validation["mime_type"],
                validation["file_size_bytes"],
                json.dumps(file_meta, ensure_ascii=False),
            ),
        )
        conn.execute(
            """
            INSERT INTO metadata_index (
              capture_id,
              doc_type,
              title,
              source,
              created_date,
              event_date,
              deadline,
              deadline_bucket,
              has_submission,
              amount,
              currency,
              location_name,
              address,
              required_submission,
              evidence_text_json,
              parsed_markdown,
              layout_blocks_json,
              category_candidates_json,
              parse_confidence,
              category_confidence,
              extract_confidence,
              confidence,
              classification_state,
              needs_review
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                capture_id,
                normalized["doc_type"],
                normalized.get("title"),
                normalized.get("source"),
                normalized.get("created_date"),
                normalized.get("event_date"),
                normalized.get("deadline"),
                normalized.get("deadline_bucket"),
                None
                if normalized.get("has_submission") is None
                else int(bool(normalized.get("has_submission"))),
                normalized.get("amount"),
                normalized.get("currency") or "KRW",
                normalized.get("location_name"),
                normalized.get("address"),
                normalized.get("required_submission"),
                json.dumps(normalized.get("evidence_text") or {}, ensure_ascii=False),
                normalized.get("parsed_markdown"),
                json.dumps(normalized.get("layout_blocks") or [], ensure_ascii=False),
                json.dumps(normalized.get("category_candidates") or [], ensure_ascii=False),
                normalized["parse_confidence"],
                normalized["category_confidence"],
                normalized["extract_confidence"],
                normalized["confidence"],
                normalized["classification_state"],
                normalized["needs_review"],
            ),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO cache_entries (
              file_hash,
              capture_id,
              cached_parse_json,
              cached_classify_json,
              cached_extract_json,
              api_version
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                file_hash,
                capture_id,
                json.dumps(
                    {
                        "parsed_markdown": normalized.get("parsed_markdown"),
                        "layout_blocks": normalized.get("layout_blocks") or [],
                        "parse_confidence": normalized["parse_confidence"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "doc_type": normalized["doc_type"],
                        "category_confidence": normalized["category_confidence"],
                        "category_candidates": normalized.get("category_candidates") or [],
                        "classification_state": normalized["classification_state"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(normalized, ensure_ascii=False),
                normalized.get("api_version") or "phase3",
            ),
        )

    return {
        "capture_id": capture_id,
        "source_image_path": source_path,
        "status": "ready",
        "cache_hit": False,
        "doc_type": normalized["doc_type"],
        "confidence": normalized["confidence"],
        "needs_review": bool(normalized["needs_review"]),
        "classification_state": normalized["classification_state"],
    }


def process_upload(db_path: Path, input_path: Path, capture_dir: Path) -> dict:
    upload_job_id = f"JOB-{int(time.time() * 1000)}"
    validation = validate_image(input_path)
    if validation["validation_status"] == "rejected":
        return {"upload_job_id": upload_job_id, **validation}

    digest = sha256_file(input_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        cached = find_cached_capture(conn, digest)
        if cached:
            return {"upload_job_id": upload_job_id, **cached}
        pipeline_result = fallback_extract(input_path.name, digest)
        stored = store_capture(conn, input_path, capture_dir, validation, pipeline_result, digest)
        return {"upload_job_id": upload_job_id, **validation, **stored}
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 3 upload indexing locally.")
    parser.add_argument("image")
    parser.add_argument("--db", default="database/odiduji.sqlite")
    parser.add_argument("--capture-dir", default="static/captures")
    args = parser.parse_args()

    result = process_upload(Path(args.db), Path(args.image), Path(args.capture_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.get("status") != "rejected" else 2)


if __name__ == "__main__":
    main()
