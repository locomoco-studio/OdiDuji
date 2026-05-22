PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS capture_records (
  capture_id TEXT PRIMARY KEY CHECK (
    capture_id GLOB 'CAP-[0-9][0-9][0-9]' OR capture_id GLOB 'CAP-LIVE-[0-9]*'
  ),
  source_image_path TEXT NOT NULL UNIQUE,
  file_hash TEXT NOT NULL UNIQUE,
  file_name TEXT NOT NULL,
  file_ext TEXT NOT NULL CHECK (lower(file_ext) IN ('jpg', 'jpeg', 'png')),
  mime_type TEXT NOT NULL CHECK (mime_type IN ('image/jpeg', 'image/png')),
  file_size_bytes INTEGER NOT NULL DEFAULT 0 CHECK (file_size_bytes >= 0),
  file_meta_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'received' CHECK (
    status IN (
      'received',
      'validated',
      'parsed',
      'classified',
      'extracted',
      'indexed',
      'ready',
      'rejected',
      'failed'
    )
  ),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+09:00', 'now', '+9 hours')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+09:00', 'now', '+9 hours'))
);

CREATE TABLE IF NOT EXISTS metadata_index (
  index_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
  capture_id TEXT NOT NULL UNIQUE REFERENCES capture_records(capture_id) ON DELETE CASCADE,
  doc_type TEXT NOT NULL CHECK (
    doc_type IN ('notice', 'assignment', 'scholarship', 'receipt', 'place_link', 'noise')
  ),
  title TEXT,
  source TEXT,
  created_date TEXT,
  event_date TEXT,
  deadline TEXT,
  deadline_bucket TEXT CHECK (
    deadline_bucket IS NULL OR deadline_bucket IN ('today', 'this_week', 'this_month', 'future', 'past')
  ),
  has_submission INTEGER CHECK (has_submission IS NULL OR has_submission IN (0, 1)),
  amount REAL,
  currency TEXT DEFAULT 'KRW',
  location_name TEXT,
  address TEXT,
  required_submission TEXT,
  evidence_text_json TEXT NOT NULL DEFAULT '{}',
  parsed_markdown TEXT,
  layout_blocks_json TEXT NOT NULL DEFAULT '[]',
  category_candidates_json TEXT NOT NULL DEFAULT '[]',
  parse_confidence REAL CHECK (parse_confidence IS NULL OR parse_confidence BETWEEN 0.0 AND 1.0),
  category_confidence REAL CHECK (category_confidence IS NULL OR category_confidence BETWEEN 0.0 AND 1.0),
  extract_confidence REAL CHECK (extract_confidence IS NULL OR extract_confidence BETWEEN 0.0 AND 1.0),
  confidence REAL NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
  classification_state TEXT NOT NULL DEFAULT 'Classified' CHECK (
    classification_state IN ('Classified', 'Classify_Ambiguous')
  ),
  needs_review INTEGER NOT NULL DEFAULT 0 CHECK (needs_review IN (0, 1)),
  indexed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+09:00', 'now', '+9 hours'))
);

CREATE INDEX IF NOT EXISTS idx_metadata_doc_type ON metadata_index(doc_type);
CREATE INDEX IF NOT EXISTS idx_metadata_deadline ON metadata_index(deadline);
CREATE INDEX IF NOT EXISTS idx_metadata_amount ON metadata_index(amount);
CREATE INDEX IF NOT EXISTS idx_metadata_confidence ON metadata_index(confidence);

CREATE TABLE IF NOT EXISTS cache_entries (
  file_hash TEXT PRIMARY KEY REFERENCES capture_records(file_hash) ON DELETE CASCADE,
  capture_id TEXT NOT NULL REFERENCES capture_records(capture_id) ON DELETE CASCADE,
  cached_parse_json TEXT NOT NULL DEFAULT '{}',
  cached_classify_json TEXT NOT NULL DEFAULT '{}',
  cached_extract_json TEXT NOT NULL DEFAULT '{}',
  api_version TEXT,
  cached_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+09:00', 'now', '+9 hours')),
  expires_at TEXT
);

CREATE TABLE IF NOT EXISTS golden_dataset (
  case_id TEXT PRIMARY KEY,
  capture_id TEXT NOT NULL UNIQUE REFERENCES capture_records(capture_id) ON DELETE CASCADE,
  image_id TEXT NOT NULL UNIQUE,
  dataset_file_name TEXT NOT NULL,
  expected_doc_type TEXT NOT NULL CHECK (
    expected_doc_type IN ('notice', 'assignment', 'scholarship', 'receipt', 'place_link', 'noise')
  ),
  expected_fields_json TEXT NOT NULL DEFAULT '{}',
  evidence_text_json TEXT NOT NULL DEFAULT '{}',
  representative_query TEXT,
  is_ambiguous_sample INTEGER NOT NULL DEFAULT 0 CHECK (is_ambiguous_sample IN (0, 1)),
  loaded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+09:00', 'now', '+9 hours'))
);

CREATE TABLE IF NOT EXISTS test_report (
  report_id TEXT PRIMARY KEY,
  generated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+09:00', 'now', '+9 hours')),
  dataset_size INTEGER NOT NULL CHECK (dataset_size >= 0),
  ambiguous_sample_count INTEGER NOT NULL CHECK (ambiguous_sample_count >= 0),
  top3_accuracy REAL CHECK (top3_accuracy IS NULL OR top3_accuracy BETWEEN 0.0 AND 1.0),
  field_accuracy_json TEXT NOT NULL DEFAULT '{}',
  evidence_display_rate REAL CHECK (evidence_display_rate IS NULL OR evidence_display_rate BETWEEN 0.0 AND 1.0),
  no_answer_accuracy REAL CHECK (no_answer_accuracy IS NULL OR no_answer_accuracy BETWEEN 0.0 AND 1.0),
  hallucination_rate REAL CHECK (hallucination_rate IS NULL OR hallucination_rate BETWEEN 0.0 AND 1.0),
  needs_review_rate REAL CHECK (needs_review_rate IS NULL OR needs_review_rate BETWEEN 0.0 AND 1.0),
  answer_recall_rate REAL CHECK (answer_recall_rate IS NULL OR answer_recall_rate BETWEEN 0.0 AND 1.0),
  threshold_sweep_json TEXT NOT NULL DEFAULT '{}',
  ambiguous_activation_rate REAL CHECK (
    ambiguous_activation_rate IS NULL OR ambiguous_activation_rate BETWEEN 0.0 AND 1.0
  ),
  raw_report_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS correction_log (
  correction_id TEXT PRIMARY KEY,
  query_id TEXT,
  selected_capture_id TEXT REFERENCES capture_records(capture_id) ON DELETE SET NULL,
  previous_rank INTEGER CHECK (previous_rank IS NULL OR previous_rank >= 1),
  corrected_field TEXT,
  before_value_hash TEXT,
  after_value_hash TEXT,
  action TEXT NOT NULL CHECK (
    action IN ('doc_type_override', 'correction', 'fallback_select', 'qa_note')
  ),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+09:00', 'now', '+9 hours')),
  note_json TEXT NOT NULL DEFAULT '{}'
);
