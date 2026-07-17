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

## 질문 카테고리

- 단순 사실 (Fact)
- 논리 추론 (Logical Reasoning)
- 윤리·가치 판단 (Ethical Reasoning)
- 중첩 부정 (Nested Negation)
- 한국 사회 특화 (Korean Context)
- 프레이밍 효과 (Framing Effect)

---

## 평가 항목

| 항목 | 비중 |
|------|------:|
| 입장 일치도 | 40% |
| 결론 일치도 | 20% |
| 근거 일치도 | 20% |
| 결론 강도 | 10% |
| 의미 유사도 | 10% |

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

## 📁 프로젝트 구조

추후 기재

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

추후 기재

### Frontend 실행

추후 기재

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
https://github.com/dahui7072

나연우
https://github.com/nowybb
