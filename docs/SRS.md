# OdidujI — 어디두지 SRS v1.2 Full Version

**학생용 캡처 정보 검색함 요구사항 명세서**

---

## 0. 개정 이력

| Ver |       Date | Author           | 변경 요약                                                                                                                                                                                                                  |
| --- | ---------: | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.0 | 2026-05-22 | AI 시스템 분석가 | `LOCOMOCO_기획서_v4`와 리뷰어 피드백을 통합하여 ISO/IEC/IEEE 29148 기준 SRS 초안 작성                                                                                                                                      |
| 1.1 | 2026-05-22 | AI 시스템 분석가 | Frontend를 HTML/CSS/JavaScript + Tailwind CSS로 확정, Backend 제거, IndexedDB + n8n 로컬 디스크 + Local JSON DB 구조로 변경, 모호분류 샘플·threshold sweep 보류, 메신저 channel adapter 제거, 브라우저 알림 확장 계획 추가 |
| 1.2 | 2026-05-23 | AI 시스템 분석가 | PRD 최신 결정 반영: Frontend HTML/CSS/JavaScript only, Backend n8n 자체 기능, SQLite 저장소, golden dataset 81장/모호분류 3장, n8n Trigger Webhook 2개로 확정 |

---

## 1. 개요

### 1.1 목적

본 문서는 **OdidujI — 어디두지** 서비스의 MVP 개발을 위한 요구사항 명세서이다. OdidujI는 대학생이 캡처해 둔 과제 공지, 영수증, 장학금, 학사·행정 공지 정보를 다시 찾지 못해 발생하는 **마감·금액·제출물 손실**을 줄이기 위한 **학생용 캡처 정보 검색함**이다.

OdidujI는 캡처 이미지를 단순 OCR 텍스트가 아니라 문서형 데이터로 구조화하고, 사용자가 손해 보기 쉬운 정보를 **원본 캡처 + 근거 문장 + 결과 카드** 형태로 회수한다. 기획서 v4는 Upstage Document Parse, Document Classify, Information Extract, Solar LLM을 단계별로 사용하는 Upstage-first 구조를 제시한다.

### 1.2 범위

#### 1.2.1 MVP 포함 범위

| 구분          | 포함 내용                                                                                                                            |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| 데모 데이터   | 캡처 81장 고정 사전 인덱싱                                                                                                           |
| 라이브 데모   | 발표 중 캡처 1장 수동 업로드                                                                                                         |
| 데모 질문     | `이번 주 마감 과제 공지`, `2만 원 넘는 영수증`, `장학금 신청 기간`                                                                   |
| AI 파이프라인 | Upstage Document Parse → Document Classify → Schema Router → Information Extract → Solar Query Planner → Solar Evidence-bound Answer |
| UI            | HTML/CSS/JavaScript 기반 업로드 화면, 인덱싱 상태, 결과 카드, 원본 캡처, 근거 문장 하이라이트                                        |
| Workflow      | n8n Trigger Webhook 2개, validation, JPG/PNG 저장, Upstage API 호출, no-answer 처리, SQLite 저장                                     |
| 저장소        | SQLite, n8n 로컬 디스크                                                                                                              |
| 안전장치      | confidence 0.70 기준, needs_review, no-answer, evidence-bound answer, cache fallback                                                 |
| QA            | golden_dataset.json, test_report.json, Top-3 정답 포함률, 필드별 추출 정확도, no-answer 정확도, 환각 답변률                          |

#### 1.2.2 MVP 제외 범위

| 제외 항목                                 | 처리                 |
| ----------------------------------------- | -------------------- |
| 사진첩 자동 동기화                        | 제외                 |
| 캘린더 실연동                             | 제외                 |
| 메신저 channel adapter                    | 제외                 |
| 카카오톡/텔레그램 봇 연동                 | 제외                 |
| 수천 장 이상 장기 인덱싱                  | 제외                 |
| 자동 폴더 생성                            | 제외                 |
| 자유형 챗봇                               | 제외                 |
| 별도 Backend 서버                         | 제외                 |
| React / Next.js                           | 제외                 |
| FastAPI / Node.js                         | 제외                 |
| Local JSON DB primary storage             | 제외                 |
| 실제 브라우저 예약 알림 구현              | 제외                 |

리뷰어 피드백은 업로드 마찰, no-answer 사용성, 분류 모호성, Top-3 실패 보조 흐름을 주요 보완점으로 지적했다. 최신 PRD 결정에 따라 외부 메신저 채널은 실제 연동하지 않고 이미지업로드 웹훅 payload contract 확장 가능성만 남긴다.

### 1.3 용어 정의

| 용어                     | 정의                                                                                       |
| ------------------------ | ------------------------------------------------------------------------------------------ |
| Capture                  | 사용자가 업로드하거나 사전 등록한 JPG/PNG 캡처 이미지                                      |
| capture_id               | 각 캡처에 부여되는 고유 식별자. 예: `CAP-001`                                              |
| doc_type                 | 캡처 유형. `assignment`, `notice`, `scholarship`, `receipt`, `place_link`, `noise` 중 하나 |
| Schema Router            | `doc_type`에 따라 Information Extract용 JSON Schema를 선택하는 라우팅 컴포넌트             |
| evidence_text            | 추출 필드의 근거가 되는 원문 문장                                                          |
| confidence               | Parse, Classify, Extract 단계별 신뢰도. 0.00~1.00 범위                                     |
| needs_review             | confidence 또는 추출 충돌 기준에 따라 사용자 확인이 필요한 상태                            |
| no-answer                | 근거 문장이 없거나 필수 필드가 없을 때 답변을 생성하지 않는 상태                           |
| Risk Card                | 마감, 금액, 제출물, 기관명, D-day, evidence_text, 원본 캡처를 표시하는 결과 카드           |
| Golden Dataset           | 데모 및 QA용 81장 캡처와 정답 메타데이터                                                   |
| Top-3 정답 포함률        | 질의 결과 상위 3개 후보 안에 정답 캡처가 포함되는 비율                                     |
| Evidence-bound Answer    | 후보 카드와 근거 문장 안에서만 생성되는 제한형 답변                                        |
| SQLite                   | n8n Workflow가 capture, metadata index, cache, QA result, correction log를 저장하는 primary storage |
| n8n Trigger Webhook      | Frontend가 호출하는 n8n 진입점. MVP에서는 이미지업로드 웹훅과 질문 전송 웹훅 2개만 사용    |

### 1.4 참조 문서

| 문서                             | 내용                                                                                        | 참조                     |
| -------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------ |
| LOCOMOCO\_기획서\_v4.pdf         | 제품 정의, 서비스 개요, 구현 계획, 데이터셋, QA 지표, 리스크 대응                           |                          |
| 03*LOCOMOCO*어디두지\_피드백.pdf | 강점, 우려사항, 피벗·확장 방향, 다음 단계 제안                                              |                          |
| 사용자 v1.2 수정 피드백          | Frontend HTML/CSS/JavaScript only, Backend n8n 자체 기능, SQLite, golden dataset 81장/모호분류 3장, Trigger Webhook 2개 확정 | 본 대화 내 사용자 피드백 |

---

## 2. 피드백 반영 요약 (Feedback Integration Summary)

### 2.0 피드백 분해

#### 2.0.1 리뷰어 피드백 분해

| ID   | 원문 인용                                                                      | 분류 | 핵심 의도                                         | 적용 우선순위 |
| ---- | ------------------------------------------------------------------------------ | ---- | ------------------------------------------------- | ------------- |
| S-01 | “‘대학생의 캡처 디지털 호딩’이라는 문제 정의에서 출발”                         | 강점 | 문제 정의를 대학생 캡처 회수 실패로 고정          | M             |
| S-02 | “Document Parse → Classify → Information Extract → Solar의 역할 분담”          | 강점 | Upstage-first 파이프라인 유지                     | M             |
| S-03 | “no-answer/confidence 0.7 컷오프, 정량 검증, 에러 상태 8종 정의”               | 강점 | 안전장치와 QA를 제품 구조에 내재화                | M             |
| S-04 | “안전장치와 단계적 스코핑이 가장 잘 짜여 있는 제안”                            | 강점 | Core 1개 + Nice-to-have 2개 스코프 유지           | M             |
| S-05 | “스키마 라우팅이라는 설계 원칙”                                                | 강점 | Classify 결과가 Extract Schema를 결정하도록 유지  | M             |
| S-06 | “캡처 유형을 먼저 분류하고, 유형별 추출 스키마를 적용”                         | 강점 | `doc_type → schema_json` 라우팅 명세화            | M             |
| S-07 | “Solar는 query planner와 evidence-bound answer로 제한”                         | 강점 | 자유 생성 차단 및 근거 기반 답변 유지             | M             |
| S-08 | “hallucination 가능성을 사전에 차단”                                           | 강점 | no-answer와 evidence_text 필수화                  | M             |
| S-09 | “손실 방지 시나리오 3개”                                                       | 강점 | 3개 데모 질문 유지                                | M             |
| S-10 | “81장 골든 데이터셋과 Top-3 정답 포함률·no-answer 정확도”                      | 강점 | QA 지표를 수용 기준으로 승격                      | M             |
| S-11 | “한국 대학생 캡처 속 마감·돈·제출 손실을 구조화”                               | 강점 | 도메인 특화 필드 유지                             | M             |
| S-12 | “Pixel Screenshots/Recall/Live Text와의 비교도 도메인 특화 측면에서 잘 갈라짐” | 강점 | 범용 사진 검색이 아닌 손실 방지 카드 구조 유지    | S             |
| S-13 | “Classify_Ambiguous 상태에서 confidence 0.7 미만일 때 후보 유형 선택”          | 강점 | 능동적 분류 보완 UI 유지                          | S             |
| W-01 | “‘이미지를 업로드해야 한다’라는 입력 흐름이 본 서비스의 가장 큰 마찰”          | 약점 | 업로드 단계를 최소 상호작용으로 축소              | M             |
| W-02 | “‘저장 직후 자동 인덱싱’이 이상적”                                             | 약점 | 자동 인덱싱은 제외하되 입력 payload contract 확장 가능성 관리 | C             |
| W-03 | “메신저 채널 인덱싱”                                                           | 약점 | 실제 봇은 제외하고 이미지업로드 웹훅 payload 확장으로만 정의   | C             |
| W-04 | “답을 못 주는 경우가 잦은 도구로 느껴질 가능성”                                | 약점 | no-answer 시 조건 완화와 원본 확인 제공           | M             |
| W-05 | “답변 회수율과 confidence 임계치 사이의 균형”                                  | 약점 | 0.6/0.7/0.8 threshold sweep으로 trade-off 측정    | M             |
| W-06 | “6개 라벨이 실제 캡처에서 경계가 모호한 케이스”                                | 약점 | runtime Classify_Ambiguous 처리 유지              | S             |
| W-07 | “능동 분류 보완 단계가 골든 데이터셋의 어떤 비율에서 작동하는지”               | 약점 | golden dataset 81장 중 모호분류 3장으로 측정      | M             |
| W-08 | “Top-3 정답 포함률 90% 이상은 강한 약속”                                       | 약점 | 4~10위 fallback 후보와 correction_log 추가        | S             |
| W-09 | “사용자가 직접 수정해 데이터로 환류”                                           | 약점 | correction_log 저장                               | S             |
| N-01 | “손실 방지 시나리오 3개를 골든 데이터셋 위에서 끝까지”                         | 중립 | 현재 MVP 초점 유지                                | M             |
| N-02 | “사진첩 자동 동기화/캘린더 실연동 중 하나”                                     | 중립 | MVP 제외 유지                                     | W             |
| N-03 | “분류가 흔들리는 케이스 측정”                                                  | 중립 | 모호분류 3장과 ambiguous_activation_rate로 측정   | M             |

#### 2.0.2 v1.2 사용자 피드백 분해

| ID    | 원문 인용                                                                                          | 분류      | 핵심 의도                                           | 적용 우선순위 |
| ----- | -------------------------------------------------------------------------------------------------- | --------- | --------------------------------------------------- | ------------- |
| UF-01 | “Frontend는 html, css, javascript로만 만들어줘.”                                                   | 기술 결정 | React/Next.js/Tailwind 없이 정적 웹 UI로 확정        | M             |
| UF-02 | “Backend는 n8n 자체 기능만 쓸거야.”                                                                | 기술 결정 | 별도 FastAPI/Node.js Backend 제거, n8n Workflow 확정 | M             |
| UF-03 | “저장소로는 SQLite를 쓴다.”                                                                        | 기술 결정 | SQLite primary storage 확정                         | M             |
| UF-04 | “golden dataset는 81장이고 모호분류는 3장이야.”                                                    | QA 결정   | golden dataset 81장, 모호분류 샘플 3장 확정          | M             |
| UF-05 | “트리거 노드 웹훅은 이미지업로드 웹훅, 질문 전송 웹훅 총 2개만 사용할거야.”                         | 인터페이스 결정 | n8n Trigger Webhook 2개로 제한                  | M             |

---

### 2.1 보존된 강점

| 강점 ID | 내용                                               | 반영 요구사항 ID                                | 강화 방식                                                                  |
| ------- | -------------------------------------------------- | ----------------------------------------------- | -------------------------------------------------------------------------- |
| S-01    | 대학생 캡처 디지털 호딩 문제 정의                  | FR-021, FR-022, DR-001, NFR-QLT-001             | 3개 손실 방지 질문과 결과 카드 구조를 MVP 핵심 성공 기준으로 고정          |
| S-02    | Upstage 단계별 역할 분담                           | FR-006, FR-007, FR-008, FR-009, IR-EXT-001~005  | API별 입력·처리·출력 스키마를 인터페이스 요구사항으로 분리                 |
| S-03    | no-answer/confidence/정량 검증/에러 상태           | FR-012, FR-018, FR-024, FR-031, NFR-QLT-006~009 | 안전장치를 UI와 QA 리포트 수용 기준에 반영                                 |
| S-04    | 안전장치와 단계적 스코핑                           | FR-023, FR-024, NFR-AVL-002, NFR-AVL-003, §7    | 캐시 fallback, 제외 범위, MVP 경계를 명시                                  |
| S-05    | 스키마 라우팅 설계 원칙                            | FR-008, DR-003, DR-004, IR-EXT-003              | `doc_type → extract_schema_id → schema_json`을 필수 데이터 흐름으로 지정   |
| S-06    | 유형별 추출 스키마 적용                            | FR-008, FR-009, DR-004                          | 각 doc_type별 필수·선택 필드와 confidence 저장 요구                        |
| S-07    | Solar를 query planner/evidence-bound answer로 제한 | FR-014, FR-017, FR-018, IR-EXT-004, IR-EXT-005  | `allow_free_generation=false`와 `require_evidence_text=true`를 처리 규칙화 |
| S-08    | 환각 차단                                          | FR-018, NFR-QLT-008                             | 근거 없는 필드 답변률 0%를 정량 목표로 지정                                |
| S-09    | 과제·영수증·장학금 3개 손실 시나리오               | FR-022, NFR-QLT-001                             | 3개 데모 질문 성공률 3/3을 수용 기준화                                     |
| S-10    | 81장 golden dataset과 Top-3/no-answer 지표         | FR-030, FR-031, DR-008, NFR-QLT-001~010         | QA 리포트 산출물을 필수 산출물로 지정                                      |
| S-11    | 한국 대학생 도메인 특화 포지셔닝                   | FR-007, FR-009, FR-019, DR-004                  | deadline, amount, required_submission, institution을 핵심 필드로 고정      |
| S-12    | 범용 사진 검색과 차별화                            | FR-019, FR-020, FR-021                          | 위치·날짜 중심이 아니라 근거 문장과 손실 위험 카드 중심 UI로 구현          |
| S-13    | Classify_Ambiguous 후보 유형 선택                  | FR-026, FR-027, FR-028, NFR-QLT-010             | ambiguity 판정 기준과 모호분류 3장 검증을 명세화                           |

---

### 2.2 보완된 약점

| 약점 ID | 원인 분석                                        | 개선 방향                                                         | 신규/수정 요구사항 ID                  |
| ------- | ------------------------------------------------ | ----------------------------------------------------------------- | -------------------------------------- |
| W-01    | 매번 이미지 업로드가 필요하면 사용 빈도가 낮아짐 | HTML 업로드를 3 actions 이하로 제한하고 n8n Webhook으로 직접 전송 | FR-001, FR-002, FR-003, NFR-USA-001    |
| W-02    | 저장 직후 자동 인덱싱 부재                       | MVP 제외 범위를 유지하되 이미지업로드 웹훅 payload 확장 가능성 정의 | FR-032, NFR-SCL-003                    |
| W-03    | 메신저 채널 확장 제안                            | 실제 봇 구현은 제외하고 이미지업로드 웹훅 확장용 payload contract만 정의 | FR-032, IR-EXT-007                     |
| W-04    | no-answer 과다 시 사용성 저하                    | no-answer 시 조건 완화 옵션과 원본 확인 제공                      | FR-018, FR-025, IR-UI-006              |
| W-05    | confidence 0.70 기준의 회수율 trade-off          | 0.6/0.7/0.8 threshold sweep 결과를 QA 리포트에 포함               | FR-012, FR-031, NFR-QLT-009            |
| W-06    | doc_type 경계 모호                               | Classify_Ambiguous runtime 판정과 후보 유형 선택 유지             | FR-026, FR-027, FR-028                 |
| W-07    | ambiguity 측정 미정                              | golden dataset 81장 전체 denominator와 모호분류 3장 결과를 보고   | FR-031, NFR-QLT-010                    |
| W-08    | Top-3 실패 시 사용자 흐름 단절                   | 4~10위 fallback 후보 표시                                         | FR-029                                 |
| W-09    | 사용자 수정이 모델·데이터 개선으로 환류되지 않음 | correction_log 저장                                               | FR-030                                 |
| UF-01   | Frontend 기술 선택 미정                          | HTML/CSS/JavaScript only 확정                                      | IR-UI-001~003, CON-011                 |
| UF-02   | Backend 필요성 제거                              | n8n 자체 Workflow와 2개 Trigger Webhook 구조로 전환               | FR-001, FR-013, IR-N8N-001~002, CON-013 |
| UF-03   | DB 선택 미정                                     | SQLite primary storage 확정                                       | FR-013, DR-012, CON-015                |
| UF-04   | 모호분류 샘플 수 미정                            | golden dataset 81장 중 모호분류 3장 확정                          | FR-031, FR-033, NFR-QLT-010            |
| UF-05   | n8n Webhook 수 미정                              | 이미지업로드 웹훅과 질문 전송 웹훅 총 2개로 제한                  | IR-N8N-001~002, CON-014                |

---

### 2.3 v1.2 확정 아키텍처 요약

```text
[HTML/CSS/JavaScript UI]
        ↓
[n8n Trigger Webhook 2개]
- 이미지업로드 웹훅: /webhook/image-upload
- 질문 전송 웹훅: /webhook/question-submit
        ↓
[n8n Workflow]
- validation
- JPG/PNG validation
- Upstage Document Parse
- Upstage Document Classify
- Schema Router
- Upstage Information Extract
- Solar Query Planner
- Solar Evidence-bound Answer
        ↓
[SQLite + n8n Local Disk]
- /static/captures/*
- capture_records
- metadata_index
- cache_entries
- golden_dataset
- test_report
- correction_log
```

---

## 3. 기능 요구사항 (FR)

### FR-001: 캡처 업로드 요청 수신

- 설명: 시스템은 사용자가 HTML 업로드 폼에서 캡처 이미지를 선택하면 이미지업로드 웹훅으로 업로드 요청을 전송해야 한다.
- 입력/출력:
  - 입력: `multipart/form-data.image`
  - 출력: `upload_job_id`, `capture_id`, `status=received`

- 처리 규칙:
  - 업로드 요청 1건은 이미지 1장만 포함한다.
  - Frontend는 별도 Backend API를 호출하지 않는다.
  - Frontend는 이미지업로드 웹훅(`/webhook/image-upload`)과 질문 전송 웹훅(`/webhook/question-submit`)만 호출한다.
  - Upstage API Key는 Frontend JavaScript에 포함되면 안 된다.

- 우선순위: M
- 수용 기준:
  - Given 사용자가 HTML 업로드 폼에서 JPG/PNG 이미지 1장을 선택한 상태
  - When 사용자가 업로드 버튼을 클릭하면
  - Then Frontend는 이미지업로드 웹훅으로 파일을 전송하고 `upload_job_id`를 1초 이내 화면에 표시한다.

- 출처: 기획서 §2.2, §3.3 / 피드백 #W-01, #UF-01, #UF-02
- 연관 강점/약점: W-01, UF-01, UF-02

### FR-002: 파일 확장자 검증

- 설명: 시스템은 업로드된 파일의 확장자가 JPG 또는 PNG 중 하나인지 검증해야 한다.
- 입력/출력:
  - 입력: `file_name`, `mime_type`
  - 출력: `validation_status`, `reject_reason`

- 처리 규칙:
  - 허용 확장자: `.jpg`, `.jpeg`, `.png`
  - 허용되지 않은 확장자는 `status=rejected`로 처리한다.

- 우선순위: M
- 수용 기준:
  - Given 사용자가 `.pdf` 파일을 업로드한 상태
  - When 파일 검증이 실행되면
  - Then 시스템은 `reject_reason=unsupported_file_type`을 반환한다.

- 출처: 기획서 §2.2 / 피드백 #W-01
- 연관 강점/약점: W-01

### FR-003: 파일 크기 검증

- 설명: 시스템은 업로드 파일 크기가 10MB 이하인지 검증해야 한다.
- 입력/출력:
  - 입력: `file_size_bytes`
  - 출력: `validation_status`, `reject_reason`

- 처리 규칙:
  - `file_size_bytes > 10,485,760`이면 업로드를 거부한다.

- 우선순위: M
- 수용 기준:
  - Given 10MB를 초과하는 이미지가 업로드된 상태
  - When 파일 검증이 실행되면
  - Then 시스템은 `reject_reason=file_too_large`를 반환한다.

- 출처: 기획서 §2.2, §5.1 / 피드백 #W-01
- 연관 강점/약점: W-01

### FR-004: HEIC 파일 거부

- 설명: 시스템은 HEIC 파일을 업로드 대상에서 제외하고 명시적인 거부 사유를 반환해야 한다.
- 입력/출력:
  - 입력: `.heic` 이미지
  - 출력: `validation_status=rejected`, `reject_reason=unsupported_file_type`

- 처리 규칙:
  - HEIC 파일은 JPG로 변환하지 않는다.
  - HEIC 파일은 Upstage 호출 단계로 전달하지 않는다.

- 우선순위: M
- 수용 기준:
  - Given 사용자가 HEIC 캡처를 업로드한 상태
  - When 파일 검증이 실행되면
  - Then 시스템은 `reject_reason=unsupported_file_type`을 반환하고 인덱싱을 시작하지 않는다.

- 출처: 기획서 §2.2, §3.9 / 피드백 #S-04
- 연관 강점/약점: S-04

### FR-005: 원본 캡처 저장

- 설명: 시스템은 검증된 JPG/PNG 캡처 이미지를 n8n 로컬 디스크에 저장해야 한다.
- 입력/출력:
  - 입력: 검증 완료 이미지
  - 출력: `source_image_path`

- 처리 규칙:
  - 저장 경로 형식은 `/static/captures/{capture_id}.{ext}`로 한다.
  - 파일명에는 원본 사용자 파일명을 사용하지 않는다.

- 우선순위: M
- 수용 기준:
  - Given 파일 검증이 완료된 이미지가 있는 상태
  - When 저장 프로세스가 실행되면
  - Then 시스템은 `source_image_path`를 포함한 capture_record를 생성한다.

- 출처: 기획서 §2.1, §3.4 / 피드백 #S-11, #UF-02
- 연관 강점/약점: S-11, UF-02

### FR-006: Document Parse 실행

- 설명: 시스템은 캡처 이미지를 Upstage Document Parse로 파싱해야 한다.
- 입력/출력:
  - 입력: `source_image_path`
  - 출력: `parsed_markdown`, `layout_blocks`, `evidence_candidates`, `parse_confidence`

- 처리 규칙:
  - Parse 결과는 `capture_id`와 연결하여 저장한다.
  - `parse_confidence`는 0.00~1.00 범위의 소수로 저장한다.

- 우선순위: M
- 수용 기준:
  - Given 저장된 캡처 이미지가 있는 상태
  - When Document Parse가 완료되면
  - Then 시스템은 `parsed_markdown`과 `parse_confidence`를 저장한다.

- 출처: 기획서 §3.1~3.3 / 피드백 #S-02
- 연관 강점/약점: S-02

### FR-007: Document Classify 실행

- 설명: 시스템은 파싱 결과를 Upstage Document Classify로 분류해야 한다.
- 입력/출력:
  - 입력: `parsed_markdown`, `file_meta`
  - 출력: `doc_type`, `category_confidence`, `category_candidates`

- 처리 규칙:
  - `doc_type`은 `assignment`, `notice`, `scholarship`, `receipt`, `place_link`, `noise` 중 하나로 저장한다.

- 우선순위: M
- 수용 기준:
  - Given `parsed_markdown`이 저장된 캡처가 있는 상태
  - When Document Classify가 실행되면
  - Then 시스템은 허용된 6개 라벨 중 하나를 `doc_type`으로 저장한다.

- 출처: 기획서 §2.2, §3.2, §3.3 / 피드백 #S-06, #W-06
- 연관 강점/약점: S-06, W-06

### FR-008: 추출 스키마 라우팅

- 설명: 시스템은 `doc_type`에 대응하는 Information Extract 스키마를 선택해야 한다.
- 입력/출력:
  - 입력: `doc_type`
  - 출력: `extract_schema_id`, `schema_json`

- 처리 규칙:
  - 스키마 매핑은 `/data/schema_registry.json`에 정의한다.
  - 등록되지 않은 `doc_type`은 `schema_not_found`로 처리한다.

- 우선순위: M
- 수용 기준:
  - Given `doc_type=receipt`인 캡처가 있는 상태
  - When Schema Router가 실행되면
  - Then 시스템은 영수증 추출용 `schema_json`을 반환한다.

- 출처: 기획서 §3.2~3.3 / 피드백 #S-05, #S-06
- 연관 강점/약점: S-05, S-06

### FR-009: Information Extract 실행

- 설명: 시스템은 선택된 스키마로 Upstage Information Extract를 실행해야 한다.
- 입력/출력:
  - 입력: `parsed_markdown`, `layout_blocks`, `schema_json`
  - 출력: `deadline`, `date_range`, `amount`, `required_submission`, `institution`, `merchant`, `action_items`, `evidence_text`, `extract_confidence`

- 처리 규칙:
  - 추출 필드는 `doc_type`별 스키마에 정의된 필드만 저장한다.
  - 각 추출 필드는 `evidence_text`와 연결되어야 한다.

- 우선순위: M
- 수용 기준:
  - Given `doc_type=assignment`와 과제 스키마가 있는 상태
  - When Information Extract가 실행되면
  - Then 시스템은 `deadline` 또는 `required_submission` 중 추출 가능한 필드와 해당 `evidence_text`를 저장한다.

- 출처: 기획서 §2.2, §3.3 / 피드백 #S-05, #S-11
- 연관 강점/약점: S-05, S-11

### FR-010: 날짜·기간 정규화

- 설명: 시스템은 추출된 날짜·기간을 KST 기준 ISO-8601 형식으로 정규화해야 한다.
- 입력/출력:
  - 입력: `deadline`, `date_range`, `evidence_text`
  - 출력: `normalized_deadline`, `normalized_date_range`

- 처리 규칙:
  - 시간 정보가 없으면 기본 마감 시간은 `23:59:00+09:00`으로 저장한다.
  - 날짜 해석 실패 시 원문 값을 유지하고 `needs_review=true`로 표시한다.

- 우선순위: M
- 수용 기준:
  - Given `evidence_text="5월 20일 23:59까지"`가 있는 상태
  - When 날짜 정규화가 실행되면
  - Then 시스템은 `2026-05-20T23:59:00+09:00` 형식의 값을 저장한다.

- 출처: 기획서 §3.4, §4 / 피드백 #S-09
- 연관 강점/약점: S-09

### FR-011: 금액 정규화

- 설명: 시스템은 추출된 금액을 KRW 정수 값으로 정규화해야 한다.
- 입력/출력:
  - 입력: `amount`, `currency`, `evidence_text`
  - 출력: `normalized_amount`, `currency=KRW`

- 처리 규칙:
  - 쉼표, 원 기호, 공백은 제거하고 정수로 저장한다.
  - 두 개 이상의 금액 후보가 있고 확정할 수 없으면 `amount_conflict=true`를 저장한다.

- 우선순위: M
- 수용 기준:
  - Given `evidence_text="23,500원"`이 있는 상태
  - When 금액 정규화가 실행되면
  - Then 시스템은 `normalized_amount=23500`을 저장한다.

- 출처: 기획서 §2.4, §3.4 / 피드백 #S-09
- 연관 강점/약점: S-09

### FR-012: needs_review 판정

- 설명: 시스템은 confidence 또는 추출 충돌 기준에 따라 `needs_review`를 판정해야 한다.
- 입력/출력:
  - 입력: `parse_confidence`, `category_confidence`, `extract_confidence`, `amount_conflict`, `date_parse_failed`
  - 출력: `needs_review`

- 처리 규칙:
  - `parse_confidence < 0.70`, `category_confidence < 0.70`, `extract_confidence < 0.70` 중 하나라도 참이면 `needs_review=true`로 저장한다.
  - `amount_conflict=true` 또는 `date_parse_failed=true`이면 `needs_review=true`로 저장한다.

- 우선순위: M
- 수용 기준:
  - Given `extract_confidence=0.64`인 캡처가 있는 상태
  - When needs_review 판정이 실행되면
  - Then 시스템은 `needs_review=true`를 저장한다.

- 출처: 기획서 §3.6, §5.1 / 피드백 #S-03, #W-04, #W-05
- 연관 강점/약점: S-03, W-04, W-05

### FR-013: 메타데이터 인덱스 저장

- 설명: 시스템은 추출·정규화 결과를 SQLite에 저장해야 한다.
- 입력/출력:
  - 입력: `capture_record`, `doc_type`, `normalized_deadline`, `normalized_amount`, `confidence`, `needs_review`
  - 출력: `index_record_id`

- 처리 규칙:
  - metadata index는 SQLite `metadata_index` 테이블에 저장한다.
  - capture 원본 정보는 SQLite `capture_records` 테이블에 저장한다.
  - Local JSON DB는 primary storage로 사용하지 않는다.
  - 동일 이미지 해시가 이미 존재하면 새 인덱스 레코드를 생성하지 않는다.
  - 중복 이미지 요청은 기존 `capture_id`를 반환한다.

- 우선순위: M
- 수용 기준:
  - Given n8n workflow가 Information Extract 결과를 생성한 상태
  - When 인덱싱 노드가 실행되면
  - Then SQLite `metadata_index`에 해당 `capture_id`의 metadata record가 추가된다.

- 출처: 기획서 §3.1, §3.4 / 피드백 #S-04, #S-10, #UF-02, #UF-03
- 연관 강점/약점: S-04, S-10, UF-02, UF-03

### FR-014: 자연어 질의 계획 생성

- 설명: 시스템은 사용자 자연어 질문을 Solar LLM Query Planner로 필터 JSON으로 변환해야 한다.
- 입력/출력:
  - 입력: `raw_query`
  - 출력: `query_intent`, `target_doc_type`, `filters`, `sort_rule`, `answer_policy`

- 처리 규칙:
  - Solar LLM은 자유 답변을 생성하지 않고 필터 JSON만 생성한다.
  - `answer_policy.mode=evidence_bound`로 설정한다.

- 우선순위: M
- 수용 기준:
  - Given `raw_query="2만 원 넘는 영수증"`이 입력된 상태
  - When Query Planner가 실행되면
  - Then 시스템은 `target_doc_type=receipt`와 `filters.amount_min=20000`을 반환한다.

- 출처: 기획서 §2.4, §3.5 / 피드백 #S-07
- 연관 강점/약점: S-07

### FR-015: 질의 계획 유효성 검증

- 설명: 시스템은 Query Planner가 생성한 필터 JSON이 허용 스키마를 준수하는지 검증해야 한다.
- 입력/출력:
  - 입력: `query_plan`
  - 출력: `query_plan_valid`, `validation_error`

- 처리 규칙:
  - 허용되지 않은 `doc_type`, `sort_rule`, `filter_key`가 포함되면 질의 실행을 중단한다.
  - 실패 시 `query_plan_invalid` 에러를 반환한다.

- 우선순위: M
- 수용 기준:
  - Given `target_doc_type=free_chat`인 query_plan이 생성된 상태
  - When 유효성 검증이 실행되면
  - Then 시스템은 `query_plan_valid=false`를 반환한다.

- 출처: 기획서 §3.5 / 피드백 #S-07, #S-08
- 연관 강점/약점: S-07, S-08

### FR-016: 후보 Top-3 검색

- 설명: 시스템은 유효한 질의 계획에 따라 SQLite의 metadata index에서 후보 상위 3개를 검색해야 한다.
- 입력/출력:
  - 입력: `query_plan`, SQLite `metadata_index`
  - 출력: `candidate_cards[0..3]`

- 처리 규칙:
  - 후보 정렬은 `sort_rule`을 따른다.
  - 후보 수가 0개이면 `no_candidate=true`를 반환한다.

- 우선순위: M
- 수용 기준:
  - Given `target_doc_type=assignment`, `deadline_range=this_week`, `sort_rule=deadline_asc`인 질의 계획이 있는 상태
  - When 검색이 실행되면
  - Then 시스템은 마감일 오름차순의 후보를 최대 3개 반환한다.

- 출처: 기획서 §2.4, §3.6, §4 / 피드백 #S-09, #S-10, #W-08
- 연관 강점/약점: S-09, S-10, W-08

### FR-017: Evidence-bound 답변 생성

- 설명: 시스템은 후보 카드와 근거 문장 안에서만 답변을 생성해야 한다.
- 입력/출력:
  - 입력: `candidate_cards`, `cited_fields`, `evidence_text`
  - 출력: `answer`, `cards`, `cited_fields`

- 처리 규칙:
  - `allow_free_generation=false`를 적용한다.
  - 답변에 포함되는 모든 필드는 `cited_fields`에 존재해야 한다.

- 우선순위: M
- 수용 기준:
  - Given 후보 카드에 `amount=23500`과 `evidence_text`가 있는 상태
  - When Evidence-bound Answer가 실행되면
  - Then 답변은 `23,500원`을 포함하고 해당 필드를 `cited_fields`에 포함한다.

- 출처: 기획서 §2.5, §3.5 / 피드백 #S-07, #S-08
- 연관 강점/약점: S-07, S-08

### FR-018: 근거 없는 필드 no-answer 처리

- 설명: 시스템은 요청된 필드에 `evidence_text`가 없으면 no-answer를 반환해야 한다.
- 입력/출력:
  - 입력: `requested_fields`, `candidate_cards`
  - 출력: `no_answer`, `no_answer_reason`

- 처리 규칙:
  - `require_evidence_text=true`를 적용한다.
  - 근거 없는 필드는 추론으로 보완하지 않는다.

- 우선순위: M
- 수용 기준:
  - Given 사용자가 “제출 서류 알려줘”라고 질문했고 후보 카드에 `required_submission`의 `evidence_text`가 없는 상태
  - When 답변 생성이 실행되면
  - Then 시스템은 `no_answer=true`와 `no_answer_reason=missing_evidence_text`를 반환한다.

- 출처: 기획서 §2.1, §3.5, §4 / 피드백 #S-08, #W-04
- 연관 강점/약점: S-08, W-04

### FR-019: 손실 위험 결과 카드 렌더링

- 설명: 시스템은 검색 결과를 손실 위험 카드로 표시해야 한다.
- 입력/출력:
  - 입력: `candidate_card`
  - 출력: UI `risk_card`

- 처리 규칙:
  - 카드에는 `title`, `doc_type`, `deadline` 또는 `amount`, `required_submission`, `institution`, `confidence_badge`, `needs_review` 중 존재하는 필드를 표시한다.
  - 존재하지 않는 필드는 빈 문자열로 렌더링하지 않는다.

- 우선순위: M
- 수용 기준:
  - Given 과제 후보 카드가 있는 상태
  - When 결과 화면이 렌더링되면
  - Then 카드에는 과목명, D-day, 제출물, evidence_text, 원본 캡처 링크가 표시된다.

- 출처: 기획서 §2.1~2.4 / 피드백 #S-01, #S-11, #S-12
- 연관 강점/약점: S-01, S-11, S-12

### FR-020: 근거 문장 하이라이트

- 설명: 시스템은 결과 카드의 `evidence_text`를 원문 영역에서 하이라이트해야 한다.
- 입력/출력:
  - 입력: `evidence_text`, `parsed_markdown`
  - 출력: UI highlighted evidence block

- 처리 규칙:
  - 하이라이트 대상 문장이 원문에 없으면 `evidence_highlight_failed=true`를 기록한다.

- 우선순위: M
- 수용 기준:
  - Given `evidence_text="제출 기한: 5월 20일"`이 있는 상태
  - When 결과 카드가 표시되면
  - Then 원문 보기 영역에서 동일 문장이 하이라이트된다.

- 출처: 기획서 §3.9, §4 / 피드백 #S-12
- 연관 강점/약점: S-12

### FR-021: 원본 캡처 표시

- 설명: 시스템은 결과 카드에서 원본 캡처 이미지를 열 수 있어야 한다.
- 입력/출력:
  - 입력: `source_image_path`
  - 출력: 원본 캡처 뷰어

- 처리 규칙:
  - 원본 캡처는 서비스 내 뷰어 패널에서 표시한다.
  - 이미지 로딩 실패 시 `source_image_load_failed`를 반환한다.

- 우선순위: M
- 수용 기준:
  - Given 결과 카드에 `source_image_path`가 있는 상태
  - When 사용자가 “원본 보기”를 클릭하면
  - Then 원본 캡처 뷰어가 2초 이내 표시된다.

- 출처: 기획서 §2.1, §3.9 / 피드백 #S-01, #S-12
- 연관 강점/약점: S-01, S-12

### FR-022: 3개 데모 질문 버튼 제공

- 설명: 시스템은 3개 고정 데모 질문을 버튼으로 제공해야 한다.
- 입력/출력:
  - 입력: 버튼 클릭 이벤트
  - 출력: `raw_query`

- 처리 규칙:
  - 버튼 문구는 `이번 주 마감 과제 공지`, `2만 원 넘는 영수증`, `장학금 신청 기간`으로 고정한다.

- 우선순위: M
- 수용 기준:
  - Given 데모 화면이 열린 상태
  - When 사용자가 `장학금 신청 기간` 버튼을 클릭하면
  - Then 시스템은 동일 문구를 `raw_query`로 질문 전송 웹훅에 전달한다.

- 출처: 기획서 §2.1, §2.4, §3.6 / 피드백 #S-09, #N-01
- 연관 강점/약점: S-09, N-01

### FR-023: n8n 처리 로그 표시

- 설명: 시스템은 발표 중 1장 라이브 업로드의 n8n workflow 처리 단계를 UI에 표시해야 한다.
- 입력/출력:
  - 입력: `upload_job_id`, n8n workflow execution status
  - 출력: `processing_log[]`

- 처리 규칙:
  - 로그 단계는 `received`, `validated`, `normalized`, `parsed`, `classified`, `schema_routed`, `extracted`, `indexed`, `ready`로 제한한다.
  - Frontend는 별도 status Webhook을 호출하지 않고 질문 전송 웹훅의 `action=status` 응답 또는 n8n 내부 상태 결과를 사용한다.

- 우선순위: S
- 수용 기준:
  - Given 라이브 업로드가 시작된 상태
  - When n8n의 Document Parse 노드가 완료되면
  - Then UI는 `parsed` 단계와 완료 시각을 표시한다.

- 출처: 기획서 §3.3, §3.6, §3.9 / 피드백 #S-04, #UF-02
- 연관 강점/약점: S-04, UF-02

### FR-024: API 실패 시 캐시 fallback

- 설명: 시스템은 Upstage API 실패 시 동일 이미지 해시의 캐시 결과를 반환해야 한다.
- 입력/출력:
  - 입력: `file_hash`, API error
  - 출력: cached `capture_record`, `cache_hit=true`

- 처리 규칙:
  - 동일 이미지 해시에 대한 캐시가 없으면 `api_failure_no_cache`를 반환한다.
  - 캐시 결과 사용 여부를 UI 로그에 표시한다.

- 우선순위: M
- 수용 기준:
  - Given 동일 이미지의 캐시가 존재하고 Upstage API가 실패한 상태
  - When 인덱싱을 재시도하면
  - Then 시스템은 캐시 결과와 `cache_hit=true`를 반환한다.

- 출처: 기획서 §3.6, §5.1 / 피드백 #S-04
- 연관 강점/약점: S-04

### FR-025: no-answer 조건 완화 제안

- 설명: 시스템은 no-answer 발생 시 조건 완화 옵션을 제안해야 한다.
- 입력/출력:
  - 입력: `no_answer_reason`, `query_plan`
  - 출력: `relaxation_options[]`

- 처리 규칙:
  - 조건 완화 옵션은 최대 3개로 제한한다.
  - 허용 옵션은 `date_range_expand_7d`, `search_all_doc_type`, `include_needs_review`로 제한한다.

- 우선순위: M
- 수용 기준:
  - Given `no_candidate=true`인 질의 결과가 있는 상태
  - When 결과 없음 메시지가 표시되면
  - Then 시스템은 최소 1개, 최대 3개의 조건 완화 옵션을 표시한다.

- 출처: 기획서 §5.1, §5.2 / 피드백 #W-04, #W-05
- 연관 강점/약점: W-04, W-05

### FR-026: Classify_Ambiguous 판정

- 설명: 시스템은 분류 신뢰도 기준에 따라 `Classify_Ambiguous` 상태를 판정해야 한다.
- 입력/출력:
  - 입력: `category_candidates[]`
  - 출력: `classification_state`

- 처리 규칙:
  - top1 `category_confidence < 0.70`이면 `classification_state=Classify_Ambiguous`로 설정한다.
  - top1과 top2 confidence 차이가 0.10 미만이면 `classification_state=Classify_Ambiguous`로 설정한다.
  - golden dataset 81장 중 모호분류 샘플 3장을 포함해 Classify_Ambiguous 동작률을 측정한다.

- 우선순위: S
- 수용 기준:
  - Given top1 confidence가 0.68인 분류 결과가 있는 상태
  - When 분류 상태 판정이 실행되면
  - Then 시스템은 `Classify_Ambiguous`를 저장한다.

- 출처: 기획서 §5.1 / 피드백 #S-13, #W-06, #UF-04
- 연관 강점/약점: S-13, W-06, W-07, UF-04

### FR-027: 후보 유형 선택 UI 제공

- 설명: 시스템은 `Classify_Ambiguous` 상태에서 사용자에게 후보 유형을 선택하게 해야 한다.
- 입력/출력:
  - 입력: `category_candidates[]`
  - 출력: user-selected `doc_type`

- 처리 규칙:
  - 후보 유형은 confidence 상위 3개까지만 표시한다.
  - 각 후보에는 `doc_type`, `category_confidence`, 대표 키워드 3개 이하를 표시한다.

- 우선순위: S
- 수용 기준:
  - Given `Classify_Ambiguous` 상태인 캡처가 있는 상태
  - When 사용자가 후보 유형 선택 화면을 열면
  - Then 시스템은 후보 유형을 최대 3개 표시한다.

- 출처: 기획서 §5.1, §5.2 / 피드백 #S-13, #W-06
- 연관 강점/약점: S-13, W-06

### FR-028: 사용자 선택 유형 기반 재추출

- 설명: 시스템은 사용자가 선택한 `doc_type`의 스키마로 Information Extract를 재실행해야 한다.
- 입력/출력:
  - 입력: user-selected `doc_type`, `parsed_markdown`, `layout_blocks`
  - 출력: updated extracted fields

- 처리 규칙:
  - 기존 추출 결과는 `previous_extract_result`로 보존한다.
  - 재추출 결과에는 `user_override_doc_type=true`를 기록한다.

- 우선순위: S
- 수용 기준:
  - Given 사용자가 `scholarship` 후보 유형을 선택한 상태
  - When 재추출이 실행되면
  - Then 시스템은 장학금 스키마로 추출 결과를 갱신한다.

- 출처: 기획서 §5.1 / 피드백 #S-13, #W-06
- 연관 강점/약점: S-13, W-06

### FR-029: Top-3 실패 수동 선택

- 설명: 시스템은 사용자가 Top-3 결과에 정답이 없다고 표시하면 4~10위 fallback 후보를 표시해야 한다.
- 입력/출력:
  - 입력: `query_id`, user action `not_in_top3`
  - 출력: `fallback_candidates[4..10]`

- 처리 규칙:
  - fallback 후보는 최대 7개까지 표시한다.
  - fallback 후보에도 evidence_text가 없으면 표시하지 않는다.

- 우선순위: S
- 수용 기준:
  - Given Top-3 결과가 표시된 상태
  - When 사용자가 “찾는 캡처가 없음”을 클릭하면
  - Then 시스템은 4~10위 후보 중 evidence_text가 있는 후보를 표시한다.

- 출처: 기획서 §5.1 / 피드백 #W-08
- 연관 강점/약점: W-08

### FR-030: 사용자 수정 이력 저장

- 설명: 시스템은 사용자가 결과를 수동 선택·수정하면 correction_log에 저장해야 한다.
- 입력/출력:
  - 입력: `query_id`, `selected_capture_id`, `previous_rank`, `corrected_field`, `user_action`
  - 출력: `correction_id`

- 처리 규칙:
  - correction_log는 `/data/correction_log.json`에 저장한다.
  - correction_log는 `created_at`, `raw_query`, `before_value_hash`, `after_value_hash`를 포함한다.
  - correction_log에는 이름, 학번, 카드번호 등 개인정보 원문을 저장하지 않는다.

- 우선순위: S
- 수용 기준:
  - Given 사용자가 fallback 후보 중 정답 캡처를 선택한 상태
  - When 수정 저장이 실행되면
  - Then 시스템은 `correction_id`를 생성하고 `previous_rank`를 기록한다.

- 출처: 기획서 §5.1 / 피드백 #W-09
- 연관 강점/약점: W-09

### FR-031: QA 리포트 생성

- 설명: 시스템은 golden dataset 테스트 실행 후 SQLite `test_report` 레코드와 `test_report.json` export를 생성해야 한다.
- 입력/출력:
  - 입력: SQLite `golden_dataset`, test execution results
  - 출력: SQLite `test_report`, `test_report.json`

- 처리 규칙:
  - 필수 포함 지표는 다음 10개로 한다.
    1. 대표 데모 질문 성공률
    2. Top-3 정답 포함률
    3. 마감·기간 추출 정확도
    4. 금액 추출 정확도
    5. 제출물 추출 정확도
    6. 근거 문장 표시율
    7. no-answer 정확도
    8. 환각 답변률
    9. 확인 필요 UI 동작률
    10. threshold sweep 및 ambiguous_activation_rate

  - threshold sweep은 0.6/0.7/0.8 기준 비교를 포함한다.
  - ambiguous_activation_rate는 81장 전체 denominator와 모호분류 3장 결과를 포함한다.

- 우선순위: M
- 수용 기준:
  - Given golden dataset 81장과 대표 질의가 준비된 상태
  - When QA 테스트를 실행하면
  - Then `test_report.json`은 필수 지표 10개 이상과 모호분류 3장 결과를 포함한다.

- 출처: 기획서 §3.9, §4, §5.1 / 피드백 #S-10, #W-05, #W-07, #UF-04
- 연관 강점/약점: S-10, W-05, W-07, UF-04

### FR-032: 외부 입력 채널 payload contract 정의

- 설명: 시스템은 향후 메신저 채널 인덱싱을 위한 입력 payload contract를 정의해야 한다.
- 입력/출력:
  - 입력: `channel_type`, `external_message_id`, `image_payload`, `received_at`
  - 출력: `upload_job_id`, `channel_ingestion_status`

- 처리 규칙:
  - MVP에서는 실제 카카오톡·텔레그램 인증 연동을 구현하지 않는다.
  - 허용 `channel_type`은 `manual_upload`, `kakao_self`, `telegram_bot_stub`로 제한한다.
  - 별도 channel ingestion Webhook은 만들지 않고, 확장 시에도 이미지업로드 웹훅의 payload 형식 확장으로 수용한다.

- 우선순위: C
- 수용 기준:
  - Given `channel_type=telegram_bot_stub`와 이미지 payload가 있는 요청 명세가 작성된 상태
  - When 입력 payload contract 검토를 수행하면
  - Then request/response JSON schema가 문서화되어 있다.

- 출처: 기획서 §5.3 / 피드백 #W-02, #W-03, #N-02
- 연관 강점/약점: W-02, W-03, N-02

### FR-033: Golden Dataset 일괄 인덱싱

- 설명: 시스템은 데모 데이터 81장을 일괄 인덱싱해야 한다.
- 입력/출력:
  - 입력: SQLite `golden_dataset`, `/static/captures/*`
  - 출력: 81개 `capture_record`, `indexing_summary`

- 처리 규칙:
  - 일괄 인덱싱 대상 수는 81장으로 고정한다.
  - 완료 후 `indexed_count=81`이어야 한다.

- 우선순위: M
- 수용 기준:
  - Given 81장 캡처와 정답 메타데이터가 있는 상태
  - When 일괄 인덱싱을 실행하면
  - Then 시스템은 81개 capture_record와 indexing_summary를 생성한다.

- 출처: 기획서 §3.6, §3.7 / 피드백 #S-10, #N-01
- 연관 강점/약점: S-10, N-01

---

## 4. 비기능 요구사항 (NFR)

### 4.1 성능

| ID          | 요구사항                                                            |              정량 지표 | 우선순위 | 검증 방법                     | 출처               |
| ----------- | ------------------------------------------------------------------- | ---------------------: | -------- | ----------------------------- | ------------------ |
| NFR-PER-001 | 사전 인덱싱된 81장 대상 질의 응답은 지정 시간 이내 완료되어야 한다. |            P95 ≤ 1.5초 | M        | 81개 대표 질의 부하 테스트    | 기획서 §4 / S-10   |
| NFR-PER-002 | 결과 카드 첫 화면 렌더링은 지정 시간 이내 완료되어야 한다.          |            P95 ≤ 2.0초 | M        | 브라우저 Performance API 측정 | 기획서 §3.9 / S-12 |
| NFR-PER-003 | 발표 중 1장 라이브 업로드 인덱싱은 지정 시간 이내 완료되어야 한다.  | P95 ≤ 30초, 5회 테스트 | S        | 라이브 업로드 리허설          | 기획서 §3.6 / S-04 |
| NFR-PER-004 | 캐시 hit 결과 반환은 지정 시간 이내 완료되어야 한다.                |            P95 ≤ 1.0초 | M        | 캐시 hit 10회 테스트          | 기획서 §5.1 / S-04 |

### 4.2 보안

| ID          | 요구사항                                                                                                                               |                        정량 지표 | 우선순위 | 검증 방법                                                                      | 출처                       |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------: | -------- | ------------------------------------------------------------------------------ | -------------------------- |
| NFR-SEC-001 | Upstage API Key는 Frontend HTML, CSS, JavaScript에 포함되면 안 되며, n8n credentials 또는 n8n 환경변수에만 저장되어야 한다. |     Frontend secret exposure 0건 | M        | 정적 파일 grep, n8n credential 설정 확인 | 기획서 §3.1 / S-03 / UF-02 |
| NFR-SEC-002 | 발표용 데모 데이터의 개인정보는 마스킹되어야 한다.                                                                                     | 이름·학번·결제정보 원문 노출 0건 | M        | golden_dataset 검수                                                            | 기획서 §5.1 / S-03         |
| NFR-SEC-003 | 허용되지 않은 파일 MIME은 거부되어야 한다.                                                                                             |                      차단율 100% | M        | 악성 확장자 10종 업로드 테스트                                                 | 기획서 §2.2 / W-01         |
| NFR-SEC-004 | 원본 이미지는 지정된 로컬 경로 외부로 공개 배포되면 안 된다.                                                                           |                공개 URL 노출 0건 | M        | 라우팅 및 배포 설정 점검                                                       | 기획서 §3.1, §5.1          |

### 4.3 가용성 및 신뢰성

| ID          | 요구사항                                                 |                        정량 지표 | 우선순위 | 검증 방법               | 출처               |
| ----------- | -------------------------------------------------------- | -------------------------------: | -------- | ----------------------- | ------------------ |
| NFR-AVL-001 | 데모 환경은 발표 리허설 2시간 동안 사용 가능해야 한다.   |             availability ≥ 99.5% | S        | 2시간 health check      | 기획서 §5.1 / S-04 |
| NFR-AVL-002 | Upstage API 실패 시 재시도 정책을 적용해야 한다.         | 최대 2회 재시도, backoff 1초/3초 | M        | API mock failure 테스트 | 기획서 §5.1 / S-04 |
| NFR-AVL-003 | 사전 인덱싱된 81장에 대해 캐시 fallback이 동작해야 한다. |            fallback success 100% | M        | API 차단 후 81장 재질의 | 기획서 §5.1 / S-04 |
| NFR-AVL-004 | SQLite 업데이트는 트랜잭션으로 처리되어야 한다.            |                 transaction 적용률 100% | M        | SQLite write 테스트       | UF-03              |

### 4.4 확장성

| ID          | 요구사항                                                                                                      |                            정량 지표 | 우선순위 | 검증 방법                            | 출처               |
| ----------- | ------------------------------------------------------------------------------------------------------------- | -----------------------------------: | -------- | ------------------------------------ | ------------------ |
| NFR-SCL-001 | 신규 doc_type은 taxonomy와 schema_registry 수정으로 추가 가능해야 한다.                                       |       신규 doc_type 1개 추가 ≤ 2시간 | C        | 병원 예약 doc_type dry-run           | 기획서 §5.3 / S-11 |
| NFR-SCL-002 | SQLite 인덱스는 300개 capture_record까지 질의 성능을 유지해야 한다.                                           |                          P95 ≤ 2.5초 | C        | synthetic 300 records 테스트         | 기획서 §5.3        |
| NFR-SCL-003 | 외부 입력 채널은 이미지업로드 웹훅 payload contract 확장으로 수용 가능해야 한다.                              | channel_type 3종 schema 정의 | C        | payload schema review | 피드백 #W-02, #W-03 |

### 4.5 사용성

| ID          | 요구사항                                                              |                      정량 지표 | 우선순위 | 검증 방법                     | 출처               |
| ----------- | --------------------------------------------------------------------- | -----------------------------: | -------- | ----------------------------- | ------------------ |
| NFR-USA-001 | 수동 업로드는 제한된 사용자 행동 수 안에 제출되어야 한다.             | 랜딩 → 업로드 제출 ≤ 3 actions | M        | UI task test 5회              | W-01               |
| NFR-USA-002 | 결과 카드에는 근거·원본·confidence 상태가 표시되어야 한다.            |                    표시율 100% | M        | 81장 결과 카드 UI 테스트      | 기획서 §3.9 / S-12 |
| NFR-USA-003 | Classify_Ambiguous 해결은 제한된 사용자 행동 수 안에 완료되어야 한다. |     후보 선택 완료 ≤ 2 actions | S        | synthetic ambiguous UI 테스트 | S-13, W-06, UF-04  |
| NFR-USA-004 | no-answer 발생 시 조건 완화 제안이 표시되어야 한다.                   |                    표시율 100% | M        | no-answer 5개 질의 테스트     | W-04               |

### 4.6 호환성

| ID          | 요구사항                                                     |                          정량 지표 | 우선순위 | 검증 방법              | 출처                    |
| ----------- | ------------------------------------------------------------ | ---------------------------------: | -------- | ---------------------- | ----------------------- |
| NFR-CMP-001 | 이미지 입력 포맷은 JPG, PNG만 지원해야 한다.                 | JPG/PNG 성공률 100%, HEIC 차단율 100% | M        | 포맷별 업로드 테스트   | 사용자 결정             |
| NFR-CMP-002 | UI는 최신 2개 버전의 Chrome, Edge, Safari에서 동작해야 한다. |            주요 플로우 성공률 100% | S        | 브라우저 matrix 테스트 | UF-01                   |
| NFR-CMP-003 | n8n Webhook 응답은 JSON Schema 검증을 통과해야 한다.         |        schema validation pass 100% | M        | contract test          | 기획서 §3.4~3.5 / UF-02 |

### 4.7 규정 준수 및 보존

| ID           | 요구사항                                                 |               정량 지표 | 우선순위 | 검증 방법                   | 출처        |
| ------------ | -------------------------------------------------------- | ----------------------: | -------- | --------------------------- | ----------- |
| NFR-COMP-001 | 발표용 원본 이미지의 개인정보는 가명·마스킹되어야 한다.  |        PII 미마스킹 0건 | M        | 데이터셋 사전 검수          | 기획서 §5.1 |
| NFR-COMP-002 | 데모 종료 후 원본 이미지는 지정 시간 내 삭제되어야 한다. | 24시간 이내 삭제율 100% | S        | 파일 시스템 검증            | 기획서 §5.1 |
| NFR-COMP-003 | correction_log에는 개인정보 원문이 저장되면 안 된다.     |            PII 저장 0건 | M        | 로그 샘플링 100건 이하 검토 | W-09        |
| NFR-COMP-004 | SQLite DB 파일은 데모 환경의 지정 경로에 저장되어야 한다. |       DB 파일 존재율 100% | M        | SQLite 파일 검사           | UF-03       |

### 4.8 품질 및 정확도

| ID          | 요구사항                                                                     |                            정량 지표 | 우선순위 | 검증 방법                     | 출처             |
| ----------- | ---------------------------------------------------------------------------- | -----------------------------------: | -------- | ----------------------------- | ---------------- |
| NFR-QLT-001 | 3개 대표 데모 질문은 모두 성공해야 한다.                                     |                                  3/3 | M        | 데모 시나리오 테스트          | 기획서 §4 / S-09 |
| NFR-QLT-002 | Top-3 정답 포함률은 목표 이상이어야 한다.                                    |                                ≥ 90% | M        | 81개 대표 질의 테스트         | 기획서 §4 / S-10 |
| NFR-QLT-003 | 마감·기간 추출 정확도는 목표 이상이어야 한다.                                |                                ≥ 90% | M        | deadline/date_range 비교      | 기획서 §4        |
| NFR-QLT-004 | 금액 추출 정확도는 목표 이상이어야 한다.                                     |                                ≥ 95% | M        | 영수증 6장 amount 비교        | 기획서 §4        |
| NFR-QLT-005 | 제출물 추출 정확도는 목표 이상이어야 한다.                                   |                                ≥ 85% | M        | required_submission 비교      | 기획서 §4        |
| NFR-QLT-006 | 근거 문장 표시율은 목표 이상이어야 한다.                                     |                                ≥ 95% | M        | evidence_text 존재 여부 확인  | 기획서 §4 / S-08 |
| NFR-QLT-007 | 관련 없는 질문의 no-answer 정확도는 목표를 충족해야 한다.                    |                                 100% | M        | 관련 없는 질문 5개 테스트     | 기획서 §4 / S-08 |
| NFR-QLT-008 | 근거 없는 필드의 환각 답변률은 0이어야 한다.                                 |                                   0% | M        | unsupported field 질의 테스트 | 기획서 §4 / S-08 |
| NFR-QLT-009 | 낮은 confidence 또는 추출 충돌 샘플은 확인 필요 UI로 표시되어야 한다.        | 낮은 confidence 샘플 2장 표시율 100% | M        | 실패·노이즈 검증 샘플 테스트  | 기획서 §4 / S-03 |
| NFR-QLT-010 | Classify_Ambiguous 발화율을 보고해야 한다.                                   | 81장 전체 denominator 및 모호분류 3장 포함 | M        | `test_report.json` 확인       | UF-04            |

---

## 5. 데이터 요구사항

### 5.1 주요 엔티티

| ID     | 엔티티               | 주요 속성                                                                                                                                                                 | 관계                                                       | 보존 정책                                                          |
| ------ | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------ |
| DR-001 | CaptureRecord        | `capture_id`, `source_image_path`, `file_hash`, `file_meta`, `status`, `created_at`                                                                                       | ParsedDocument, ClassificationResult, ExtractedField와 1:1 | 원본 이미지는 데모 종료 후 24시간 이내 삭제                        |
| DR-002 | ParsedDocument       | `capture_id`, `parsed_markdown`, `layout_blocks`, `evidence_candidates`, `parse_confidence`                                                                               | CaptureRecord와 1:1                                        | QA 리포트 생성을 위해 7일 보존 가능                                |
| DR-003 | ClassificationResult | `capture_id`, `doc_type`, `category_confidence`, `category_candidates`, `classification_state`                                                                            | CaptureRecord와 1:1                                        | correction_log 반영 전후 상태 보존                                 |
| DR-004 | ExtractedField       | `capture_id`, `field_name`, `field_value`, `normalized_value`, `evidence_text`, `extract_confidence`                                                                      | CaptureRecord와 1:N                                        | 개인정보 원문이 포함된 field_value는 마스킹 후 저장                |
| DR-005 | RiskCard             | `card_id`, `capture_id`, `title`, `display_fields`, `confidence_badge`, `needs_review`                                                                                    | AnswerRecord와 N:M                                         | 데모 세션 종료 후 삭제 가능                                        |
| DR-006 | QueryPlan            | `query_id`, `raw_query`, `query_intent`, `target_doc_type`, `filters`, `sort_rule`, `answer_policy`                                                                       | AnswerRecord와 1:1                                         | QA 목적 7일 보존                                                   |
| DR-007 | AnswerRecord         | `answer_id`, `query_id`, `cards`, `cited_fields`, `no_answer`, `no_answer_reason`                                                                                         | QueryPlan과 1:1                                            | QA 목적 7일 보존                                                   |
| DR-008 | GoldenDatasetCase    | `case_id`, `capture_id`, `expected_doc_type`, `expected_fields`, `representative_query`                                                                                   | CaptureRecord와 1:1                                        | 프로젝트 저장소에 보존                                             |
| DR-009 | CorrectionLog        | `correction_id`, `query_id`, `selected_capture_id`, `previous_rank`, `corrected_field`, `before_value_hash`, `after_value_hash`, `created_at`                             | AnswerRecord와 N:1                                         | 개인정보 원문 없이 30일 보존 가능                                  |
| DR-010 | CacheEntry           | `file_hash`, `cached_parse`, `cached_classify`, `cached_extract`, `cached_at`, `api_version`                                                                              | CaptureRecord와 1:1                                        | 데모 종료 후 7일 이내 삭제                                         |
| DR-011 | SQLiteStore          | `capture_records`, `metadata_index`, `cache_entries`, `golden_dataset`, `test_report`, `correction_log`                                                                   | n8n workflow와 1:N                                         | 데모 종료 후 원본 이미지 24시간 이내 삭제, QA 데이터는 7일 보존 가능 |
| DR-012 | WebhookPayload       | `webhook_type`, `action`, `raw_query`, `image`, `selected_doc_type`, `selected_capture_id`, `corrected_field`                                                             | n8n Trigger Webhook과 1:N                                  | 요청 로그는 QA 목적 7일 보존 가능                                  |

### 5.2 데이터 무결성 규칙

| ID          | 규칙                                                                                                                                         |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| DR-RULE-001 | 모든 `capture_id`는 `CAP-{000}` 형식을 따른다.                                                                                               |
| DR-RULE-002 | 모든 ExtractedField는 `evidence_text` 또는 `no_evidence_reason` 중 하나를 가져야 한다.                                                       |
| DR-RULE-003 | `doc_type=noise`인 캡처는 `deadline`, `amount`, `required_submission`을 필수 출력으로 요구하지 않는다.                                       |
| DR-RULE-004 | `currency` 기본값은 `KRW`이다.                                                                                                               |
| DR-RULE-005 | `indexed_at`, `deadline`, `date_range`는 KST 기준으로 저장한다.                                                                              |
| DR-RULE-006 | `confidence` 값은 0.00 이상 1.00 이하 소수로 저장한다.                                                                                       |
| DR-RULE-007 | `needs_review=true`인 카드는 UI에서 숨기지 않는다.                                                                                           |
| DR-RULE-008 | no-answer 질의 결과는 빈 answer 문자열 대신 `no_answer=true`와 `no_answer_reason`을 저장한다.                                                |
| DR-RULE-009 | SQLite가 source of truth이다.                                                                                                                |
| DR-RULE-010 | Frontend에는 Upstage API Key, 원본 결제정보, 학번, 이름 원문을 저장하지 않는다.                                                              |
| DR-RULE-011 | SQLite 쓰기는 트랜잭션으로 수행한다.                                                                                                         |
| DR-RULE-012 | `test_report.json` export는 SQLite `test_report` 내용을 기준으로 생성한다.                                                                   |
| DR-RULE-013 | `test_report`에는 threshold sweep 결과와 ambiguous_activation_rate를 포함한다.                                                               |
| DR-RULE-014 | 외부 채널 관련 필드는 별도 Webhook이 아니라 이미지업로드 웹훅 payload 확장 필드로만 포함한다.                                                |

### 5.3 Golden Dataset 구성

| 유형               | 장수 | 포함 정보                                 | 검증 필드                                                      |
| ------------------ | ---: | ----------------------------------------- | -------------------------------------------------------------- |
| 과제               |   20 | 과목명, 제출 기한, 제출 방식, 필요 제출물 | `deadline`, `course`, `required_submission`, `action_items`    |
| 학사·행정 공지     |   18 | 신청 마감, 담당 기관, 안내 문구           | `deadline`, `institution`, `action_items`                      |
| 장학금             |   15 | 신청 기간, 기관명, 필요 제출물            | `date_range`, `deadline`, `institution`, `required_submission` |
| 영수증             |   16 | 결제 금액, 상호명, 결제일                 | `amount`, `merchant`, `payment_date`                           |
| 장소·링크          |    9 | 주소, URL, 방문 일정                      | `address`, `url`, `date_range`                                 |
| 모호분류 전용 샘플 |    3 | doc_type 경계가 겹치는 캡처               | `category_candidates`, `classification_state`                  |
| 합계               |   81 | 손실 방지 데모 고정 데이터                | Top-3, 필드 정확도, no-answer, ambiguous_activation_rate 검증   |

---

## 6. 인터페이스 요구사항

### 6.1 UI 인터페이스

| ID        | UI 요구사항                                                      | 입력                    | 출력                          | 수용 기준                                       |
| --------- | ---------------------------------------------------------------- | ----------------------- | ----------------------------- | ----------------------------------------------- |
| IR-UI-001 | 정적 HTML 업로드 화면은 이미지 선택과 제출 기능을 제공해야 한다. | 사용자 파일 선택        | n8n Webhook upload request    | 랜딩 후 3 actions 이내 업로드 제출              |
| IR-UI-002 | UI는 CSS 파일과 JavaScript만으로 반응형 화면을 제공해야 한다.    | HTML/CSS/JavaScript     | responsive UI                 | React/Next.js/Tailwind 의존성 0건               |
| IR-UI-003 | JavaScript는 지정된 2개 n8n Webhook으로만 요청을 전송해야 한다.  | user event              | webhook request               | Backend API 호출 0건, Trigger Webhook 2개만 사용 |
| IR-UI-004 | 인덱싱 상태 배지는 pipeline status를 표시해야 한다.              | `status`                | received/validated/parsed/classified/extracted/indexed/ready | 상태 변경 후 1초 이내 UI 반영 |
| IR-UI-005 | 3개 데모 질문 버튼을 제공해야 한다.                              | 버튼 클릭               | raw_query                     | 버튼 문구 3개 고정                              |
| IR-UI-006 | 결과 카드는 핵심 필드와 confidence badge를 표시해야 한다.        | `risk_card`             | card UI                       | 81장 테스트에서 표시율 100%                     |
| IR-UI-007 | Classify_Ambiguous 화면은 후보 유형을 표시해야 한다.             | `category_candidates`   | 후보 유형 선택 UI             | 후보 최대 3개 표시                              |
| IR-UI-008 | no-answer 화면은 조건 완화 옵션을 표시해야 한다.                 | `no_answer_reason`      | relaxation_options            | no-answer 5개 테스트에서 100% 표시              |

### 6.2 n8n Webhook 인터페이스

MVP의 n8n Trigger Webhook은 아래 2개만 사용한다. 상태 조회, 모호분류 선택, correction_log 저장, QA 리포트 생성은 별도 Webhook을 만들지 않고 질문 전송 웹훅의 `action` 분기 또는 n8n 내부 수동 실행/Workflow 단계로 처리한다.

| ID         | n8n Trigger Webhook | Method | Request | Response | 수용 기준 |
| ---------- | ------------------- | ------ | ------- | -------- | --------- |
| IR-N8N-001 | 이미지업로드 웹훅 `/webhook/image-upload` | POST | `multipart/form-data.image`, optional `channel_type`, optional `external_message_id` | `upload_job_id`, `capture_id`, `status` | 정상 이미지 업로드 시 1초 이내 수신 응답 |
| IR-N8N-002 | 질문 전송 웹훅 `/webhook/question-submit` | POST | `raw_query`, optional `action`, optional `query_id`, optional `selected_doc_type`, optional `selected_capture_id`, optional `corrected_field` | `answer`, `cards`, `no_answer`, `relaxation_options`, optional `processing_log` | 3개 데모 질문 모두 성공 |

### 6.3 외부 시스템 연동

| ID         | 외부 인터페이스             | 입력                                              | 출력                                                                          | 처리 원칙                                                    |
| ---------- | --------------------------- | ------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------ |
| IR-EXT-001 | Upstage Document Parse      | `binary.data`                                     | `parsed_markdown`, `layout_blocks`, `evidence_candidates`, `parse_confidence` | 캡처 이미지를 문서형 구조로 변환                             |
| IR-EXT-002 | Upstage Document Classify   | `parsed_markdown`, `file_meta`                    | `doc_type`, `category_confidence`, `category_candidates`                      | 6개 taxonomy 기반 분류                                       |
| IR-EXT-003 | Upstage Information Extract | `parsed_markdown`, `layout_blocks`, `schema_json` | 핵심 필드, `evidence_text`, `extract_confidence`                              | doc_type별 schema 적용                                       |
| IR-EXT-004 | Solar Query Planner         | `raw_query`                                       | `query_intent`, `target_doc_type`, `filters`, `sort_rule`                     | 자유 답변 금지                                               |
| IR-EXT-005 | Solar Evidence Answer       | `candidate_cards`, `evidence_text`                | `answer`, `cards`, `cited_fields`, `no_answer`                                | 근거 문장 범위 내 답변                                       |
| IR-EXT-006 | n8n Workflow                | Webhook event                                     | node execution log                                                            | validation, JPG/PNG 저장, Upstage 호출, no-answer 처리 시각화 |
| IR-EXT-007 | Channel Adapter Stub        | channel payload                                   | upload job                                                                    | 별도 Webhook 없이 이미지업로드 웹훅 payload 확장으로만 정의  |

### 6.4 삭제된 인터페이스

| 삭제 ID        | 삭제 항목                       | 삭제 사유                             |
| -------------- | ------------------------------- | ------------------------------------- |
| IR-API-001~007 | Backend `/api/*` endpoints      | 별도 Backend 제거                     |
| IR-N8N-003~006 | status/doc-type/correction/qa 개별 Webhook | Trigger Webhook 2개 제한에 따라 질문 전송 웹훅 `action` 분기로 통합 |
| FR-034 기존안  | IndexedDB 클라이언트 캐시 저장  | PRD 저장소 SQLite 확정에 따라 MVP 요구사항에서 제외 |

---

## 7. 제약사항 및 가정

### 7.1 제약사항

| ID      | 제약사항                                                             | 근거                      |
| ------- | -------------------------------------------------------------------- | ------------------------- |
| CON-001 | MVP 데이터셋은 81장으로 고정한다.                                    | PRD OI-004 결정           |
| CON-002 | 발표 중 라이브 업로드는 1장만 수행한다.                              | 기획서 §2.1, §3.6         |
| CON-003 | 사진첩 자동 동기화는 MVP에서 제외한다.                               | 기획서 §3.6, 피드백 #N-02 |
| CON-004 | 캘린더 실연동은 MVP에서 제외한다.                                    | 기획서 §3.6, 피드백 #N-02 |
| CON-005 | 자유형 챗봇은 MVP에서 제외한다.                                      | 기획서 §3.6               |
| CON-006 | 답변은 evidence_text가 있는 필드에 한정한다.                         | 기획서 §2.1, §3.5         |
| CON-007 | confidence 기본 기준값은 0.70으로 둔다.                              | 기획서 §5.1, 피드백 #W-05 |
| CON-008 | 모든 날짜·시간은 KST 기준으로 정규화한다.                            | 기획서 §3.4               |
| CON-009 | 원본 캡처는 n8n 로컬 디스크에 저장한다.                              | UF-02                     |
| CON-010 | Upstage API 호출 실패 가능성에 대비해 캐시 fallback을 구현한다.      | 기획서 §5.1               |
| CON-011 | Frontend는 HTML, CSS, JavaScript만 사용하며 React, Next.js, Tailwind CSS 등 프레임워크는 사용하지 않는다. | PRD OI-001 결정 |
| CON-012 | Backend는 별도 FastAPI/Node.js 서버 없이 n8n 자체 기능과 Webhook/Workflow 노드로 구현한다. | PRD OI-002 결정 |
| CON-013 | 저장소는 SQLite를 사용한다.                                          | PRD OI-003 결정 |
| CON-014 | n8n Trigger Webhook은 이미지업로드 웹훅과 질문 전송 웹훅 총 2개만 사용한다. | PRD 사용자 결정 |
| CON-015 | threshold sweep 결과는 QA 리포트에 포함한다.                         | PRD NFR-QLT-009 |
| CON-016 | golden dataset에는 모호분류 샘플 3장을 포함한다.                     | PRD OI-004 결정 |

### 7.2 가정

| ID      | 가정                                                                                                       |
| ------- | ---------------------------------------------------------------------------------------------------------- |
| ASM-001 | 데모 데이터 81장은 발표 전 SQLite `golden_dataset` 및 `golden_dataset.json` export와 함께 준비되며, 이 중 모호분류 샘플은 3장이다. |
| ASM-002 | Upstage API Key는 n8n credentials 또는 n8n 환경변수로 주입된다.                                            |
| ASM-003 | 데모 환경은 로컬 또는 단일 서버에서 실행된다.                                                              |
| ASM-004 | 사용자는 대학생, 장학금 신청자, 동아리·프로젝트 팀원, 행정 공지 이용자, 발표·실습 팀을 포함한다.           |
| ASM-005 | Frontend는 HTML/CSS/JavaScript 정적 파일, Backend는 n8n 자체 Workflow, 저장소는 SQLite로 구현한다.          |
| ASM-006 | 라이브 업로드 실패 시 동일 시나리오의 백업 영상과 캐시 결과로 시연한다.                                    |
| ASM-007 | 외부 메신저 채널 연동은 이번 MVP에서 실제 인증·수신을 구현하지 않고 이미지업로드 웹훅 확장용 payload contract만 정의한다. |
| ASM-008 | n8n 로컬 디스크는 데모 환경에서 읽기/쓰기 권한을 가진다.                                                   |
| ASM-009 | SQLite 업데이트 중 동시 쓰기 요청은 n8n workflow queue 또는 sequential execution으로 제어한다.             |

---

## 8. 추적 매트릭스 (Traceability Matrix)

| 요구사항 ID      | 기획서 출처      | 피드백 ID                             | 검증 방법                                      |
| ---------------- | ---------------- | ------------------------------------- | ---------------------------------------------- |
| FR-001           | §2.2, §3.3       | W-01, UF-01, UF-02                    | HTML 업로드 → n8n Webhook 테스트               |
| FR-002           | §2.2             | W-01                                  | 파일 확장자 negative test                      |
| FR-003           | §2.2, §5.1       | W-01                                  | 10MB 초과 업로드 테스트                        |
| FR-004           | §2.2, §3.9       | S-04                                  | HEIC 거부 테스트                               |
| FR-005           | §2.1, §3.4       | S-11, UF-02                           | n8n 로컬 디스크 저장 확인                      |
| FR-006           | §3.1~3.3         | S-02                                  | Document Parse mock/integration test           |
| FR-007           | §2.2, §3.2~3.3   | S-06, W-06                            | Classify 결과 schema validation                |
| FR-008           | §3.2~3.3         | S-05, S-06                            | schema_registry 라우팅 테스트                  |
| FR-009           | §2.2, §3.3       | S-05, S-11                            | Extract 필드/evidence 저장 확인                |
| FR-010           | §3.4, §4         | S-09                                  | 날짜 정규화 unit test                          |
| FR-011           | §2.4, §3.4       | S-09                                  | 금액 정규화 unit test                          |
| FR-012           | §3.6, §5.1       | S-03, W-04, W-05                      | confidence threshold 테스트                    |
| FR-013           | §3.1, §3.4       | S-04, S-10, UF-02, UF-03              | SQLite write test                              |
| FR-014           | §2.4, §3.5       | S-07                                  | Query Planner contract test                    |
| FR-015           | §3.5             | S-07, S-08                            | invalid query_plan test                        |
| FR-016           | §2.4, §3.6, §4   | S-09, S-10, W-08                      | Top-3 검색 테스트                              |
| FR-017           | §2.5, §3.5       | S-07, S-08                            | evidence-bound answer test                     |
| FR-018           | §2.1, §3.5, §4   | S-08, W-04                            | missing evidence no-answer test                |
| FR-019           | §2.1~2.4         | S-01, S-11, S-12                      | 결과 카드 UI 테스트                            |
| FR-020           | §3.9, §4         | S-12                                  | evidence highlight UI 테스트                   |
| FR-021           | §2.1, §3.9       | S-01, S-12                            | 원본 캡처 뷰어 테스트                          |
| FR-022           | §2.1, §2.4, §3.6 | S-09, N-01                            | 3개 데모 버튼 E2E                              |
| FR-023           | §3.3, §3.6, §3.9 | S-04, UF-02                           | n8n execution log 표시 테스트                  |
| FR-024           | §3.6, §5.1       | S-04                                  | API failure cache fallback test                |
| FR-025           | §5.1~5.2         | W-04, W-05                            | no-answer 조건 완화 UI 테스트                  |
| FR-026           | §5.1             | S-13, W-06, UF-04                     | ambiguous 판정 unit test                       |
| FR-027           | §5.1~5.2         | S-13, W-06                            | 후보 유형 선택 UI 테스트                       |
| FR-028           | §5.1             | S-13, W-06                            | user override 재추출 테스트                    |
| FR-029           | §5.1             | W-08                                  | fallback 후보 표시 테스트                      |
| FR-030           | §5.1             | W-09                                  | correction_log 저장 테스트                     |
| FR-031           | §3.9, §4, §5.1   | S-10, W-05, W-07, UF-04, UF-05        | test_report.json 검증                          |
| FR-032           | §5.3             | W-02, W-03, N-02                      | payload contract review                        |
| FR-033           | §3.6~3.7         | S-10, N-01                            | 81장 일괄 인덱싱 테스트                        |
| NFR-PER-001~004  | §3.6, §4, §5.1   | S-04, S-10, UF-02                     | 성능 측정                                      |
| NFR-SEC-001~004  | §3.1, §5.1       | S-03, W-01, UF-02                     | secret scan, storage inspection                |
| NFR-AVL-001~004  | §5.1             | S-04, UF-03                           | health check, cache fallback, SQLite write test |
| NFR-SCL-001~003  | §5.3             | S-11, W-02, W-03                      | schema review, dry-run                         |
| NFR-USA-001~004  | §3.9, §5.2       | W-01, W-04, S-13, UF-02               | UI task test                                   |
| NFR-CMP-001~003  | §2.2, §3.1       | UF-01, UF-02                          | 브라우저 및 contract test                      |
| NFR-COMP-001~004 | §5.1             | S-03, W-09, UF-03                     | PII 검수, SQLite 파일 검사                     |
| NFR-QLT-001~010  | §4, §5.1         | S-08, S-09, S-10, UF-04               | QA 리포트 검증                                 |
| DR-001~012       | §3.4~3.5, §5.1   | S-10, W-09, UF-02, UF-03              | 데이터 스키마 검증                             |
| IR-UI-001~008    | §3.9, §5.2       | W-01, W-04, S-13, UF-01, UF-02        | UI E2E 테스트                                  |
| IR-N8N-001~002   | §2.2, §3.3       | UF-02, UF-05                          | 2개 Webhook contract test                      |
| IR-EXT-001~007   | §3.1~3.3         | S-02, S-05, S-07, W-03                | n8n workflow/API mock test                     |
| CON-001~016      | §3.6, §5.3       | N-02, UF-01~UF-05                     | 범위 검토                                      |
| ASM-001~009      | §3.6, §5.1       | UF-01~UF-05                           | 구현 착수 전 확인                              |

---

## 9. 리스크 및 오픈 이슈

### 9.1 리스크

| 리스크                            | 영향                                         | 대응 방안                                                                        | 담당                     |
| --------------------------------- | -------------------------------------------- | -------------------------------------------------------------------------------- | ------------------------ |
| 업로드 마찰                       | 손실 방지 가치가 실제 행동으로 연결되지 않음 | 수동 업로드 3 actions 이하 유지, 이미지업로드 웹훅 payload 확장 가능성 정의      | PM / Frontend            |
| no-answer 과다                    | 사용자가 답변 실패 도구로 인식               | 조건 완화 옵션, 원본 열기, no-answer 정확도와 환각 답변률 동시 측정              | Workflow / AI            |
| confidence 0.70 임계치 부적합     | 회수율 또는 안전성 저하                      | 0.6/0.7/0.8 threshold sweep 후 test_report에 기록                                | Data / QA                |
| doc_type 경계 모호                | 잘못된 스키마 적용으로 추출 실패             | Classify_Ambiguous 판정, 후보 유형 선택, 재추출 기능 유지                        | Workflow / AI / Frontend |
| golden dataset 모호분류 샘플 관리 | 분류 모호성 정량 검증 필요                   | golden dataset 81장 중 모호분류 3장을 포함해 ambiguous_activation_rate 측정      | PM / QA                  |
| Top-3 목표 미달                   | 핵심 QA 지표 실패                            | 4~10위 fallback 후보, correction_log 저장                                        | Workflow / Data          |
| Upstage API 지연 또는 실패        | 라이브 데모 중단                             | 캐시 fallback, API 재시도 2회, 백업 영상                                         | Workflow / 발표          |
| n8n 단독 백엔드 한계              | 복잡한 서버 로직 구현이 어려울 수 있음        | n8n workflow가 파일 검증, JPG/PNG 저장, Upstage 호출, SQLite 저장 담당           | Workflow                 |
| API Key 노출                      | 보안 사고                                    | n8n credentials 또는 n8n 환경변수 저장, Frontend 노출 0건 검증                   | Workflow / QA            |
| SQLite DB 손상                    | 인덱스 손실                                  | 트랜잭션 적용, 백업 DB 파일 유지                                                 | Workflow                 |
| 개인정보 노출                     | 발표·저장 리스크                             | 데모 데이터 가명·마스킹, 원본 로컬 저장, 24시간 내 삭제                          | Data / QA                |
| Low-code 평가 매핑 약화           | 평가 항목 대응력 저하                        | n8n workflow JSON과 Upstage 호출 노드·입출력 매핑 제출                           | Workflow                 |

### 9.2 오픈 이슈

| ID     | 오픈 이슈                                                               | 최신 상태 | 결정                                                      |
| ------ | ----------------------------------------------------------------------- | --------- | --------------------------------------------------------- |
| OI-001 | Frontend 기술 선택                                                     | 해결      | HTML, CSS, JavaScript만 사용                              |
| OI-002 | Backend 기술 선택                                                      | 해결      | n8n 자체 기능만 사용                                      |
| OI-003 | 저장소 선택                                                            | 해결      | SQLite                                                    |
| OI-004 | golden dataset 규모 및 모호분류 샘플 수                                | 해결      | golden dataset 81장, 모호분류 3장                         |
| OI-005 | threshold sweep 결과가 0.70 기준과 충돌할 경우 발표 기준 선택 필요      | 미해결    | 환각 0% 우선, 회수율은 조건 완화로 보완                   |
| OI-006 | n8n Trigger Webhook 수                                                  | 해결      | 이미지업로드 웹훅, 질문 전송 웹훅 총 2개만 사용           |
| OI-007 | n8n Webhook URL을 로컬/배포 환경 중 어디로 고정할지 결정 필요           | 미해결    | 데모 환경 확정 시 `config.js`에 기록                       |
