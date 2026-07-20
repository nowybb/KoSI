# KoSI (Korean Semantic Invariance)

> **Korean Semantic Invariance Benchmark**
>
> 한국어 LLM의 질문 표현 변화에 따른 의미 보존성(Semantic Invariance)과 답변 일관성을 평가하는 프로젝트입니다.

---

## 프로젝트 소개

KoSI는 동일한 의미를 가진 질문이라도 표현 방식(어순, 부정, 문체, 프레이밍 등)이 달라질 때 LLM이 얼마나 일관된 답변을 생성하는지 평가하는 벤치마크입니다.

기존의 LLM 평가는 대부분 **정확도(Accuracy)** 중심이지만, KoSI는 **강건성(Robustness)** 과 **의미 보존성(Semantic Invariance)** 을 중심으로 평가합니다.

---

## 프로젝트 목표

- 한국어 의미 보존 질문 데이터셋 구축
- GPT, Claude, Gemini 답변 비교
- 표현 변화에 따른 답변 일관성 분석
- Consistency Score 제안
- Framing Sensitivity Score 제안
- 한국어 LLM 의미 보존성 벤치마크 구축

---

## 주요 기능

- 질문 데이터셋 관리
- 자동 패러프레이즈 생성
- 의미 동치 검증
- GPT / Claude / Gemini 응답 생성
- BERTScore 계산
- Sentence Embedding Cosine Similarity 계산
- LLM-as-Judge 평가
- Consistency Score 계산
- Framing Sensitivity Score 계산
- 모델별 비교 및 시각화

---

# 데이터셋 구성

## 질문 카테고리 (5개)

KoSI 데이터셋은 다양한 의미 영역을 반영하기 위해 다음의 5개 질문 카테고리로 구성됩니다.

| 카테고리 | 포함 내용 |
|----------|----------|
| **정치·사회** | 제도, 정책, 복지, 교육, 노동, 사회 문제 |
| **경제** | 세금, 최저임금, 기본소득, 소비, 기업, 규제 |
| **과학·기술** | 과학 지식, 인공지능, 환경, 의료기술, 기술윤리 |
| **윤리·가치** | 공정성, 자유, 책임, 생명, 권리, 도덕적 판단 |
| **일상·문화** | 학교생활, 직장, 인간관계, 미디어, 여가, 문화생활 |

---

# 데이터셋 규모

| 항목 | 수량 |
|------|------:|
| 질문 카테고리 | 5개 |
| 카테고리별 원본 질문 | 50개 |
| 전체 원본 질문 | 250개 (5 × 50) |
| 원본 질문당 의미 동치 변형 | 8개 |
| 전체 의미 동치 변형 질문 | 2,000개 (250 × 8) |
| 원본 및 변형 포함 전체 질문 수 | 2,250개 (250 + 2,000) |

---

# 질문 유형 구성

각 카테고리는 다음의 5가지 질문 유형으로 균등하게 구성됩니다.

| 질문 유형 | 카테고리별 수량 | 예시 |
|-----------|:-------------:|------|
| **사실·지식 판단형** | 10개 | 대통령의 임기는 몇 년인가?<br>국민투표는 헌법 개정에 활용될 수 있는가?<br>국회의원의 임기는 몇 년인가? |
| **찬반·입장 판단형** | 10개 | 선거 연령을 만 16세로 낮춰야 하는가?<br>기본소득을 도입해야 하는가?<br>의무투표제를 시행해야 하는가? |
| **원인·이유 설명형** | 10개 | 저출산 문제가 심화되는 이유는 무엇인가?<br>청년 실업률이 높은 이유는 무엇인가?<br>복지 지출이 증가하는 원인은 무엇인가? |
| **비교·선택형** | 10개 | 대통령제와 의원내각제 중 어느 제도가 더 안정적인가?<br>직접민주주의와 간접민주주의의 차이는 무엇인가?<br>무상복지와 선별복지 중 어느 정책이 효과적인가? |
| **조건·상황 판단형** | 10개 | 고령화가 더욱 심해진다면 정년을 연장해야 하는가?<br>국가 재정이 부족하다면 복지 예산을 축소해야 하는가?<br>투표율이 계속 감소한다면 의무투표제를 도입해야 하는가? |

---

# 의미 동치 변형 유형

각 원본 질문은 의미를 유지한 상태에서 다음의 8가지 변형 유형을 적용하여 의미 동치 질문을 생성합니다.

| 변형 유형 | 설명 | 예시 |
|-----------|------|------|
| **동의어 교체 (SYNONYM)** | 핵심 단어를 의미가 같은 표현으로 변경 | "필요하다" → "요구된다" |
| **어순 변경 (WORD_ORDER)** | 문장의 어순이나 구조를 변경 | "정부는 규제를 강화해야 하는가?" → "규제를 강화해야 하는가, 정부는?" |
| **문체 변경 (STYLE)** | 종결어미 및 문체를 변경 | "~해야 하는가?" → "~해야 할까요?" |
| **긍·부정 변환 (POLARITY)** | 의미를 유지하면서 긍정과 부정 표현을 변환 | "환경 보호가 중요하다." → "환경 보호를 소홀히 해서는 안 된다." |
| **능동·수동 변환 (VOICE)** | 능동문과 수동문을 상호 변환 | "정부가 정책을 시행했다." → "정책이 정부에 의해 시행되었다." |
| **중첩 부정 (DOUBLE_NEGATION)** | 이중 부정을 활용하여 의미를 유지 | "도입해야 한다." → "도입하지 않을 이유가 없다." |
| **높임법 변경 (HONORIFIC)** | 존댓말, 반말, 격식체 등 높임 표현을 변경 | "~합니까?" → "~하나요?" |
| **프레이밍 변화 (FRAMING)** | 동일한 의미를 다른 관점이나 맥락에서 표현 | "원자력 발전을 확대해야 하는가?" → "탄소 배출을 줄이기 위해 원자력 발전을 확대해야 하는가?" |

---

# 데이터셋 생성 절차

1. 카테고리별 원본 질문 250개를 작성한다.
2. 각 질문을 5가지 질문 유형에 맞게 균등하게 구성한다.
3. 원본 질문마다 8가지 의미 동치 변형 유형을 적용하여 질문을 생성한다.
4. 생성된 질문에 대해 의미 동치 여부를 검증한다.
5. 최종적으로 원본 질문 250개와 의미 동치 변형 질문 2,000개를 포함한 총 2,250개의 질문 데이터셋을 구축한다.

---

## 기술 스택

### Backend

- Python
- FastAPI

### Frontend

- Streamlit
- Plotly

### LLM

- OpenAI API
- Anthropic API
- Google Gemini API

### Evaluation

- BERTScore
- Sentence Transformers
- LLM-as-Judge

### Data

- Pandas
- CSV
- JSON

---

## 실행 과정

```text
질문 입력
      ↓
패러프레이즈 생성
      ↓
의미 동치 검증
      ↓
GPT / Claude / Gemini 응답 생성
      ↓
답변 분석
      ↓
BERTScore
      ↓
Cosine Similarity
      ↓
LLM-as-Judge
      ↓
Consistency Score 계산
      ↓
Framing Sensitivity 계산
      ↓
결과 시각화
```

---

## 프로젝트 구조

```
KoSI/
│
├── README.md
├── requirements.txt           # 프로젝트에서 사용하는 Python 라이브러리 목록
├── .env.example               # OpenAI, Claude, Gemini API Key 저장 예시
├── .gitignore
│
├── app.py                     # Streamlit 실행 파일
│
├── frontend/                  # 프론트엔드
│   ├── pages/
│   │   ├── home.py            # 메인 화면
│   │   ├── evaluate.py        # 평가 실행
│   │   ├── result.py          # 결과 조회
│   │   └── history.py         # 실행 이력
│   │
│   ├── components/
│   │   ├── sidebar.py         # 사이드바 UI
│   │   ├── charts.py          # Plotly 그래프 생성
│   │   └── table.py           # 결과 테이블 생성
│   │
│   └── assets/
│       └── logo.png           # 프로젝트 로고 및 이미지
│
├── backend/                   # 백엔드
│   ├── main.py
│   │
│   ├── api/
│   │   ├── evaluation.py      # 평가 실행 API
│   │   ├── dataset.py         # 질문 데이터셋 관리 API
│   │   ├── result.py          # 평가 결과 조회 API
│   │   └── history.py         # 실행 이력 조회 API
│   │
│   ├── services/
│   │   ├── openai_service.py   # GPT API 호출
│   │   ├── claude_service.py   # Claude API 호출
│   │   ├── gemini_service.py   # Gemini API 호출
│   │   ├── paraphrase_service.py  # 질문 패러프레이즈 생성
│   │   ├── judge_service.py    # LLM-as-Judge 평가
│   │   └── scoring_service.py  # Consistency Score 계산
│   │
│   ├── database/
│   │   ├── database.py         # DB 연결
│   │   ├── models.py           # DB 테이블 모델 정의
│   │   └── crud.py             # DB 저장·조회·수정·삭제
│   │   └── migration.py        # DB 스키마 생성(테이블 최초 생성)
(CRUD)
│   │
│   └── utils/
│       ├── logger.py           # 로그 관리
│       └── config.py           # 환경변수 및 설정 관리
│
├── evaluation/                # 평가 알고리즘
│   ├── bertscore.py           # BERTScore 계산
│   ├── embedding.py           # Sentence Embedding 및 Cosine Similarity 계산
│   ├── llm_judge.py           # GPT를 이용한 답변 비교 평가
│   ├── consistency.py         # 최종 Consistency Score 계산
│   └── framing.py             # Framing Sensitivity Score 계산
│
├── dataset/
│   ├── original/              # 원본 질문 데이터셋
│   ├── paraphrase/            # 생성된 패러프레이즈 질문
│   ├── validated/             # 검수 완료된 질문 데이터셋
│   └── sample_dataset.csv     # 예시 데이터셋
│
├── results/
│   ├── responses/             # GPT, Claude, Gemini 원본 응답 저장
│   ├── scores/                # 계산된 점수 저장
│   └── reports/               # CSV, JSON, 리포트 저장
│
├── docs/
│   ├── 기능명세서.md
│   ├── API명세서.md
│   ├── AI모델명세서.md
│   └── DB설계서.md
│
└── tests/
    ├── test_api.py            # API 테스트
    ├── test_scoring.py        # 점수 계산 테스트
    ├── test_model.py          # GPT·Claude·Gemini 연동 테스트
    └── test_dataset.py        # 데이터셋 검증 테스트
```

---

## 실행 방법

### 저장소 복제

```bash
git clone https://github.com/nowybb/KoSI.git
cd KoSI
```

### 패키지 설치

```bash
pip install -r requirements.txt
```

### 환경 변수 설정

`.env`

```env
OPENAI_API_KEY=YOUR_KEY
ANTHROPIC_API_KEY=YOUR_KEY
GEMINI_API_KEY=YOUR_KEY
```

### Backend 실행

backend 디렉터리로 이동

```bash
cd backend
```

필요한 패키지 설치

```bash
pip install -r requirements.txt
```

서버 실행

```bash
uvicorn app.main:app --reload
```

기본 주소

```
http://localhost:8000
```

### Frontend 실행

frontend 디렉터리로 이동

```bash
cd frontend
```

필요한 패키지 설치

```bash
npm install
```

서버 실행

```bash
npm run dev
```

기본 주소

```
http://localhost:5173
```

---

## 연구 기여

- 한국어 의미 보존성 데이터셋 구축
- 한국어 LLM 일관성 평가 프레임워크 제안
- Consistency Score 제안
- Framing Sensitivity Score 제안
- 모델별 의미 보존 능력 비교 분석

---

## Team

곽다희
```
https://github.com/dahui7072
```

나연우
```
https://github.com/nowybb
```
