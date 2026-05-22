# OdidujI — 어디두지 MVP 개발 실행 계획

## 프로젝트 목표

대학생이 저장해 둔 캡처 이미지에서 마감, 금액, 제출물, 신청 기간 정보를 다시 찾지 못해 생기는 손실을 줄이는 MVP를 구현한
다.

MVP는 81장 golden dataset을 사전 인덱싱하고, 발표 중 JPG/PNG 캡처 1장을 라이브 업로드하며, 3개 고정 질문에 대해 원본 캡처,
근거 문장, 결과 카드 기반 답변을 제공한다.

## 확정 기술 스펙

- Frontend: HTML, CSS, JavaScript만 사용한다.
- Backend: 별도 FastAPI/Node.js 서버 없이 n8n 자체 Workflow만 사용한다.
- Storage: SQLite를 primary storage로 사용하고, 원본 이미지는 n8n 로컬 디스크에 저장한다.
- Trigger Webhook: /webhook/image-upload, /webhook/question-submit 2개만 사용한다.
- 이미지 입력: JPG/PNG만 허용하고 HEIC는 변환 없이 거부한다.
- Dataset: golden dataset 81장, 모호분류 샘플 3장.
- AI Pipeline: Upstage Document Parse → Document Classify → Schema Router → Information Extract → Solar Query Planner →
  Solar Evidence-bound Answer.
- QA: test_report.json은 Top-3, 필드 정확도, evidence 표시율, no-answer 정확도, 환각 답변률, needs_review, threshold
  sweep, ambiguous_activation_rate를 포함한다.

## 개발 단계

### Phase 0: 데이터 및 문서 정합성 정비

- dataset/golden_dataset.json이 81건인지 확인한다.
- 현재 dataset에 남아 있는 img_005.HEIC~img_011.HEIC 7개를 JPG/PNG 대체본으로 교체한다.
- golden_dataset.json의 file_name도 JPG/PNG 파일명으로 맞춘다.
- 런타임 HEIC 변환 로직은 만들지 않는다.
- dataset/schema_definitions.json과 SRS의 6개 doc_type이 일치하는지 확인한다.

### Phase 1: 정적 Frontend 구현

- frontend/index.html, frontend/style.css, frontend/app.js만 사용한다.
- 업로드 UI는 JPG/PNG만 선택 가능하게 한다.
- HEIC/PDF/기타 파일은 즉시 unsupported_file_type 메시지를 표시한다.
- 3개 데모 질문 버튼을 고정 제공한다:
  - 이번 주 마감 과제 공지
  - 2만 원 넘는 영수증
  - 장학금 신청 기간
- 결과 카드에는 핵심 필드, confidence, needs_review, evidence_text, 원본 보기 링크를 표시한다.

### Phase 2: SQLite 및 n8n Workflow 기반 구축

- SQLite 테이블은 capture_records, metadata_index, cache_entries, golden_dataset, test_report, correction_log로 구성한다.
- 이미지 저장 경로는 /static/captures/{capture_id}.{ext} 규칙을 따른다.
- n8n Trigger Webhook은 2개만 만든다:
  - 이미지업로드 웹훅: /webhook/image-upload
  - 질문 전송 웹훅: /webhook/question-submit
- 상태 조회, 모호분류 선택, correction 저장, QA 리포트 생성은 별도 Webhook 없이 질문 전송 웹훅의 action 분기로 처리한다.

### Phase 3: 업로드 및 AI 인덱싱 파이프라인

- /webhook/image-upload 처리 순서:
  - 파일 수신
  - JPG/PNG 확장자 및 MIME 검증
  - 10MB 이하 크기 검증
  - HEIC 거부
  - 원본 이미지 저장
  - Upstage Document Parse
  - Upstage Document Classify
  - Schema Router
  - Upstage Information Extract
  - 날짜/금액 정규화
  - needs_review 판정
  - SQLite 저장
- 동일 이미지 해시가 있으면 새 인덱스 생성 없이 기존 `capture_id# PLAN.md 작성 실행 계획
