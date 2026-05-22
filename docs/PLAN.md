# OdidujI — 어디두지 MVP 개발 실행 계획

## 프로젝트 목표

대학생이 저장해 둔 캡처 이미지에서 마감, 금액, 제출물, 신청 기간 정보를 다시 찾지 못해 생기는 손실을 줄이는 MVP를 구현한다.

MVP는 81장 golden dataset을 사전 인덱싱하고, 발표 중 JPG/PNG 캡처 1장을 라이브 업로드하며, 3개 고정 질문에 대해 원본 캡처, 근거 문장, 결과 카드 기반 답변을 제공한다.

## 확정 기술 스펙

- Frontend: HTML, CSS, JavaScript만 사용한다.
- Backend: 별도 FastAPI/Node.js 서버 없이 n8n 자체 Workflow만 사용한다.
- Storage: SQLite를 primary storage로 사용하고, 원본 이미지는 n8n 로컬 디스크에 저장한다.
- Trigger Webhook: `/webhook/image-upload`, `/webhook/question-submit` 2개만 사용한다.
- 이미지 입력: JPG/PNG만 허용하고 HEIC는 변환 없이 거부한다.
- Dataset: golden dataset 81장, 모호분류 샘플 3장.
- AI Pipeline: Upstage Document Parse → Document Classify → Schema Router → Information Extract → Solar Query Planner → Solar Evidence-bound Answer.
- QA: `test_report.json`은 Top-3, 필드 정확도, evidence 표시율, no-answer 정확도, 환각 답변률, needs_review, threshold sweep, ambiguous_activation_rate를 포함한다.

## 개발 단계

### Phase 0: 데이터 및 문서 정합성 정비

- 완료: `dataset/golden_dataset.json` 81건 확인.
- 완료: `img_005.HEIC`~`img_011.HEIC` 7개를 JPG 대체본으로 변환.
- 완료: `golden_dataset.json`의 HEIC `file_name`을 JPG 파일명으로 변경.
- 완료: 런타임 HEIC 변환 없이 HEIC는 거부하는 정책을 PRD/SRS와 일치시킴.
- 완료: `dataset/schema_definitions.json`의 taxonomy를 SRS 기준 6개 `doc_type`으로 정리.
- 완료: 기존 `place` doc_type을 `place_link`로 정규화하고, doc_type 누락 1건을 `noise`로 지정.

### Phase 1: 정적 Frontend 구현

- `frontend/index.html`, `frontend/style.css`, `frontend/app.js`만 사용한다.
- 업로드 UI는 JPG/PNG만 선택 가능하게 한다.
- HEIC/PDF/기타 파일은 즉시 `unsupported_file_type` 메시지를 표시한다.
- 3개 데모 질문 버튼을 고정 제공한다:
  - 이번 주 마감 과제 공지
  - 2만 원 넘는 영수증
  - 장학금 신청 기간
- 결과 카드에는 핵심 필드, confidence, needs_review, evidence_text, 원본 보기 링크를 표시한다.

### Phase 2: SQLite 및 n8n Workflow 기반 구축

- SQLite 테이블은 `capture_records`, `metadata_index`, `cache_entries`, `golden_dataset`, `test_report`, `correction_log`로 구성한다.
- 이미지 저장 경로는 `/static/captures/{capture_id}.{ext}` 규칙을 따른다.
- n8n Trigger Webhook은 2개만 만든다:
  - 이미지업로드 웹훅: `/webhook/image-upload`
  - 질문 전송 웹훅: `/webhook/question-submit`
- 상태 조회, 모호분류 선택, correction 저장, QA 리포트 생성은 별도 Webhook 없이 질문 전송 웹훅의 `action` 분기로 처리한다.

### Phase 3: 업로드 및 AI 인덱싱 파이프라인

- `/webhook/image-upload` 처리 순서:
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
- 동일 이미지 해시가 있으면 새 인덱스 생성 없이 기존 `capture_id`를 반환한다.

### Phase 4: 질문 전송 및 결과 카드 생성

- `/webhook/question-submit` 처리 순서:
  - `raw_query` 수신
  - Solar Query Planner로 intent/filter/sort_rule 생성
  - SQLite `metadata_index`에서 후보 Top-3 검색
  - evidence_text가 있는 필드만 사용해 Solar Evidence-bound Answer 생성
  - no-answer, relaxation_options, fallback 후보를 응답에 포함
- `action` 값으로 `status`, `doc_type_override`, `correction`, `qa_report` 보조 처리를 분기한다.

### Phase 5: QA 리포트 및 데모 안정화

- 81장 golden dataset 일괄 인덱싱 결과를 검증한다.
- 모호분류 3장의 `Classify_Ambiguous` 발화 또는 후보 유형 선택 흐름을 검증한다.
- 0.6/0.7/0.8 threshold sweep 결과를 `test_report.json`에 기록한다.
- Upstage API 실패 시 cache fallback과 백업 데모 데이터를 준비한다.
- 발표 전 3개 데모 질문을 반복 리허설한다.

## To-Do List

- [x] Phase 0 데이터 정합성 확인 및 HEIC 제거
- [x] Phase 0 `doc_type` taxonomy 정리
- [ ] Phase 1 정적 Frontend 화면/상태/결과 카드 구현
- [ ] Phase 2 SQLite 테이블 및 n8n Webhook 2개 구성
- [ ] Phase 3 업로드 인덱싱 Workflow 구현
- [ ] Phase 4 질문 전송 Workflow 및 evidence-bound 응답 구현
- [ ] Phase 5 QA 리포트와 발표 리허설 완료

## 검증 및 테스트 계획

- 파일 검증: JPG/PNG 업로드 성공, HEIC/PDF/기타 확장자 거부.
- Webhook 검증: `/webhook/image-upload`, `/webhook/question-submit` 외 Trigger Webhook이 없는지 확인.
- SQLite 검증: 6개 테이블 생성, 트랜잭션 쓰기, 중복 이미지 해시 처리.
- Dataset 검증: 81장 모두 JPG/PNG로 존재하고 `golden_dataset.json` 참조와 실제 파일명이 일치하는지 확인.
- AI 파이프라인 검증: Parse/Classify/Extract 결과가 `capture_id` 기준으로 SQLite에 저장되는지 확인.
- 질문 검증: 3개 고정 질문이 Top-3 후보와 결과 카드를 반환하는지 확인.
- 안전장치 검증: evidence 없는 필드는 no-answer 처리, 낮은 confidence는 needs_review 표시.
- QA 검증: `test_report.json`에 필수 지표 10개 이상과 ambiguous_activation_rate가 포함되는지 확인.

## 리스크 및 대응

- Upstage API 실패: 동일 이미지 해시 cache fallback과 백업 결과를 사용한다.
- Top-3 목표 미달: 4~10위 fallback 후보와 correction_log 저장으로 보완한다.
- n8n 단독 백엔드 한계: 복잡한 서버 로직을 Workflow/Code 노드와 SQLite 쿼리 범위 안으로 제한한다.
- 개인정보 노출: golden dataset과 원본 이미지에서 이름, 학번, 결제정보 원문 노출을 사전 검수한다.
- Webhook 증가 위험: 신규 Trigger Webhook을 만들지 않고 질문 전송 웹훅의 `action` 분기로 통합한다.
