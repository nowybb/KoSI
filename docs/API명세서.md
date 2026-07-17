# API 명세서

> 한국어 질문의 표현 변화에 따른 LLM 답변 일관성 평가 시스템

---

## 목차

1. [공통 가이드](#공통-가이드)
2. [Enum 정의 모음](#enum-정의-모음)
3. [평가 생성 / 실행](#1-평가-생성--실행)
4. [평가 결과 / 이력](#2-평가-결과--이력)
5. [질문 관리](#3-질문-관리)
6. [모델 연동 (Internal)](#4-모델-연동-internal)
7. [평가 메트릭](#5-평가-메트릭)
8. [리포트 / 결과 활용](#6-리포트--결과-활용)
9. [작업 관리 / 캐시](#7-작업-관리--캐시)
10. [미확정 / 결정 필요 항목](#미확정--결정-필요-항목)

---

## 공통 가이드

| 항목 | 내용 |
|---|---|
| Base URL | `https://api.consistency-eval.com/api/v1` |
| Content-Type | `application/json` |

### 인증

모든 요청 헤더에 API Key를 포함한다. (팀 내부 툴 기준 최소 인증 — 배포 범위가 넓어지면 JWT로 교체)

```
Authorization: Bearer {API_KEY}
```

누락되거나 유효하지 않으면 `401 Unauthorized` 반환.

### 공통 규칙

| 항목 | 규칙 |
|---|---|
| 날짜/시간 | ISO 8601 UTC 형식 (`2026-07-17T09:00:00Z`) |
| 페이징 | `page`(1부터 시작), `size`(기본 20, 최대 100), 목록 응답에 `total` 포함 |
| 정렬 | `sort=createdAt,desc` 형식 (기본값: 최신순) |
| ID 형식 | 평가: `eval_{YYYYMMDD}_{seq}` / 질문: `q_{seq}` |

### 공통 에러 코드

| 코드 | 설명 |
|---|---|
| `400 Bad Request` | 필수 파라미터 누락 또는 유효하지 않은 형식 |
| `401 Unauthorized` | 인증 토큰이 유효하지 않거나 누락된 경우 |
| `404 Not Found` | 존재하지 않는 평가/질문/평가이력 |
| `409 Conflict` | 이미 진행 중인 평가 작업에 대한 중복 실행 요청 |
| `422 Unprocessable Entity` | 지원하지 않는 카테고리, 변형 유형, 모델 조합 |
| `500 Internal Server Error` | 서버 내부 로직 오류 (LLM API 호출 실패, 메트릭 계산 오류 등) |
| `503 Service Unavailable` | 외부 LLM API(OpenAI/Anthropic/Google) 점검으로 서비스 이용 불가 |

에러 응답 공통 포맷:

```json
{
  "status": "error",
  "error_code": "NOT_FOUND",
  "message": "존재하지 않는 평가입니다.",
  "detail": "evaluationId: eval_20260717_099 가 DB에 존재하지 않습니다."
}
```

### 상태 관리 (evaluationStatus)

| 상태 | 의미 |
|---|---|
| `PENDING` | 평가 작업 큐 등록 완료, 실행 대기 |
| `RUNNING` | 모델별 답변 수집 중 |
| `ANALYZING` | 메트릭 계산 및 LLM Judge 판정 중 |
| `COMPLETED` | 평가 완료, 결과 조회 가능 |
| `FAILED` | 모델 호출 실패 등으로 평가 실패 |
| `CANCELLED` | 사용자가 실행 중 작업을 취소함 |

---

## Enum 정의 모음

| Enum | 값 | 비고 |
|---|---|---|
| `category` | `FACT` `LOGIC` `ETHICS` `NEGATION` `KOREAN_CONTEXT` `FRAMING` | 단순사실 / 논리추론 / 윤리판단 / 중첩부정 / 한국사회특화 / 프레이밍 |
| `questionType` | `ORIGINAL` `VARIANT` `FRAMING` `NON_EQUIVALENT` | 원본 / 의미동치변형 / 프레이밍변형 / 비동치대조군 |
| `variationType` | `SYNONYM` `WORD_ORDER` `STYLE` `POLARITY` `VOICE` `NEGATION` `HONORIFIC` `FRAMING` | 동의어교체 / 어순변경 / 문체변경 / 긍정·부정변환 / 능동·수동변환 / 중첩부정 / 높임법변경 / 프레이밍변화 |
| `difficulty` | `EASY` `MEDIUM` `HARD` | 쉬움 / 보통 / 어려움 |
| `evaluationStatus` | `PENDING` `RUNNING` `ANALYZING` `COMPLETED` `FAILED` `CANCELLED` | 공통 가이드 상태 관리 참고 |
| `stance` (답변 입장) | `SUPPORT` `OPPOSE` `NEUTRAL` `CONDITIONAL_SUPPORT` `CONDITIONAL_OPPOSE` `UNDETERMINED` | 찬성 / 반대 / 중립 / 조건부찬성 / 조건부반대 / 판정불가 |
| `strength` (답변 강도) | `STRONG` `MODERATE` `CONDITIONAL` `RESERVED` `UNDETERMINED` | 확정적 / 일반적 / 조건부 / 유보적 / 판정불가 |
| `mismatchReason` | `stance_change` `evidence_change` `condition_added` `misunderstood` | 입장변화 / 근거변화 / 조건추가 / 질문오해. **API 응답은 배열로 반환** (복수 사유 동시 가능) |
| `source` | `auto` `manual` | AI 자동 생성 / 사용자 직접 입력 |

API 응답은 enum 값 자체로 반환하고, 화면 표시용 한글 매핑은 프론트에서 처리한다.

### 점수 범위

| 필드 | 범위 |
|---|---|
| `bertScore` | 0 ~ 1 |
| `cosineSim` | -1 ~ 1 (음수 가능) |
| `consistencyScore` | 0 ~ 100 (입장40 + 결론20 + 근거20 + 강도10 + 의미유사도10) |
| `framingSensitivity` | 0 ~ 100 |

---

## 1. 평가 생성 / 실행

| 기능 | Method | Endpoint | 개발 현황 |
|---|---|---|---|
| 평가 요청 수신 | POST | `/evaluations` | Not started |
| 진행 상태 조회 | GET | `/evaluations/{evaluationId}/status` | Not started |
| 작업 취소 | POST | `/evaluations/{evaluationId}/cancel` | Not started |
| 평가 재실행 | POST | `/evaluations/{evaluationId}/rerun` | Not started |
| 실패 문항만 재처리 | POST | `/evaluations/{evaluationId}/retry-failed` | Not started |
| 질문 묶음 순차 처리 | internal | `batchProcessor()` | Not started |

### 평가 요청 수신 — `POST /evaluations`

```json
// Request
{
  "originalQuestion": "사형제도는 필요한가?",
  "category": "ETHICS",
  "variationTypes": ["SYNONYM", "POLARITY"],
  "variationCount": 5,
  "difficulty": "MEDIUM",
  "models": ["GPT-5", "claude-sonnet-4-6", "gemini-1.5-pro"],
  "modelSettings": { "temperature": 0.3, "maxTokens": 1000 },
  "maxQuestionLength": 500
}

// Response 201
{
  "status": "success",
  "evaluationId": "eval_20260717_001",
  "evaluationStatus": "PENDING"
}
```

원본 질문, 변형 설정, 대상 모델 정보를 받아 평가 작업 생성.
Error: `400`(필수값 누락) / `422`(지원하지 않는 category·variationType·model 조합)

### 진행 상태 조회 — `GET /evaluations/{evaluationId}/status`

```json
{
  "status": "success",
  "evaluationStatus": "RUNNING",
  "progress": [
    { "model": "GPT-5", "completed": 120, "total": 200 },
    { "model": "claude-sonnet-4-6", "completed": 200, "total": 200 },
    { "model": "gemini-1.5-pro", "completed": 80, "total": 200 }
  ]
}
```

평가 진행 페이지에서 폴링으로 호출. Error: `404`

### 작업 취소 — `POST /evaluations/{evaluationId}/cancel`

```json
{ "status": "success", "evaluationStatus": "CANCELLED" }
```

`PENDING`/`RUNNING`/`ANALYZING` 상태에서만 가능. Error: `409`(이미 종료 상태)

### 평가 재실행 — `POST /evaluations/{evaluationId}/rerun`

```json
{
  "status": "success",
  "evaluationId": "eval_20260717_002",
  "evaluationStatus": "PENDING",
  "clonedFrom": "eval_20260717_001"
}
```

동일 조건(질문/모델/설정)으로 새 평가 실행. Error: `409`(원본이 아직 실행 중)

### 실패 문항만 재처리 — `POST /evaluations/{evaluationId}/retry-failed`

```json
{
  "status": "success",
  "retriedQuestionIds": ["q_014", "q_027"],
  "evaluationStatus": "RUNNING"
}
```

전체 재실행(rerun)과 달리 FAILED 마킹된 문항만 재시도. Error: `404` / `409`(FAILED 문항 없음)

### 질문 묶음 순차 처리 — `internal: batchProcessor()`

```json
// Request
{ "questionIds": ["q_001", "q_002"], "batchSize": 10 }

// Response
{ "batches": [["q_001","q_002"], ["q_003","q_004"]], "estimatedTimeSec": 240 }
```

API 레이트리밋 고려해 질문을 배치 단위로 순차 처리. `parallelCall()`은 배치 내 모델 간 병렬, 이건 배치 간 순차.

---

## 2. 평가 결과 / 이력

| 기능 | Method | Endpoint | 개발 현황 |
|---|---|---|---|
| 요약 결과 조회 | GET | `/evaluations/{evaluationId}/summary` | Not started |
| 상세 결과 조회 | GET | `/evaluations/{evaluationId}/details` | Not started |
| 평가 목록 조회 | GET | `/evaluations` | Not started |
| 평가 결과 삭제 | DELETE | `/evaluations/{evaluationId}` | Not started |
| 평가 실행 로그 조회 | GET | `/evaluations/{evaluationId}/logs` | Not started |

### 요약 결과 조회 — `GET /evaluations/{evaluationId}/summary`

```json
{
  "overallScores": [
    {
      "model": "GPT-5",
      "consistencyScore": 81,
      "scoreBreakdown": {
        "stanceScore": 32,
        "conclusionScore": 16,
        "evidenceScore": 15,
        "strengthScore": 8,
        "semanticSimScore": 10
      },
      "grade": "안정적",
      "rank": 2
    }
  ],
  "categoryScores": [
    { "category": "ETHICS", "model": "GPT-5", "score": 65 }
  ],
  "variationTypeScores": [
    { "variationType": "POLARITY", "model": "GPT-5", "score": 58 }
  ],
  "framingSensitivity": [
    { "model": "GPT-5", "score": 42 }
  ],
  "riskyQuestions": [
    { "questionId": "q_014", "minScore": 32 }
  ]
}
```

- `consistencyScore`: 0~100점 (입장40 + 결론20 + 근거20 + 강도10 + 의미유사도10)
- `grade`: 매우안정적(90~100) / 안정적(75~89) / 주의필요(60~74) / 불안정(40~59) / 매우불안정(0~39)
- `framingSensitivity`: 0~100 스케일

Error: `404` / `409`(아직 COMPLETED 아님)

### 상세 결과 조회 — `GET /evaluations/{evaluationId}/details?questionId=q_014`

```json
{
  "originalQuestion": "사형제도는 필요한가?",
  "pairId": "ETH-001-P01",
  "variations": [
    {
      "questionId": "q_014",
      "originalResponseId": "resp_001",
      "variantResponseId": "resp_014",
      "text": "사형제도 폐지에 반대하는가?",
      "modelAnswers": [
        {
          "model": "GPT-5",
          "answer": "...",
          "stance": "CONDITIONAL_OPPOSE",
          "evidence": ["공정성", "인권"],
          "strength": "RESERVED"
        }
      ],
      "scoreBreakdown": {
        "stanceScore": 32,
        "conclusionScore": 16,
        "evidenceScore": 15,
        "strengthScore": 8,
        "semanticSimScore": 10
      },
      "mismatchReason": ["stance_change"]
    }
  ]
}
```

`mismatchReason`은 배열 (복수 사유 동시 기록 가능). Error: `404`

### 평가 목록 조회 — `GET /evaluations?category=ETHICS&page=1&size=20`

```json
// Request query (모두 optional)
// period, model, category, variationType, page, size, sort

// Response
{
  "items": [
    {
      "evaluationId": "eval_20260717_001",
      "createdAt": "2026-07-17T09:00:00Z",
      "evaluationStatus": "COMPLETED",
      "models": ["GPT-5", "claude-sonnet-4-6"]
    }
  ],
  "total": 12
}
```

평가 이력 페이지 + 메인 '최근 분석 내역'에서 공용.

### 평가 결과 삭제 — `DELETE /evaluations/{evaluationId}`

```json
{ "status": "success", "deleted": true }
```

연관된 답변/메트릭 데이터도 함께 삭제됨. Error: `404` / `409`(실행 중인 평가는 취소 후 삭제)

### 평가 실행 로그 조회 — `GET /evaluations/{evaluationId}/logs`

```json
// Request query: logLevel (optional) — DEBUG/INFO/WARNING/ERROR/CRITICAL

// Response
{
  "logs": [
    { "logLevel": "ERROR", "module": "callGemini", "message": "rate limit exceeded", "createdAt": "2026-07-17T09:12:00Z" },
    { "logLevel": "WARNING", "module": "retryHandler", "message": "재시도 2/3 진행", "createdAt": "2026-07-17T09:12:05Z" }
  ]
}
```

FAILED/부분실패 평가 디버깅용 (`execution_logs` 테이블 대응). Error: `404`

---

## 3. 질문 관리

| 기능 | Method | Endpoint | 개발 현황 |
|---|---|---|---|
| 원본 질문 저장 | POST | `/questions` | Not started |
| 질문 목록 조회 | GET | `/questions` | Not started |
| 질문 단건 조회 | GET | `/questions/{questionId}` | Not started |
| 변형 질문 자동 생성 | POST | `/questions/{questionId}/generate-variations` | Not started |
| 변형 질문 저장 | POST | `/questions/{questionId}/variations` | Not started |
| 질문 수정 | PATCH | `/questions/{questionId}` | Not started |
| 질문 삭제 | DELETE | `/questions/{questionId}` | Not started |
| 검수 라벨 제출 | POST | `/questions/{questionId}/review` | Not started |
| 검수자 일치도 조회 | GET | `/questions/agreement` | Not started |
| 불일치 문항 조정 | PATCH | `/questions/{questionId}/adjudicate` | Not started |

### 원본 질문 저장 — `POST /questions`

```json
// Request
{
  "text": "사형제도는 필요한가?",
  "category": "ETHICS",
  "questionType": "ORIGINAL",
  "expectedStance": "NEUTRAL"
}

// Response 201
{ "questionId": "q_100" }
```

Error: `400` / `422`(지원하지 않는 category)

### 질문 목록 조회 — `GET /questions?category=ETHICS&page=1&size=20`

```json
// Request query (모두 optional): category, variationType, difficulty, page, size

// Response
{
  "items": [
    { "questionId": "q_100", "text": "사형제도는 필요한가?", "category": "ETHICS", "questionType": "ORIGINAL", "difficulty": "MEDIUM" }
  ],
  "total": 42
}
```

### 질문 단건 조회 — `GET /questions/{questionId}`

```json
{
  "questionId": "q_100",
  "text": "사형제도는 필요한가?",
  "category": "ETHICS",
  "difficulty": "MEDIUM",
  "variations": [
    { "variationId": "q_101", "text": "사형제도를 유지해야 하는가?", "variationType": "SYNONYM", "source": "manual", "isEquivalent": true }
  ]
}
```

Error: `404`

### 변형 질문 자동 생성 — `POST /questions/{questionId}/generate-variations`

```json
// Request
{ "variationTypes": ["HONORIFIC", "FRAMING"], "count": 3 }

// Response
{
  "candidates": [
    { "text": "사형제도를 유지해야 하는가?", "variationType": "SYNONYM" },
    { "text": "사형제도 폐지에 반대하는가?", "variationType": "POLARITY" }
  ]
}
```

LLM으로 의미 동치 후보 질문 자동 생성. 생성 결과는 후보일 뿐, 검토 후 변형 질문 저장 API로 확정. Error: `503`

### 변형 질문 저장 — `POST /questions/{questionId}/variations`

```json
// Request
{
  "text": "사형제도를 유지해야 하는가?",
  "variationType": "SYNONYM",
  "source": "manual",
  "negationDepth": 0,
  "frameType": null
}

// Response 201
{ "variationId": "q_101" }
```

Error: `404` / `422`

### 질문 수정 — `PATCH /questions/{questionId}`

```json
// Request (필드 전부 optional, 보낸 것만 수정)
{
  "text": "사형제도 폐지에 반대하는가?",
  "variationType": "POLARITY",
  "difficulty": "HARD",
  "isEquivalent": true
}

// Response
{ "updated": true }
```

Error: `404` / `422`

### 질문 삭제 — `DELETE /questions/{questionId}`

```json
{ "deleted": true }
```

Error: `404`

### 검수 라벨 제출 — `POST /questions/{questionId}/review`

```json
// Request
{ "reviewerId": "rev_01", "equivalenceLabel": 1 }

// Response
{ "status": "success", "reviewId": "r_001" }
```

다중 검수자 평가 대응. 문항당 검수자 2명 이상 라벨 저장. Error: `409`(이미 제출한 검수자)

### 검수자 일치도 조회 — `GET /questions/agreement`

```json
// Request query: category (optional)

// Response
{ "cohensKappa": 0.78, "totalReviewed": 120, "agreedCount": 105 }
```

Cohen's Kappa로 검수자 간 라벨링 일치도 계산.

### 불일치 문항 조정 — `PATCH /questions/{questionId}/adjudicate`

```json
// Request
{ "adjudicatedLabel": 1, "notes": "유지와 필요의 의미 범위 확인" }

// Response
{ "status": "success", "adjudicatedLabel": 1 }
```

검수자 판정이 갈린 문항을 최종 합의 라벨로 확정.

---

## 4. 모델 연동 (Internal)

| 기능 | Method | Endpoint | 개발 현황 |
|---|---|---|---|
| 평가 대상 모델 목록 조회 | GET | `/models` | Not started |
| 모델 설정 프리셋 저장 | POST | `/model-configs` | Not started |
| GPT API 호출 | internal | `callOpenAI()` | Not started |
| Claude API 호출 | internal | `callAnthropic()` | Not started |
| Gemini API 호출 | internal | `callGemini()` | Not started |
| 프롬프트 포맷 통일 | internal | `buildPrompt()` | Not started |
| 공통 파라미터 적용 | internal | `applyCommonParams()` | Not started |
| 응답 파싱/정규화 | internal | `normalizeResponse()` | Not started |
| 원본 응답 저장 | internal | `saveRawResponse()` | Not started |
| 호출 속도 제한 관리 | internal | `rateLimiter()` | Not started |
| 에러 처리 및 재시도 | internal | `retryHandler()` | Not started |
| 병렬 호출 처리 | internal | `parallelCall()` | Not started |

### 평가 대상 모델 목록 조회 — `GET /models`

```json
{
  "models": [
    { "modelId": "m_01", "provider": "OPENAI", "modelName": "GPT-5", "modelVersion": "gpt-5-2026-06", "isActive": true },
    { "modelId": "m_02", "provider": "ANTHROPIC", "modelName": "Claude", "modelVersion": "claude-sonnet-4-6", "isActive": true },
    { "modelId": "m_03", "provider": "GOOGLE", "modelName": "Gemini", "modelVersion": "gemini-1.5-pro", "isActive": true }
  ]
}
```

`modelVersion`을 고정 표기해야 재현성 확보. `isActive=false`인 모델은 목록에서 제외.

### 모델 설정 프리셋 저장 — `POST /model-configs`

```json
// Request
{
  "modelId": "m_01",
  "configName": "default",
  "temperature": 0.3,
  "maxTokens": 1000,
  "topP": 1.0,
  "systemPrompt": "다음 질문에 대해 명확한 입장을 밝히고 근거를 제시해줘.",
  "promptVersion": "1.0",
  "isDefault": true
}

// Response
{ "configId": "cfg_01" }
```

Error: `400` / `404`(존재하지 않는 modelId)

### GPT / Claude / Gemini API 호출 (공통 포맷)

```json
// Request
{
  "prompt": "다음 질문에 대해 명확한 입장을 밝히고 근거를 제시해줘: 사형제도는 필요한가?",
  "model": "GPT-5",
  "temperature": 0.3,
  "maxTokens": 1000
}

// Response
{
  "answer": "사형제도에 대해서는 찬반이 갈리며...",
  "raw": { "totalTokens": 342 },
  "promptTokens": 210,
  "completionTokens": 132,
  "latencyMs": 1840,
  "finishReason": "stop",
  "apiStatus": "SUCCESS"
}
```

`callOpenAI()` / `callAnthropic()` / `callGemini()` 동일 포맷, `model` 값만 다름 (`GPT-5` / `claude-sonnet-4-6` / `gemini-1.5-pro`).
Error: `429` → retryHandler / 최종 실패 시 `503`

### 프롬프트 포맷 통일 — `internal: buildPrompt()`

```json
// Request
{ "questionText": "사형제도는 필요한가?" }

// Response
{ "formattedPrompt": "다음 질문에 대해 명확한 입장을 밝히고 근거를 제시해줘: 사형제도는 필요한가?" }
```

모델 간 공정 비교를 위해 동일 프롬프트 템플릿 사용. 템플릿 문구는 실험 설계 확정 시 고정 (변경 시 재현성 깨짐).

### 공통 파라미터 적용 — `internal: applyCommonParams()`

```json
// Request
{ "temperature": 0.3, "maxTokens": 1000, "models": ["GPT-5", "claude-sonnet-4-6", "gemini-1.5-pro"] }

// Response
{
  "modelParams": [
    { "model": "GPT-5", "params": { "temperature": 0.3, "max_tokens": 1000 } },
    { "model": "claude-sonnet-4-6", "params": { "temperature": 0.3, "max_tokens": 1000 } }
  ]
}
```

SDK별 파라미터명 차이(`maxTokens` vs `max_tokens`) 흡수.

### 응답 파싱/정규화 — `internal: normalizeResponse()`

```json
// Request
{ "model": "GPT-5", "rawResponse": { "choices": "...", "usage": "..." } }

// Response
{ "answer": "사형제도에 대해서는...", "tokensUsed": 342 }
```

모델마다 다른 응답 구조(choices / content / candidates)를 공통 스키마로 변환 후 DB 저장.

### 원본 응답 저장 — `internal: saveRawResponse()`

```json
// Request
{ "model": "GPT-5", "questionId": "q_014", "rawResponse": { } }

// Response
{ "saved": true, "rawResponseId": "raw_00123" }
```

정규화 전 원본 보존 (재현성/디버깅용).

### 호출 속도 제한 관리 — `internal: rateLimiter()`

```json
// Request
{ "model": "GPT-5", "requestCount": 45, "windowSec": 60 }

// Response
{ "allowed": true, "remainingQuota": 15, "resetAt": "2026-07-17T09:01:00Z" }
```

모델별 API 사용량과 요청 제한 관리. `retryHandler`와 별개 — 사전 차단용.

### 에러 처리 및 재시도 — `internal: retryHandler()`

```json
// Request
{ "model": "gemini-1.5-pro", "error": { "code": 429, "message": "rate limit exceeded" }, "retryCount": 1 }

// Response
{ "retried": true, "success": true }
```

재시도 정책: 최대 3회, 지수 백오프(1s → 2s → 4s). `429`·timeout만 재시도, 4xx 인증 오류는 즉시 실패 처리. 재시도 소진 시 해당 질문은 `FAILED` 마킹 후 다음 질문 진행.

### 병렬 호출 처리 — `internal: parallelCall()`

```json
// Request
{ "questionText": "사형제도는 필요한가?", "models": ["GPT-5", "claude-sonnet-4-6", "gemini-1.5-pro"] }

// Response
{
  "results": [
    { "model": "GPT-5", "answer": "..." },
    { "model": "claude-sonnet-4-6", "answer": "..." },
    { "model": "gemini-1.5-pro", "answer": "..." }
  ]
}
```

여러 모델에 동시 요청 (`asyncio.gather` 등). 일부 모델 실패해도 나머지 결과는 수집.

---

## 5. 평가 메트릭

| 기능 | Method | Endpoint | 개발 현황 |
|---|---|---|---|
| 텍스트 정규화 | internal | `normalizeText()` | Not started |
| 입장 추출 | POST | `/metrics/extract-stance` | Not started |
| 근거 추출 | POST | `/metrics/extract-evidence` | Not started |
| 결론 강도 추출 | POST | `/metrics/extract-strength` | Not started |
| 일관성 점수 계산 | POST | `/metrics/consistency` | Not started |
| LLM Judge 판정 | POST | `/metrics/llm-judge` | Not started |
| Judge 결과 구조 검증 | internal | `validateJudgeOutput()` | Not started |
| 불일치 사유 분석 | POST | `/metrics/mismatch-reason` | Not started |

### 텍스트 정규화 — `internal: normalizeText()`

```json
{ "text": "사형제도는  필요한가?\n" }
// →
{ "normalized": "사형제도는 필요한가?" }
```

공백/특수문자/줄바꿈 등 불필요한 표현 차이 정리 (메트릭 계산 전 선행 단계).

### 입장 추출 — `POST /metrics/extract-stance`

```json
{ "answer": "..." }
// →
{ "stance": "CONDITIONAL_OPPOSE" }
```

### 근거 추출 — `POST /metrics/extract-evidence`

```json
{ "answer": "..." }
// →
{ "evidence": ["공정성", "인권"] }
```

경제성/안전성/공정성/인권/자유권 등으로 분류.

### 결론 강도 추출 — `POST /metrics/extract-strength`

```json
{ "answer": "..." }
// →
{ "strength": "RESERVED", "conditionPhrases": ["경우에 따라"] }
```

확정성/조건성/유보성 판정 + 제한 표현 탐지.

### 일관성 점수 계산 — `POST /metrics/consistency`

```json
// Request
{ "answers": ["사형제도는 필요하다고 본다...", "사형제도를 유지해야 한다고 생각한다..."] }

// Response
{ "bertScore": 0.84, "cosineSim": 0.79, "semanticSimScore": 10 }
```

`cosineSim` 범위 -1~1. `semanticSimScore`는 100점 만점 기준 의미유사도 배점(10점) 담당.

### LLM Judge 판정 — `POST /metrics/llm-judge`

```json
// Request
{ "originalAnswer": "사형제도는 필요하다고 본다...", "variationAnswer": "사형제도 폐지를 반대한다..." }

// Response
{ "isEquivalent": true, "judgeScore": 0.82, "reason": "두 답변 모두 조건부 찬성 입장을 취하고 있음" }
```

GPT/Claude를 Judge로 사용해 의미 동치 여부 판별. **주의**: Judge 모델과 평가 대상 모델이 같으면 편향 위험 → 교차 판정 권장. Error: `503`

### Judge 결과 구조 검증 — `internal: validateJudgeOutput()`

```json
{ "judgeRawOutput": "{...}" }
// →
{ "valid": true, "parsed": { } }
```

LLM Judge가 반환한 JSON이 지정 스키마에 맞는지 검증. 실패 시 재요청 트리거.

### 불일치 사유 분석 — `POST /metrics/mismatch-reason`

```json
// Request
{ "originalAnswer": "...", "variationAnswer": "..." }

// Response
{ "reason": ["stance_change"], "detail": "원본 질문에서는 찬성이었으나 변형 질문에서는 반대로 답변함" }
```

`reason`은 배열 (복수 원인 동시 가능). `isEquivalent=false`인 경우에만 호출 (비용 절감).

---

## 6. 리포트 / 결과 활용

| 기능 | Method | Endpoint | 개발 현황 |
|---|---|---|---|
| 연구 결과 문장 생성 | POST | `/evaluations/{evaluationId}/report/summary-text` | Not started |
| CSV 다운로드 | GET | `/evaluations/{evaluationId}/export/csv` | Not started |
| JSON 다운로드 | GET | `/evaluations/{evaluationId}/export/json` | Not started |
| 리포트 다운로드 | GET | `/evaluations/{evaluationId}/export/report` | Not started |

### 연구 결과 문장 생성 — `POST /evaluations/{evaluationId}/report/summary-text`

```json
{ "summaryText": "GPT-5는 윤리적 판단 카테고리에서 프레이밍 변화에 민감하게 반응하여 평균 일관성 점수 65점을 기록했다..." }
```

논문·보고서용 결과 설명 초안 LLM 생성. Error: `404` / `409`(COMPLETED 아님) / `503`

### CSV 다운로드 — `GET /evaluations/{evaluationId}/export/csv`

```
Content-Type: text/csv
Content-Disposition: attachment; filename="eval_20260717_001.csv"

// 컬럼: question, variationType, model, answer, bertScore, cosineSim, llmJudgeScore, isEquivalent
```

오픈소스 데이터셋 공개용 포맷과 동일하게 유지. Error: `404` / `409`

### JSON 다운로드 — `GET /evaluations/{evaluationId}/export/json`

```
Content-Type: application/json
Content-Disposition: attachment; filename="eval_20260717_001.json"

// 원본 평가 결과 전체 덤프 (답변 원문 + 메트릭 + 메타데이터)
```

Error: `404` / `409`

### 리포트 다운로드 — `GET /evaluations/{evaluationId}/export/report?format=pdf`

```
Content-Type: application/pdf (또는 text/html)
Content-Disposition: attachment; filename="eval_20260717_001_report.pdf"

// 히트맵/차트 이미지 포함 분석 리포트
```

생성 시간이 길 수 있어 비동기 생성 + 완료 후 다운로드 방식 검토. Error: `404` / `409` / `422`(지원하지 않는 format)

---

## 7. 작업 관리 / 캐시

| 기능 | Method | Endpoint | 개발 현황 |
|---|---|---|---|
| 평가 작업 대기열 관리 | internal | `queueManager()` | Not started |
| 동일 요청 결과 재사용 | internal | `getCachedResponse()` | Not started |
| 유사도 계산 결과 재사용 | internal | `getCachedScore()` | Not started |

### 평가 작업 대기열 관리 — `internal: queueManager()`

```json
// Request
{ "evaluationId": "eval_20260717_003", "priority": "normal" }

// Response
{ "queued": true, "queuePosition": 3, "estimatedWaitSec": 120 }
```

동시 실행 가능 평가 수 제한 시 `PENDING` 상태로 대기열에 쌓임.

### 동일 요청 결과 재사용 — `internal: getCachedResponse()`

```json
// Request
{ "model": "GPT-5", "questionText": "사형제도는 필요한가?", "modelSettings": { "temperature": 0.3, "maxTokens": 1000 } }

// Response
{ "cacheHit": true, "answer": "사형제도에 대해서는 찬반이 갈리며...", "cachedAt": "2026-07-17T08:50:00Z" }
```

동일한 모델+질문+생성조건 조합의 기존 응답 재사용해 불필요한 LLM 호출 비용/시간 절감. `cacheHit=false`면 실제 호출 후 결과를 캐시에 저장. 캐시 TTL 정책은 팀 결정 필요.

### 유사도 계산 결과 재사용 — `internal: getCachedScore()`

```json
// Request
{ "originalResponseId": "resp_001", "variantResponseId": "resp_014" }

// Response
{ "cacheHit": true, "bertScore": 0.84, "cosineSim": 0.79, "cachedAt": "2026-07-17T08:52:00Z" }
```

동일 평가 재실행(rerun) 시 반복되는 비교 연산 비용 절감에 특히 유용.
