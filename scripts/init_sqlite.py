import argparse
import hashlib
import json
import mimetypes
import sqlite3
from pathlib import Path


DOC_TYPES = {"notice", "assignment", "scholarship", "receipt", "place_link", "noise"}
AMBIGUOUS_SAMPLE_IDS = {"img_069", "img_070", "img_071"}


def capture_id_from_image_id(image_id: str) -> str:
    number = int(image_id.split("_", 1)[1])
    return f"CAP-{number:03d}"


def normalized_ext(file_name: str) -> str:
    suffix = Path(file_name).suffix.lower().lstrip(".")
    if suffix == "jpeg":
        return "jpg"
    return suffix


def static_capture_path(capture_id: str, file_name: str) -> str:
    return f"/static/captures/{capture_id}.{normalized_ext(file_name)}"


def file_hash(dataset_dir: Path, file_name: str) -> str:
    file_path = dataset_dir / file_name
    if file_path.exists():
        return hashlib.sha256(file_path.read_bytes()).hexdigest()
    return hashlib.sha256(file_name.encode("utf-8")).hexdigest()


def file_size(dataset_dir: Path, file_name: str) -> int:
    file_path = dataset_dir / file_name
    return file_path.stat().st_size if file_path.exists() else 0


def mime_type(file_name: str) -> str:
    guessed = mimetypes.guess_type(file_name)[0]
    if guessed == "image/png":
        return "image/png"
    return "image/jpeg"


def load_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    conn.executescript(schema_path.read_text(encoding="utf-8"))


def seed_golden_dataset(conn: sqlite3.Connection, dataset_path: Path) -> None:
    dataset_dir = dataset_path.parent
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))

    with conn:
        for item in cases:
            image_id = item["image_id"]
            file_name = item["file_name"]
            capture_id = capture_id_from_image_id(image_id)
            metadata = item.get("metadata", {})
            doc_type = metadata.get("doc_type") or "noise"
            if doc_type not in DOC_TYPES:
                raise ValueError(f"Unsupported doc_type for {image_id}: {doc_type}")

            ext = normalized_ext(file_name)
            if ext not in {"jpg", "png"}:
                raise ValueError(f"Unsupported file extension for {image_id}: {file_name}")

            source_path = static_capture_path(capture_id, file_name)
            digest = file_hash(dataset_dir, file_name)

            conn.execute(
                """
                INSERT OR REPLACE INTO capture_records (
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
                    digest,
                    file_name,
                    ext,
                    mime_type(file_name),
                    file_size(dataset_dir, file_name),
                    json.dumps({"seed_source": "golden_dataset"}, ensure_ascii=False),
                ),
            )

            evidence = item.get("evidence_text", {})
            confidence = float(metadata.get("confidence") or 0.0)
            needs_review = 1 if confidence < 0.7 or image_id in AMBIGUOUS_SAMPLE_IDS else 0
            classification_state = (
                "Classify_Ambiguous" if image_id in AMBIGUOUS_SAMPLE_IDS else "Classified"
            )

            conn.execute(
                """
                INSERT OR REPLACE INTO metadata_index (
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
                  category_candidates_json,
                  parse_confidence,
                  category_confidence,
                  extract_confidence,
                  confidence,
                  classification_state,
                  needs_review
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', ?, ?, ?, ?, ?, ?)
                """,
                (
                    capture_id,
                    doc_type,
                    metadata.get("title"),
                    metadata.get("source"),
                    metadata.get("created_date"),
                    metadata.get("event_date"),
                    metadata.get("deadline"),
                    metadata.get("deadline_bucket"),
                    None
                    if metadata.get("has_submission") is None
                    else int(bool(metadata.get("has_submission"))),
                    metadata.get("amount"),
                    metadata.get("currency") or "KRW",
                    metadata.get("location_name"),
                    metadata.get("address"),
                    evidence.get("has_submission"),
                    json.dumps(evidence, ensure_ascii=False),
                    confidence,
                    confidence,
                    confidence,
                    confidence,
                    classification_state,
                    needs_review,
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
                VALUES (?, ?, '{}', ?, ?, 'golden-dataset-v1')
                """,
                (
                    digest,
                    capture_id,
                    json.dumps(
                        {
                            "doc_type": doc_type,
                            "category_confidence": confidence,
                            "classification_state": classification_state,
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(metadata, ensure_ascii=False),
                ),
            )

            conn.execute(
                """
                INSERT OR REPLACE INTO golden_dataset (
                  case_id,
                  capture_id,
                  image_id,
                  dataset_file_name,
                  expected_doc_type,
                  expected_fields_json,
                  evidence_text_json,
                  representative_query,
                  is_ambiguous_sample
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"CASE-{int(image_id.split('_', 1)[1]):03d}",
                    capture_id,
                    image_id,
                    file_name,
                    doc_type,
                    json.dumps(metadata, ensure_ascii=False),
                    json.dumps(evidence, ensure_ascii=False),
                    None,
                    1 if image_id in AMBIGUOUS_SAMPLE_IDS else 0,
                ),
            )

        conn.execute(
            """
            INSERT OR REPLACE INTO test_report (
              report_id,
              dataset_size,
              ambiguous_sample_count,
              threshold_sweep_json,
              raw_report_json
            )
            VALUES ('REPORT-SEED', ?, ?, ?, ?)
            """,
            (
                len(cases),
                len(AMBIGUOUS_SAMPLE_IDS),
                json.dumps({"0.6": None, "0.7": None, "0.8": None}),
                json.dumps({"status": "seeded", "source": "golden_dataset.json"}),
            ),
        )


def verify(conn: sqlite3.Connection) -> dict:
    required_tables = {
        "capture_records",
        "metadata_index",
        "cache_entries",
        "golden_dataset",
        "test_report",
        "correction_log",
    }
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    missing = sorted(required_tables - tables)
    counts = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in sorted(required_tables)
        if table in tables
    }
    return {"missing_tables": missing, "counts": counts}


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the OdidujI SQLite database.")
    parser.add_argument("--db", default="database/odiduji.sqlite")
    parser.add_argument("--schema", default="database/schema.sql")
    parser.add_argument("--golden-dataset", default="dataset/golden_dataset.json")
    args = parser.parse_args()

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        load_schema(conn, Path(args.schema))
        seed_golden_dataset(conn, Path(args.golden_dataset))
        result = verify(conn)
    finally:
        conn.close()

    print(json.dumps({"db": str(db_path), **result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
