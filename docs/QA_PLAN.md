# 어디두지 v1.0 MVP — 수용기준 및 검증 계획

| 항목 | 내용 |
| --- | --- |
| 문서 유형 | Acceptance Criteria & Validation Plan |
| 제품명 | OdidujI — 어디두지 |
| 버전/마일스톤 | v1.0 MVP |
| Target Release | 2026-05-22 |
| 기술 스택 | HTML / Tailwind CSS / JavaScript / n8n / IndexedDB / Local JSON DB / Upstage APIs |
| 작성 기준 | `PRD.md`, `SRS.md`, `LOCOMOCO_기획서_v4.pdf` |
| 상태 | Draft |

## 0. 검증 원칙

본 검증 계획의 목적은 어디두지 v1.0 MVP가 “학생용 캡처 정보 검색함”으로서 30장 고정 캡처와 3개 대표 질문에 대해 원본 캡처, 근거 문장, 결과 카드, no-answer 정책을 안정적으로 제공하는지 확인하는 것이다.

검증은 다음 3개 증거 레이어를 모두 사용한다.

| Evidence Layer | 설명 | 필수 여부 |
| --- | --- | --- |
| 기능 결과 증거 | UI, n8n 응답, Local JSON DB, QA 리포트에서 기능 결과를 확인 | 필수 |
| 수동 확인 증거 | QA 담당자가 브라우저 화면에서 결과 카드, 원본 캡처, 근거 문장, 오류 메시지, 조건 완화 옵션을 직접 확인 | 필수 |
| 브라우저 저장소 확인 증거 | Chrome DevTools 또는 동등 도구로 IndexedDB, Local Storage, Session Storage에 저장된 값과 보안 금지 항목을 직접 확인 | 필수 |

## 1. Release Acceptance Gate

v1.0 MVP는 아래 Gate를 모두 통과해야 데모 가능 상태로 간주한다.

| Gate ID | Release Gate | Pass Criteria | Evidence |
| --- | --- | --- | --- |
| RG-001 | 30장 golden dataset 인덱싱 완료 | `indexed_count=30`, `capture_record` 30개 생성 | `/data/metadata_index.json`, `/data/capture_records.json`, `indexing_summary` |
| RG-002 | 3개 대표 데모 질문 성공 | `이번 주 마감 과제 공지`, `2만 원 넘는 영수증`, `장학금 신청 기간` 각각 1회 실행 성공. 성공률 3/3 | UI 녹화, n8n `/webhook/query` response, `/data/test_report.json` |
| RG-003 | Top-3 정답 포함률 | 30개 대표 질의 중 Top-3 내 정답 포함률 ≥ 90% | `/data/test_report.json` |
| RG-004 | 핵심 필드 추출 정확도 | 마감·기간 ≥ 90%, 금액 ≥ 95%, 제출물 ≥ 85% | `/data/test_report.json`, golden dataset 비교표 |
| RG-005 | 근거 기반 답변 | 근거 문장 표시율 ≥ 95%, 근거 없는 필드 환각 답변률 0% | UI 수동 확인, `cited_fields`, `evidence_text` 검사 |
| RG-006 | no-answer 안전장치 | 관련 없는 질문 5개 no-answer 정확도 100% | no-answer test run, UI 수동 확인 |
| RG-007 | 브라우저 저장소 안전성 | IndexedDB에 `query_history` 저장, API Key·원본 개인정보 원문 저장 0건 | DevTools Application 탭 inspection 결과 |
| RG-008 | 보안 노출 차단 | Frontend HTML/CSS/JS/IndexedDB에 Upstage API Key 노출 0건 | static grep, DevTools Sources/Storage inspection |
| RG-009 | 캐시 fallback | 사전 인덱싱 30장 API 실패 시 fallback success 100% | API mock failure test, `cache_hit=true` log |
| RG-010 | MVP 제외 범위 준수 | 사진첩 자동 동기화, 캘린더 실연동, 메신저 channel adapter, 자유형 챗봇, 별도 Backend 호출 없음 | Network tab, scope checklist |

## 2. Acceptance Criteria

### AC-001. 수동 업로드 및 파일 검증

- **Priority**: P0
- **Related Requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, IR-UI-001~003, IR-N8N-001, NFR-USA-001, NFR-CMP-001, NFR-SEC-001

| AC ID | Given | When | Then | Pass Criteria |
| --- | --- | --- | --- | --- |
| AC-001-01 | 사용자가 JPG/PNG/HEIC 이미지 1장을 선택한 상태 | 업로드 버튼을 클릭한다 | Frontend는 n8n `/webhook/capture-upload`로 `multipart/form-data.image`를 전송한다 | 1초 이내 `upload_job_id`, `capture_id`, `status=received`가 UI에 표시됨 |
| AC-001-02 | 사용자가 `.pdf`, `.txt`, `.zip` 등 미지원 파일을 선택한 상태 | 업로드를 시도한다 | 시스템은 업로드를 거부한다 | `reject_reason=unsupported_file_type`, Upstage API 호출 0건 |
| AC-001-03 | 사용자가 10MB 초과 이미지를 선택한 상태 | 업로드를 시도한다 | 시스템은 업로드를 거부한다 | `reject_reason=file_too_large`, Upstage API 호출 0건 |
| AC-001-04 | 사용자가 HEIC 파일을 업로드한 상태 | 정규화가 실행된다 | 시스템은 JPG 변환 파일을 생성한다 | `normalized_format=jpg`, `source_image_path` 생성 |
| AC-001-05 | 검증 완료 이미지가 있는 상태 | 저장 노드가 실행된다 | 원본 또는 정규화 이미지를 n8n 로컬 디스크에 저장한다 | `/static/captures/{capture_id}.{ext}` 생성, 사용자 원본 파일명 미사용 |

### AC-002. Golden Dataset 30장 사전 인덱싱

- **Priority**: P0
- **Related Requirements**: FR-006~013, FR-024, FR-033, DR-001~012, NFR-AVL-002~004

| AC ID | Given | When | Then | Pass Criteria |
| --- | --- | --- | --- | --- |
| AC-002-01 | `/data/golden_dataset.json`과 `/static/captures/*`에 30장 캡처가 준비된 상태 | 일괄 인덱싱 workflow를 실행한다 | 시스템은 30개 `capture_record`와 metadata record를 생성한다 | `indexed_count=30`, 누락 capture 0건 |
| AC-002-02 | 동일 이미지 해시가 이미 존재하는 상태 | 동일 이미지를 다시 인덱싱한다 | 신규 record를 만들지 않고 기존 `capture_id`를 반환한다 | 중복 record 0건, 기존 `capture_id` 반환 |
| AC-002-03 | Upstage API가 실패하고 동일 이미지 해시 cache가 있는 상태 | 인덱싱 또는 재질의를 실행한다 | cache fallback을 반환한다 | `cache_hit=true`, UI 로그에 cache 사용 표시 |
| AC-002-04 | `metadata_index.json` 업데이트가 필요한 상태 | JSON write가 실행된다 | 업데이트 전 백업 파일을 생성한다 | `metadata_index.backup.{timestamp}.json` 생성률 100% |

### AC-003. 문서 파싱·분류·스키마 라우팅·정보 추출

- **Priority**: P0
- **Related Requirements**: FR-006, FR-007, FR-008, FR-009, IR-EXT-001~003, DR-002~004

| AC ID | Given | When | Then | Pass Criteria |
| --- | --- | --- | --- | --- |
| AC-003-01 | 저장된 캡처 이미지가 있는 상태 | Upstage Document Parse가 완료된다 | `parsed_markdown`, `layout_blocks`, `evidence_candidates`, `parse_confidence`를 저장한다 | 필수 필드 누락 0건, confidence 0.00~1.00 범위 |
| AC-003-02 | `parsed_markdown`이 저장된 캡처가 있는 상태 | Document Classify가 실행된다 | 6개 허용 라벨 중 하나를 `doc_type`으로 저장한다 | `assignment`, `notice`, `scholarship`, `receipt`, `place_link`, `noise` 외 라벨 0건 |
| AC-003-03 | `doc_type=receipt`인 캡처가 있는 상태 | Schema Router가 실행된다 | 영수증 추출용 `schema_json`을 반환한다 | `extract_schema_id`와 `schema_json` 매핑 성공 |
| AC-003-04 | 선택된 스키마와 `parsed_markdown`이 있는 상태 | Information Extract가 실행된다 | doc_type별 핵심 필드와 `evidence_text`를 저장한다 | 각 ExtractedField는 `evidence_text` 또는 `no_evidence_reason` 보유 |

### AC-004. 날짜·금액 정규화 및 확인 필요 판정

- **Priority**: P0
- **Related Requirements**: FR-010, FR-011, FR-012, DR-RULE-004~008, NFR-QLT-003~005, NFR-QLT-009

| AC ID | Given | When | Then | Pass Criteria |
| --- | --- | --- | --- | --- |
| AC-004-01 | `evidence_text="5월 20일 23:59까지"`가 있는 상태 | 날짜 정규화가 실행된다 | KST ISO-8601 형식으로 저장한다 | `2026-05-20T23:59:00+09:00` 형식 |
| AC-004-02 | 시간 정보 없는 날짜가 추출된 상태 | 날짜 정규화가 실행된다 | 기본 마감 시간을 적용한다 | `23:59:00+09:00` 적용 |
| AC-004-03 | `evidence_text="23,500원"`이 있는 상태 | 금액 정규화가 실행된다 | KRW 정수 값으로 저장한다 | `normalized_amount=23500`, `currency=KRW` |
| AC-004-04 | 금액 후보가 2개 이상이고 확정 불가한 상태 | 금액 정규화가 실행된다 | 충돌 상태를 표시한다 | `amount_conflict=true`, `needs_review=true` |
| AC-004-05 | parse/classify/extract confidence 중 하나가 0.70 미만인 상태 | needs_review 판정이 실행된다 | 확인 필요 상태로 저장한다 | `needs_review=true`, UI에서 숨김 0건 |

### AC-005. 3개 대표 데모 질문 버튼 및 Query Planner

- **Priority**: P0
- **Related Requirements**: FR-014, FR-015, FR-016, FR-022, IR-UI-005, IR-N8N-003, NFR-QLT-001~002

| AC ID | Given | When | Then | Pass Criteria |
| --- | --- | --- | --- | --- |
| AC-005-01 | 데모 화면이 열린 상태 | `이번 주 마감 과제 공지` 버튼을 클릭한다 | query_plan이 과제·이번 주·마감일 오름차순 검색으로 생성된다 | `target_doc_type=assignment`, `deadline_range=this_week`, `sort_rule=deadline_asc` |
| AC-005-02 | 데모 화면이 열린 상태 | `2만 원 넘는 영수증` 버튼을 클릭한다 | query_plan이 영수증·금액 하한 검색으로 생성된다 | `target_doc_type=receipt`, `amount_min=20000` |
| AC-005-03 | 데모 화면이 열린 상태 | `장학금 신청 기간` 버튼을 클릭한다 | query_plan이 장학금 신청 기간 검색으로 생성된다 | `target_doc_type=scholarship`, `query_intent=find_application_period` |
| AC-005-04 | 허용되지 않은 `doc_type` 또는 `filter_key`가 query_plan에 포함된 상태 | 유효성 검증이 실행된다 | 질의 실행을 중단한다 | `query_plan_valid=false`, `query_plan_invalid` 반환 |

### AC-006. Top-3 검색 및 Evidence-bound Answer

- **Priority**: P0
- **Related Requirements**: FR-016, FR-017, FR-018, NFR-QLT-002, NFR-QLT-006~008

| AC ID | Given | When | Then | Pass Criteria |
| --- | --- | --- | --- | --- |
| AC-006-01 | 유효한 query_plan이 있는 상태 | Local JSON DB 검색이 실행된다 | 후보 Top-3를 반환한다 | 후보 수 ≤ 3, 정렬 규칙 준수 |
| AC-006-02 | 30개 대표 질의가 준비된 상태 | Top-3 검색 평가를 실행한다 | 정답 캡처가 Top-3에 포함된다 | Top-3 정답 포함률 ≥ 90% |
| AC-006-03 | 후보 카드와 `evidence_text`가 있는 상태 | Evidence-bound Answer가 실행된다 | 답변은 후보 카드와 근거 문장 범위 안에서만 생성된다 | 답변 필드가 모두 `cited_fields`에 존재 |
| AC-006-04 | 요청 필드에 `evidence_text`가 없는 상태 | 답변 생성이 실행된다 | no-answer를 반환한다 | `no_answer=true`, `no_answer_reason=missing_evidence_text` |
| AC-006-05 | 관련 없는 질문 5개가 입력된 상태 | 질의를 실행한다 | 허위 답변 없이 no-answer 처리한다 | no-answer 정확도 100%, 환각 답변률 0% |

### AC-007. 손실 위험 결과 카드, 근거 문장, 원본 캡처

- **Priority**: P0
- **Related Requirements**: FR-019, FR-020, FR-021, NFR-PER-002, NFR-USA-002, NFR-QLT-006

| AC ID | Given | When | Then | Pass Criteria |
| --- | --- | --- | --- | --- |
| AC-007-01 | 과제 후보 카드가 있는 상태 | 결과 화면이 렌더링된다 | 과목명, D-day/deadline, 제출물, 근거 문장, 원본 캡처 링크를 표시한다 | 존재하는 필드 표시율 100%, 빈 필드 렌더링 0건 |
| AC-007-02 | 영수증 후보 카드가 있는 상태 | 결과 화면이 렌더링된다 | 금액, 상호명, 결제일, 근거 문장, 원본 캡처 링크를 표시한다 | 금액 KRW 표시, source link 정상 |
| AC-007-03 | 장학금 후보 카드가 있는 상태 | 결과 화면이 렌더링된다 | 신청 기간, 기관명, 필요 서류, 근거 문장을 표시한다 | evidence_text 존재 필드만 답변 |
| AC-007-04 | 결과 카드에 `evidence_text`가 있는 상태 | 원문 보기 영역을 연다 | 동일 문장을 하이라이트한다 | evidence highlight 표시율 ≥ 95% |
| AC-007-05 | 결과 카드에 `source_image_path`가 있는 상태 | 사용자가 “원본 보기”를 클릭한다 | 원본 캡처 뷰어가 열린다 | P95 ≤ 2초, 로딩 실패 0건 |

### AC-008. no-answer 조건 완화 UI

- **Priority**: P0
- **Related Requirements**: FR-018, FR-025, IR-UI-008, NFR-USA-004

| AC ID | Given | When | Then | Pass Criteria |
| --- | --- | --- | --- | --- |
| AC-008-01 | `no_candidate=true` 또는 no-answer가 발생한 상태 | no-answer UI가 표시된다 | 조건 완화 옵션을 제공한다 | 1~3개 옵션 표시 |
| AC-008-02 | 조건 완화 옵션이 표시된 상태 | QA가 옵션 목록을 확인한다 | 허용된 옵션만 표시된다 | `date_range_expand_7d`, `search_all_doc_type`, `include_needs_review` 외 옵션 0건 |
| AC-008-03 | no-answer 화면이 표시된 상태 | 사용자가 원본 확인 또는 조건 완화를 선택한다 | 다음 행동으로 이동할 수 있다 | CTA 누락 0건 |

### AC-009. IndexedDB 클라이언트 캐시 및 브라우저 저장소 안전성

- **Priority**: P0
- **Related Requirements**: FR-034, IR-UI-004, NFR-PER-005, NFR-USA-005, NFR-SEC-001, NFR-SEC-005, DR-011, DR-RULE-009~010

| AC ID | Given | When | Then | Pass Criteria |
| --- | --- | --- | --- | --- |
| AC-009-01 | 사용자가 데모 질문을 1회 실행한 상태 | 결과가 화면에 표시된다 | IndexedDB에 최근 질의가 저장된다 | `odiduji_client_store.query_history`에 `raw_query`, `query_id`, `created_at` 저장 |
| AC-009-02 | 사용자가 결과 카드를 확인한 상태 | 브라우저를 새로고침한다 | 최근 질의와 UI 상태가 복원된다 | 최근 질의 5건 복원율 100%, P95 ≤ 0.5초 |
| AC-009-03 | IndexedDB 저장이 실행된 상태 | DevTools Storage inspection을 수행한다 | API Key와 원본 개인정보 원문이 저장되어 있지 않다 | Upstage API Key 0건, 이름·학번·카드번호 원문 0건 |
| AC-009-04 | IndexedDB에 `result_cache`가 저장된 상태 | QA가 저장 데이터를 확인한다 | IndexedDB는 source of truth가 아니라 클라이언트 캐시로만 동작한다 | Local JSON DB와 불일치 시 Local JSON DB 기준으로 재조회 |
| AC-009-05 | 사용자가 notification preference placeholder를 확인한 상태 | DevTools에서 store를 확인한다 | 알림 관련 값은 설정 초안 또는 비활성 상태로만 저장된다 | 실제 예약 알림 job 생성 0건 |

### AC-010. QA 리포트 생성

- **Priority**: P0
- **Related Requirements**: FR-031, NFR-QLT-001~011, DR-008, DR-RULE-013, IR-N8N-006

| AC ID | Given | When | Then | Pass Criteria |
| --- | --- | --- | --- | --- |
| AC-010-01 | 30장 golden dataset과 대표 질의가 준비된 상태 | QA 테스트를 실행한다 | `/data/test_report.json`을 생성한다 | 파일 생성 성공, UTF-8 저장 |
| AC-010-02 | QA 리포트가 생성된 상태 | 필수 지표를 검토한다 | 9개 필수 QA 지표가 포함된다 | 대표 데모 질문 성공률, Top-3 정답 포함률, 마감·기간 추출 정확도, 금액 추출 정확도, 제출물 추출 정확도, 근거 문장 표시율, no-answer 정확도, 환각 답변률, 확인 필요 UI 동작률 포함 |
| AC-010-03 | threshold sweep과 ambiguous sample 결과가 MVP 보류 상태 | QA 리포트를 확인한다 | deferred_items에 보류 항목을 기록한다 | `deferred_items`에 `threshold_sweep_result`, `ambiguous_sample_result` 포함 |

### AC-011. n8n 처리 로그 표시

- **Priority**: P1
- **Related Requirements**: FR-023, IR-N8N-002, IR-EXT-006, NFR-PER-003, NFR-AVL-002

| AC ID | Given | When | Then | Pass Criteria |
| --- | --- | --- | --- | --- |
| AC-011-01 | 라이브 업로드가 시작된 상태 | n8n workflow 단계가 진행된다 | UI가 처리 로그를 단계별로 표시한다 | `received`, `validated`, `normalized`, `parsed`, `classified`, `schema_routed`, `extracted`, `indexed`, `ready` 표시 |
| AC-011-02 | 라이브 업로드 리허설 5회가 실행된 상태 | 인덱싱 시간을 측정한다 | 지정 시간 안에 완료한다 | P95 ≤ 30초 |
| AC-011-03 | Upstage API 실패가 발생한 상태 | retry가 실행된다 | 최대 2회 재시도 후 fallback 또는 실패 메시지를 표시한다 | backoff 1초/3초, 상태 로그 표시 |

### AC-012. 모호 분류 후보 선택 및 재추출

- **Priority**: P1
- **Related Requirements**: FR-026, FR-027, FR-028, IR-UI-007, NFR-USA-003

| AC ID | Given | When | Then | Pass Criteria |
| --- | --- | --- | --- | --- |
| AC-012-01 | top1 `category_confidence < 0.70`인 상태 | 분류 상태 판정이 실행된다 | `Classify_Ambiguous`로 저장한다 | 판정 성공 |
| AC-012-02 | top1/top2 confidence 차이가 0.10 미만인 상태 | 분류 상태 판정이 실행된다 | `Classify_Ambiguous`로 저장한다 | 판정 성공 |
| AC-012-03 | `Classify_Ambiguous` 상태인 캡처가 있는 상태 | 후보 유형 UI가 열린다 | confidence 상위 3개 후보와 대표 키워드를 표시한다 | 후보 최대 3개, 키워드 후보당 최대 3개 |
| AC-012-04 | 사용자가 후보 유형을 선택한 상태 | 재추출이 실행된다 | 선택 doc_type 스키마로 Information Extract를 재실행한다 | `user_override_doc_type=true`, 기존 결과는 `previous_extract_result`로 보존 |

### AC-013. Top-3 실패 fallback 및 correction_log

- **Priority**: P1
- **Related Requirements**: FR-029, FR-030, DR-009, NFR-COMP-003

| AC ID | Given | When | Then | Pass Criteria |
| --- | --- | --- | --- | --- |
| AC-013-01 | Top-3 결과가 표시된 상태 | 사용자가 “찾는 캡처가 없음”을 클릭한다 | 4~10위 fallback 후보를 표시한다 | evidence_text가 있는 후보만 최대 7개 표시 |
| AC-013-02 | 사용자가 fallback 후보 중 정답 캡처를 선택한 상태 | 수정 저장이 실행된다 | `/data/correction_log.json`에 수정 이력을 저장한다 | `query_id`, `selected_capture_id`, `previous_rank`, `corrected_field`, `created_at` 저장 |
| AC-013-03 | correction_log가 저장된 상태 | QA가 로그를 검토한다 | 개인정보 원문이 저장되지 않는다 | 이름·학번·카드번호 원문 0건, hash만 저장 |

### AC-014. 브라우저 알림 확장 계획 문서화

- **Priority**: P2
- **Related Requirements**: FR-032, NFR-SCL-003, IR-EXT-007, CON-021

| AC ID | Given | When | Then | Pass Criteria |
| --- | --- | --- | --- | --- |
| AC-014-01 | deadline이 있는 risk_card가 존재하는 상태 | 확장 계획 문서를 검토한다 | 브라우저 알림 권한 요청 흐름과 스케줄 규칙이 문서화되어 있다 | `/data/notification_plan.json`에 `D-1 09:00 KST`, `D-day 09:00 KST`, permission flow 포함 |
| AC-014-02 | MVP 범위 검토가 진행되는 상태 | 실제 예약 알림 구현 여부를 확인한다 | 실제 예약 알림은 구현 범위에 포함되지 않는다 | 알림 예약 job 0건, UI는 disabled placeholder 또는 문서 링크만 제공 |
| AC-014-03 | 확장 계획을 검토하는 상태 | 메신저 channel adapter 여부를 확인한다 | 메신저 channel adapter가 제외되어 있다 | 관련 field/API/adapter 0건 |

## 3. Verification Plan

### 3.1 테스트 범위

| Scope | 포함 | 제외 |
| --- | --- | --- |
| Functional | 업로드, 검증, HEIC 정규화, 사전 인덱싱, Parse/Classify/Extract, Query Planner, Top-3 검색, Evidence-bound Answer, no-answer, Risk Card, IndexedDB cache, QA 리포트 | 사진첩 자동 동기화, 캘린더 실연동, 메신저 channel adapter, 자유형 챗봇, 별도 Backend 서버 |
| Non-Functional | 성능, 보안, 가용성, Local JSON DB 무결성, 브라우저 저장소 안전성, 호환성 smoke test | 장기 대량 인덱싱, 실제 예약 알림, threshold sweep 산출 |
| Manual | UI 표시, 원본 캡처, 근거 문장 하이라이트, error message, 조건 완화, 확인 필요 badge | 자동화만으로 충분한 JSON schema validation의 반복 수동 점검 |
| Browser Storage | IndexedDB object store, Local/Session Storage, API Key·PII 미저장, 새로고침 복원 | n8n 로컬 디스크 파일의 브라우저 직접 접근 |

### 3.2 테스트 환경

| 항목 | 기준 |
| --- | --- |
| Browser | Chrome 최신 안정 버전 1개를 기준 브라우저로 사용. Edge/Safari는 핵심 플로우 smoke test |
| Frontend | HTML / Tailwind CSS / Vanilla JavaScript 정적 UI |
| Workflow | n8n local 또는 단일 데모 서버 |
| Storage | IndexedDB `odiduji_client_store`, n8n Local JSON DB `/data/*.json`, capture path `/static/captures/*` |
| Dataset | 30장 golden dataset + 1장 라이브 업로드 이미지 + negative upload 파일 10종 + 관련 없는 질문 5개 |
| Observability | n8n execution log, browser Network tab, browser Performance API, DevTools Application tab, filesystem inspection |

### 3.3 테스트 데이터

| Dataset ID | 구성 | 목적 |
| --- | --- | --- |
| TD-001 | 과제 6장 | deadline, course, required_submission, action_items 추출 검증 |
| TD-002 | 학사·행정 공지 7장 | deadline, institution, action_items 추출 검증 |
| TD-003 | 장학금 5장 | date_range, deadline, institution, required_submission 검증 |
| TD-004 | 영수증 6장 | amount, merchant, payment_date 검증 |
| TD-005 | 장소·링크 4장 | address, url, date_range 검증. MVP 핵심 데모 외 보조 검증 |
| TD-006 | 실패·노이즈 2장 | needs_review, no-answer, parse_confidence 검증 |
| TD-007 | 관련 없는 질문 5개 | no-answer 정확도와 환각 답변률 검증 |
| TD-008 | invalid upload files 10종 | 확장자/MIME 차단 검증 |
| TD-009 | 1장 라이브 업로드 이미지 | 발표 중 수동 업로드 및 n8n 처리 로그 검증 |

## 4. Test Cases

### 4.1 P0 Functional Test Cases

| Test ID | 검증 항목 | 연관 AC/요구사항 | 절차 | Expected Result | Evidence | 검증 방식 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-FN-001 | 정상 이미지 업로드 | AC-001 / FR-001 | JPG 1장 선택 → 업로드 클릭 | 1초 이내 `upload_job_id`, `capture_id`, `status=received` 표시 | UI screenshot, Network request, n8n log | 자동+수동 확인 |
| TC-FN-002 | 미지원 확장자 차단 | AC-001 / FR-002 | `.pdf`, `.zip`, `.txt` 업로드 시도 | `reject_reason=unsupported_file_type`, Upstage 호출 없음 | UI error, n8n log | 자동+수동 확인 |
| TC-FN-003 | 10MB 초과 차단 | AC-001 / FR-003 | 10MB 초과 이미지 업로드 | `reject_reason=file_too_large` | UI error, n8n log | 자동+수동 확인 |
| TC-FN-004 | HEIC 정규화 | AC-001 / FR-004 | HEIC 이미지 업로드 | JPG 변환 경로 생성, `normalized_format=jpg` | n8n log, `/static/captures/*` | 자동+수동 확인 |
| TC-FN-005 | 30장 일괄 인덱싱 | AC-002 / FR-033 | batch indexing 실행 | `indexed_count=30` | `indexing_summary`, Local JSON DB | 자동 |
| TC-FN-006 | Parse/Classify/Extract 파이프라인 | AC-003 / FR-006~009 | 30장 인덱싱 후 필드 검사 | `parsed_markdown`, `doc_type`, `schema_json`, `evidence_text` 저장 | `metadata_index.json`, n8n log | 자동 |
| TC-FN-007 | 날짜 정규화 | AC-004 / FR-010 | 날짜 근거 문장 케이스 실행 | KST ISO-8601 저장 | `metadata_index.json` | 자동 |
| TC-FN-008 | 금액 정규화 | AC-004 / FR-011 | 영수증 6장 amount 비교 | KRW 정수 저장, 정확도 ≥ 95% | `test_report.json` | 자동 |
| TC-FN-009 | needs_review 표시 | AC-004 / FR-012 | 낮은 confidence 샘플 2장 검색 | UI에 확인 필요 badge 표시 | UI screenshot, `needs_review=true` | 수동 확인 |
| TC-FN-010 | 과제 데모 질문 | AC-005~007 / FR-014~022 | `이번 주 마감 과제 공지` 클릭 | 과제 후보 Top-3, deadline 오름차순, 근거 표시 | UI screenshot, query response | 자동+수동 확인 |
| TC-FN-011 | 영수증 데모 질문 | AC-005~007 / FR-014~022 | `2만 원 넘는 영수증` 클릭 | 20,000원 초과 영수증 카드, 원본 링크 표시 | UI screenshot, query response | 자동+수동 확인 |
| TC-FN-012 | 장학금 데모 질문 | AC-005~007 / FR-014~022 | `장학금 신청 기간` 클릭 | 신청 기간, 기관, 제출물, 근거 표시 | UI screenshot, query response | 자동+수동 확인 |
| TC-FN-013 | no-answer | AC-006, AC-008 / FR-018, FR-025 | 관련 없는 질문 5개 입력 | no-answer 100%, 조건 완화 1~3개 표시 | UI screenshot, response JSON | 자동+수동 확인 |
| TC-FN-014 | 원본 캡처 뷰어 | AC-007 / FR-021 | 결과 카드의 “원본 보기” 클릭 | 2초 이내 원본 캡처 표시 | Performance timing, UI screenshot | 수동 확인 |
| TC-FN-015 | 근거 문장 하이라이트 | AC-007 / FR-020 | 결과 카드에서 원문 보기 열기 | `evidence_text` 동일 문장 하이라이트 | UI screenshot | 수동 확인 |
| TC-FN-016 | QA 리포트 생성 | AC-010 / FR-031 | `/webhook/qa-report` 실행 | 필수 9개 지표와 deferred_items 포함 | `/data/test_report.json` | 자동+수동 확인 |

### 4.2 P1/P2 Functional Test Cases

| Test ID | 검증 항목 | 연관 AC/요구사항 | 절차 | Expected Result | Evidence | 검증 방식 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-FN-017 | n8n 처리 로그 표시 | AC-011 / FR-023 | 라이브 업로드 1장 실행 | 9개 처리 단계와 완료 시각 표시 | UI screenshot, n8n execution log | 수동 확인 |
| TC-FN-018 | 라이브 업로드 P95 | AC-011 / NFR-PER-003 | 라이브 업로드 5회 리허설 | P95 ≤ 30초 | timing log | 자동 |
| TC-FN-019 | Classify_Ambiguous 판정 | AC-012 / FR-026 | synthetic ambiguous case 실행 | `Classify_Ambiguous` 저장 | response JSON | 자동 |
| TC-FN-020 | 후보 유형 선택 UI | AC-012 / FR-027 | ambiguous UI 열기 | 후보 최대 3개 표시 | UI screenshot | 수동 확인 |
| TC-FN-021 | 사용자 선택 유형 재추출 | AC-012 / FR-028 | 후보 doc_type 선택 | 재추출, `user_override_doc_type=true` | response JSON, n8n log | 자동+수동 확인 |
| TC-FN-022 | Top-3 실패 fallback | AC-013 / FR-029 | “찾는 캡처가 없음” 클릭 | 4~10위 후보 중 evidence 있는 후보 최대 7개 표시 | UI screenshot | 수동 확인 |
| TC-FN-023 | correction_log 저장 | AC-013 / FR-030 | fallback 후보 선택 후 저장 | correction_log 생성, PII 원문 미저장 | `/data/correction_log.json` | 자동+수동 확인 |
| TC-FN-024 | 브라우저 알림 확장 계획 | AC-014 / FR-032 | `notification_plan.json` 검토 | permission flow, D-1/D-day 규칙, IndexedDB 필드, 제한사항 포함 | `/data/notification_plan.json` | 수동 확인 |
| TC-FN-025 | 메신저 adapter 제외 | AC-014 / CON-018 | 코드/문서/API 검색 | messenger/channel adapter 관련 구현 0건 | grep result, Network tab | 수동 확인 |

### 4.3 Non-Functional Test Cases

| Test ID | 검증 항목 | 관련 요구사항 | 절차 | Pass Criteria | Evidence |
| --- | --- | --- | --- | --- | --- |
| TC-NF-001 | 사전 인덱싱 질의 응답 성능 | NFR-PER-001 | 30개 대표 질의 실행 | P95 ≤ 1.5초 | timing report |
| TC-NF-002 | 결과 카드 첫 렌더링 성능 | NFR-PER-002 | 3개 데모 질문 반복 실행 | P95 ≤ 2.0초 | Browser Performance API |
| TC-NF-003 | 캐시 hit 반환 성능 | NFR-PER-004 | cache hit 10회 실행 | P95 ≤ 1.0초 | timing report |
| TC-NF-004 | IndexedDB 복원 성능 | NFR-PER-005 | 새로고침 후 최근 질의 복원 10회 | P95 ≤ 0.5초 | DevTools + timing log |
| TC-NF-005 | API Key 노출 검사 | NFR-SEC-001 | 정적 파일 grep, DevTools Sources/Storage 검사 | secret exposure 0건 | grep log, screenshot |
| TC-NF-006 | 데모 데이터 PII 마스킹 | NFR-SEC-002, NFR-COMP-001 | golden dataset 검수 | 이름·학번·결제정보 원문 노출 0건 | QA checklist |
| TC-NF-007 | Unsupported MIME 차단 | NFR-SEC-003 | 악성 확장자/MIME 10종 업로드 | 차단율 100% | negative test report |
| TC-NF-008 | Local JSON DB backup | NFR-AVL-004 | metadata update 실행 | 백업 생성률 100% | filesystem screenshot |
| TC-NF-009 | JSON encoding | NFR-COMP-004 | `/data/*.json` 인코딩 검사 | UTF-8 저장률 100% | encoding check log |
| TC-NF-010 | 주요 브라우저 smoke | NFR-CMP-002 | Chrome/Edge/Safari 핵심 플로우 | 주요 플로우 성공률 100% | browser matrix report |
| TC-NF-011 | Tailwind 적용률 | NFR-CMP-004 | 주요 화면 4개 class inspection | Tailwind 적용률 100% | DOM inspection screenshot |

## 5. Manual Verification Checklist

수동 확인은 자동 테스트 통과 후 QA 담당자가 브라우저에서 실제 사용자처럼 수행한다. 아래 항목은 릴리즈 전 모두 Pass 또는 Known Issue로 기록해야 한다.

| Manual ID | 화면/기능 | 확인 절차 | Expected Result | 기록물 |
| --- | --- | --- | --- | --- |
| MV-001 | 업로드 화면 | 랜딩 → 파일 선택 → 업로드 버튼 클릭까지 action 수 계산 | 3 actions 이하 | 화면 녹화 또는 체크리스트 |
| MV-002 | 업로드 응답 | 정상 이미지 업로드 후 응답 표시 확인 | `upload_job_id`, `capture_id`, status 표시 | 스크린샷 |
| MV-003 | 오류 메시지 | `.pdf`, 10MB 초과 이미지 업로드 | 사용자가 이해 가능한 거부 메시지 표시 | 스크린샷 |
| MV-004 | 처리 로그 | 라이브 업로드 1장 실행 | 9개 workflow 단계와 완료 시각 표시 | 스크린샷 |
| MV-005 | 3개 데모 질문 버튼 | 각 버튼 클릭 | 문구가 그대로 raw_query로 전달되고 결과 카드 표시 | 스크린샷/녹화 |
| MV-006 | 과제 결과 카드 | 과제 질문 결과 확인 | 과목명, D-day/deadline, 제출물, 근거, 원본 링크 표시 | 스크린샷 |
| MV-007 | 영수증 결과 카드 | 영수증 질문 결과 확인 | 2만 원 초과 금액, 상호명, 결제일, 근거, 원본 링크 표시 | 스크린샷 |
| MV-008 | 장학금 결과 카드 | 장학금 질문 결과 확인 | 신청 기간, 기관명, 제출물, 근거 표시 | 스크린샷 |
| MV-009 | 근거 문장 하이라이트 | 카드에서 원문 보기 열기 | evidence_text와 동일 문장 하이라이트 | 스크린샷 |
| MV-010 | 원본 캡처 | “원본 보기” 클릭 | 2초 이내 뷰어 표시, 이미지 깨짐 없음 | 스크린샷 |
| MV-011 | no-answer | 관련 없는 질문 입력 | 허위 답변 없음, no-answer 메시지와 조건 완화 옵션 표시 | 스크린샷 |
| MV-012 | needs_review | 낮은 confidence 샘플 검색 | 확인 필요 badge 표시, 결과 숨김 없음 | 스크린샷 |
| MV-013 | fallback 후보 | “찾는 캡처가 없음” 클릭 | 4~10위 후보 중 evidence 있는 후보 표시 | 스크린샷 |
| MV-014 | correction 저장 | fallback 후보 선택 후 저장 | correction saved 메시지 또는 `correction_id` 표시 | 스크린샷 |
| MV-015 | MVP 제외 범위 | UI/Network/문서 확인 | 자동 동기화, 캘린더 실연동, 메신저 adapter, 자유형 챗봇 없음 | 체크리스트 |

## 6. Browser Storage Verification Plan

브라우저 저장소 확인은 Chrome DevTools 기준으로 수행한다. Edge/Safari는 동일 항목을 가능한 범위에서 smoke로 확인한다.

### 6.1 확인 대상

| Storage Area | Expected State | Must Not Contain |
| --- | --- | --- |
| IndexedDB `odiduji_client_store.query_history` | 최근 질의 최대 5건 이상, `raw_query`, `query_id`, `created_at` | Upstage API Key, 이름·학번·카드번호 원문 |
| IndexedDB `odiduji_client_store.result_cache` | 최근 질의 결과 카드 캐시, `query_id`, `risk_cards`, `cached_at` | 원본 이미지 binary, API Key, 원본 개인정보 원문 |
| IndexedDB `odiduji_client_store.ui_state` | 마지막 선택 카드, 펼침/접힘 상태, active tab 등 UI 상태 | source of truth 역할을 하는 전체 metadata index |
| IndexedDB `odiduji_client_store.notification_preferences` | MVP에서는 비활성 또는 placeholder 설정값 | 실제 예약 알림 job, 메신저 channel adapter 설정 |
| Local Storage | 비어 있거나 비민감 UI 설정만 존재 | API Key, PII, 원본 캡처 경로 외부 공개 URL |
| Session Storage | 비어 있거나 세션 UI 상태만 존재 | API Key, PII |
| Cookies | 인증 기능이 없으므로 불필요한 쿠키 없음 | API Key, PII |

### 6.2 IndexedDB 수동 확인 절차

1. Chrome에서 데모 앱을 연다.
2. DevTools를 연다. `F12` 또는 `Cmd/Ctrl + Option/Shift + I`.
3. **Application → Storage → IndexedDB**로 이동한다.
4. `odiduji_client_store` 데이터베이스가 생성되어 있는지 확인한다.
5. `query_history`, `result_cache`, `ui_state`, `notification_preferences` object store가 존재하는지 확인한다.
6. 3개 데모 질문 중 1개를 실행한다.
7. `query_history` store를 새로고침하고 `raw_query`, `query_id`, `created_at`이 저장되었는지 확인한다.
8. `result_cache` store를 확인하고 결과 카드 캐시가 저장되었는지 확인한다.
9. 페이지를 새로고침한다.
10. 최근 질의가 0.5초 P95 이내 복원되는지 확인한다.
11. 모든 IndexedDB object store에서 `upstage`, `api_key`, `Authorization`, `Bearer`, 이름, 학번, 카드번호 원문이 없는지 검색한다.
12. Local Storage, Session Storage, Cookies도 동일하게 민감 정보가 없는지 확인한다.

### 6.3 Console 확인 스니펫

아래 스니펫은 QA 편의를 위한 수동 확인 보조 도구다. 제품 코드에 포함하지 않는다.

```javascript
// IndexedDB database existence check
indexedDB.databases().then(dbs => console.table(dbs));
```

```javascript
// Basic object store read helper
const DB_NAME = 'odiduji_client_store';
const stores = ['query_history', 'result_cache', 'ui_state', 'notification_preferences'];

function readAllFromStore(storeName) {
  return new Promise((resolve, reject) => {
    const openReq = indexedDB.open(DB_NAME);
    openReq.onerror = () => reject(openReq.error);
    openReq.onsuccess = () => {
      const db = openReq.result;
      const tx = db.transaction(storeName, 'readonly');
      const store = tx.objectStore(storeName);
      const getReq = store.getAll();
      getReq.onerror = () => reject(getReq.error);
      getReq.onsuccess = () => resolve(getReq.result);
    };
  });
}

Promise.all(stores.map(async store => ({ store, rows: await readAllFromStore(store) })))
  .then(result => console.log(JSON.stringify(result, null, 2)));
```

```javascript
// Sensitive keyword scan across web storage. IndexedDB scan은 위 read helper 결과를 별도 검색한다.
const sensitivePatterns = [/upstage/i, /api[_-]?key/i, /authorization/i, /bearer/i, /card/i, /student/i, /학번/i, /카드번호/i];
const webStorageDump = {
  localStorage: { ...localStorage },
  sessionStorage: { ...sessionStorage },
  cookies: document.cookie
};
const dumpText = JSON.stringify(webStorageDump);
console.table(sensitivePatterns.map(pattern => ({ pattern: pattern.toString(), matched: pattern.test(dumpText) })));
```

### 6.4 Browser Storage Test Cases

| Test ID | 검증 항목 | 절차 | Expected Result | Evidence |
| --- | --- | --- | --- | --- |
| TC-BS-001 | IndexedDB DB 생성 | 앱 실행 후 DevTools Application 탭 확인 | `odiduji_client_store` 존재 | screenshot |
| TC-BS-002 | query_history 저장 | 데모 질문 1회 실행 후 store 확인 | `raw_query`, `query_id`, `created_at` 저장 | screenshot/console output |
| TC-BS-003 | result_cache 저장 | 결과 카드 표시 후 store 확인 | `risk_cards`, `cached_at` 저장 | screenshot/console output |
| TC-BS-004 | ui_state 저장 | 카드 펼침/원본 뷰어 등 UI 조작 후 store 확인 | UI 상태 record 저장 | screenshot/console output |
| TC-BS-005 | 새로고침 복원 | 새로고침 후 최근 질의 목록 확인 | 최근 질의 5건 복원율 100% | 화면 녹화 |
| TC-BS-006 | API Key 미저장 | IndexedDB/Local Storage/Session Storage/Cookies 검색 | API Key 노출 0건 | scan output |
| TC-BS-007 | PII 원문 미저장 | IndexedDB/Local Storage/Session Storage/Cookies 검색 | 이름·학번·카드번호 원문 0건 | scan output |
| TC-BS-008 | source of truth 아님 | IndexedDB 캐시 삭제 후 동일 질의 재실행 | Local JSON DB 기준으로 결과 재조회 | UI result, n8n log |
| TC-BS-009 | 알림 설정 placeholder | `notification_preferences` 확인 | 실제 예약 알림 job 없음, 설정 초안만 존재 | screenshot |
| TC-BS-010 | 메신저 adapter 미존재 | storage key/value 검색 | messenger/channel adapter 관련 값 0건 | scan output |

## 7. Local JSON DB 및 n8n 검증

| Test ID | 검증 항목 | 절차 | Expected Result | Evidence |
| --- | --- | --- | --- | --- |
| TC-LD-001 | capture_records 생성 | 정상 업로드 또는 batch indexing 후 확인 | `/data/capture_records.json`에 `capture_id`, `source_image_path`, `file_hash`, `status`, `created_at` 저장 | file inspection |
| TC-LD-002 | metadata_index 생성 | Extract 완료 후 확인 | `/data/metadata_index.json`에 `doc_type`, normalized fields, confidence, needs_review 저장 | file inspection |
| TC-LD-003 | cache_entries 생성 | 인덱싱 완료 후 확인 | `/data/cache_entries.json`에 file hash별 cached parse/classify/extract 저장 | file inspection |
| TC-LD-004 | test_report 생성 | QA report webhook 실행 | `/data/test_report.json` 생성, 9개 지표 포함 | file inspection |
| TC-LD-005 | correction_log 생성 | fallback 후보 선택 후 저장 | `/data/correction_log.json` 생성, PII 원문 없음 | file inspection |
| TC-LD-006 | notification_plan 생성 | 확장 계획 파일 확인 | `/data/notification_plan.json`에 permission flow와 스케줄 규칙 포함 | file inspection |
| TC-LD-007 | n8n Webhook contract | 각 Webhook request/response schema 검증 | schema validation pass 100% | contract test report |
| TC-LD-008 | Frontend Backend 미호출 | Network tab 확인 | `/api/*` Backend 호출 0건, n8n Webhook만 호출 | Network screenshot |

## 8. 수동 확인 + 브라우저 저장소 확인 통합 시나리오

아래 시나리오는 데모 전 최종 리허설에서 1회 이상 실행한다.

| Scenario ID | 절차 | Pass Criteria |
| --- | --- | --- |
| E2E-001 | 브라우저 저장소 초기화 → 앱 실행 → 데모 질문 `이번 주 마감 과제 공지` 클릭 → 결과 카드 수동 확인 → DevTools에서 IndexedDB 확인 → 새로고침 | 과제 카드 표시, 근거 하이라이트, 원본 보기 성공, `query_history` 저장, 새로고침 후 최근 질의 복원 |
| E2E-002 | 데모 질문 `2만 원 넘는 영수증` 클릭 → 금액 카드 수동 확인 → `result_cache` 확인 → 민감정보 scan | 20,000원 초과 영수증 표시, 원본 캡처 표시, API Key/PII 저장 0건 |
| E2E-003 | 데모 질문 `장학금 신청 기간` 클릭 → 제출물/evidence 확인 → evidence 없는 필드 처리 확인 | 신청 기간/기관/제출물 표시, 근거 없는 필드는 no-answer 또는 부분 답변 |
| E2E-004 | 관련 없는 질문 입력 → no-answer UI 수동 확인 → 조건 완화 클릭 → IndexedDB 저장 확인 | 허위 답변 0건, 조건 완화 옵션 1~3개 표시, query_history 기록 |
| E2E-005 | 라이브 업로드 1장 실행 → n8n 처리 로그 수동 확인 → 원본 캡처 저장 경로 확인 → IndexedDB/Local JSON DB 비교 | 9단계 로그 표시, source_image_path 생성, IndexedDB는 캐시로만 동작 |
| E2E-006 | API failure mock → 동일 이미지 재질의 → cache fallback UI/log 확인 | `cache_hit=true`, 결과 카드 표시, failure 상태 사용자 메시지 표시 |

## 9. Defect Severity 기준

| Severity | 기준 | 예시 | Release Impact |
| --- | --- | --- | --- |
| S0 Blocker | 데모 핵심 가치 또는 보안 원칙 위반 | 3개 대표 질문 중 1개 실패, API Key 노출, 환각 답변 발생, 30장 인덱싱 실패 | 릴리즈 불가 |
| S1 Critical | P0 기능 일부 실패이나 workaround 존재 | 원본 보기 2초 초과, no-answer 옵션 누락, IndexedDB 복원 실패 | 릴리즈 전 수정 필요 |
| S2 Major | P1 기능 실패 또는 사용자 경험 저하 | 처리 로그 일부 누락, fallback 후보 UI 깨짐 | Known Issue 허용 가능. 데모 script에 반영 |
| S3 Minor | 시각적 결함 또는 문구 개선 | badge 색상/간격 오류, error copy 어색함 | 릴리즈 가능. 후속 수정 |

## 10. 최종 Sign-off Checklist

| Checklist ID | 항목 | Owner | Status |
| --- | --- | --- | --- |
| SO-001 | 30장 golden dataset 준비 및 PII 마스킹 완료 | Data / QA | TBD |
| SO-002 | 일괄 인덱싱 `indexed_count=30` 확인 | Workflow / QA | TBD |
| SO-003 | 3개 대표 데모 질문 3/3 성공 | PM / QA | TBD |
| SO-004 | `/data/test_report.json` 9개 지표 포함 및 목표값 충족 | QA | TBD |
| SO-005 | no-answer 5개 질문 정확도 100%, 환각 답변률 0% | QA / AI | TBD |
| SO-006 | 수동 확인 체크리스트 MV-001~MV-015 완료 | QA | TBD |
| SO-007 | 브라우저 저장소 확인 TC-BS-001~TC-BS-010 완료 | Frontend / QA | TBD |
| SO-008 | Frontend/IndexedDB API Key 노출 0건 | Workflow / QA | TBD |
| SO-009 | Local JSON DB backup 생성률 100% 확인 | Workflow | TBD |
| SO-010 | n8n Webhook contract 및 Network tab에서 Backend 호출 0건 확인 | Frontend / Workflow | TBD |
| SO-011 | 캐시 fallback 리허설 완료 | Workflow / 발표 | TBD |
| SO-012 | MVP Out of Scope 항목 구현 없음 확인 | PM | TBD |

## 11. Traceability Matrix

| AC/Test Area | PRD User Story | SRS Requirement ID | 주요 Evidence |
| --- | --- | --- | --- |
| 업로드 및 검증 | US-001 | FR-001~005, IR-UI-001~003, IR-N8N-001 | UI, Network, n8n log |
| Golden dataset 인덱싱 | US-002 | FR-006~013, FR-024, FR-033 | Local JSON DB, indexing_summary |
| 문서형 데이터 구조화 | US-003 | FR-006~012, FR-019~021 | metadata_index, Risk Card UI |
| 과제 데모 질의 | US-004 | FR-014~018, FR-022 | query response, UI |
| 영수증 데모 질의 | US-005 | FR-011, FR-014~019, FR-021~022 | query response, UI |
| 장학금 데모 질의 | US-006 | FR-010, FR-014~020, FR-022 | query response, UI |
| no-answer/조건 완화 | US-007 | FR-018, FR-025, IR-UI-008 | response JSON, UI |
| IndexedDB cache | US-008 | FR-034, IR-UI-004, DR-011 | DevTools IndexedDB inspection |
| QA 리포트 | US-009 | FR-031, NFR-QLT-001~011 | test_report.json |
| 처리 로그 | US-010 | FR-023, IR-N8N-002 | UI, n8n execution log |
| 모호 분류 | US-011 | FR-026~028, IR-UI-007 | UI, response JSON |
| Top-3 fallback/correction | US-012 | FR-029~030, DR-009 | UI, correction_log.json |
| 브라우저 알림 계획 | US-013 | FR-032, NFR-SCL-003, IR-EXT-007 | notification_plan.json |
