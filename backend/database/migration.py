# backend/database/migration.py
# DB 초기 생성

"""
KoSI (Korean Semantic Invariance Benchmark) - DB 스키마 생성 스크립트

실행: python migration.py
- kosi.db 파일을 새로 생성/초기화한다.
- 기존 파일이 있으면 --reset 옵션으로 삭제 후 재생성 가능.

테이블 목록:
    1. evaluations           평가 작업 기본 정보/상태
    2. questions             원본/변형 질문 (마스터 데이터셋, 평가와 독립)
    3. evaluation_questions   평가 ↔ 질문 매핑 (M:N)
    4. models                평가 대상 LLM 모델
    5. model_configs         모델별 생성 설정 프리셋
    6. evaluation_models     평가 ↔ 모델(+설정) 매핑
    7. responses             모델 답변 원본
    8. analysis_results      답변 구조화 분석 결과 (1:1 with responses)
    9. comparison_scores     원본-변형 답변 비교 점수
    10. execution_logs       평가 실행 로그
    11. reports              평가 리포트 산출물

설계 근거:
    - DB_설계서.pdf 의 10개 테이블 구조를 기반으로 하되,
    dataset 구조 재설계(domain × question_form × variation_type)에 맞춰
    questions 테이블의 category 컬럼을 domain/question_form으로 분리했다.
    - questions 는 평가 실행 이전에 미리 구축되는 고정 데이터셋(2,250문항)이므로
    evaluation_id FK를 questions에서 제거하고, evaluation_questions 매핑
    테이블을 신설해 "이 평가에 어떤 질문들을 사용했는지"를 기록한다.
"""

import sqlite3
import argparse
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "kosi.db")

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

-- 1. evaluations : 평가 작업 기본 정보
CREATE TABLE IF NOT EXISTS evaluations (
    evaluation_id       TEXT PRIMARY KEY,
    title               TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'PENDING'
                        CHECK (status IN ('PENDING','RUNNING','ANALYZING','COMPLETED','FAILED','CANCELLED')),
    variation_types     TEXT,              -- JSON 배열 (예: ["SYNONYM","POLARITY"])
    variation_count     INTEGER,
    max_question_length INTEGER,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    started_at          TEXT,
    completed_at        TEXT,
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_evaluations_status ON evaluations(status);
CREATE INDEX IF NOT EXISTS idx_evaluations_created_at ON evaluations(created_at);

-- 2. questions : 원본/변형 질문 (마스터 데이터셋)
CREATE TABLE IF NOT EXISTS questions (
    question_id            TEXT PRIMARY KEY,
    parent_question_id     TEXT,               -- 변형 질문일 경우 원본 질문 ID
    question_text          TEXT NOT NULL,
    question_type          TEXT NOT NULL
                        CHECK (question_type IN ('ORIGINAL','VARIANT','FRAMING','NON_EQUIVALENT')),
    domain                  TEXT NOT NULL
                        CHECK (domain IN ('POLITICS_SOCIETY','ECONOMY','SCIENCE_TECH','ETHICS_VALUES','DAILY_CULTURE')),
    question_form           TEXT NOT NULL
                        CHECK (question_form IN ('FACT_JUDGMENT','STANCE_JUDGMENT','CAUSE_EXPLANATION','COMPARISON_CHOICE','CONDITION_JUDGMENT')),
    variation_type          TEXT
                        CHECK (variation_type IS NULL OR variation_type IN
                                ('SYNONYM','WORD_ORDER','STYLE','POLARITY','VOICE','DOUBLE_NEGATION','HONORIFIC','FRAMING')),
    equivalence_label       INTEGER,            -- 0/1, NULL = 미검증
    equivalence_confidence  REAL,
    difficulty              TEXT NOT NULL DEFAULT 'MEDIUM'
                        CHECK (difficulty IN ('EASY','MEDIUM','HARD')),
    negation_depth          INTEGER NOT NULL DEFAULT 0,
    frame_type              TEXT,
    expected_stance         TEXT
                        CHECK (expected_stance IS NULL OR expected_stance IN
                                ('SUPPORT','OPPOSE','NEUTRAL','CONDITIONAL_SUPPORT','CONDITIONAL_OPPOSE','UNDETERMINED')),
    source                  TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('auto','manual')),
    is_active               INTEGER NOT NULL DEFAULT 1,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (parent_question_id) REFERENCES questions(question_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_questions_parent_id ON questions(parent_question_id);
CREATE INDEX IF NOT EXISTS idx_questions_domain ON questions(domain);
CREATE INDEX IF NOT EXISTS idx_questions_question_form ON questions(question_form);
CREATE INDEX IF NOT EXISTS idx_questions_variation_type ON questions(variation_type);

-- 3. evaluation_questions : 평가 ↔ 질문 매핑 (M:N)
CREATE TABLE IF NOT EXISTS evaluation_questions (
    evaluation_question_id TEXT PRIMARY KEY,
    evaluation_id           TEXT NOT NULL,
    question_id             TEXT NOT NULL,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(evaluation_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE,
    UNIQUE (evaluation_id, question_id)
);
CREATE INDEX IF NOT EXISTS idx_eval_questions_evaluation_id ON evaluation_questions(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_eval_questions_question_id ON evaluation_questions(question_id);

-- 4. models : 평가 대상 LLM 모델
CREATE TABLE IF NOT EXISTS models (
    model_id        TEXT PRIMARY KEY,
    provider        TEXT NOT NULL CHECK (provider IN ('OPENAI','ANTHROPIC','GOOGLE')),
    model_name      TEXT NOT NULL,
    model_version   TEXT NOT NULL,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 5. model_configs : 모델별 생성 설정 프리셋
CREATE TABLE IF NOT EXISTS model_configs (
    config_id       TEXT PRIMARY KEY,
    model_id        TEXT NOT NULL,
    config_name     TEXT NOT NULL,
    temperature     REAL NOT NULL DEFAULT 0.3,
    max_tokens      INTEGER NOT NULL DEFAULT 1000,
    top_p           REAL NOT NULL DEFAULT 1.0,
    system_prompt   TEXT,
    prompt_version  TEXT NOT NULL DEFAULT '1.0',
    is_default      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (model_id) REFERENCES models(model_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_model_configs_model_id ON model_configs(model_id);

-- 6. evaluation_models : 평가 ↔ 모델(+설정) 매핑
CREATE TABLE IF NOT EXISTS evaluation_models (
    evaluation_model_id TEXT PRIMARY KEY,
    evaluation_id       TEXT NOT NULL,
    model_id            TEXT NOT NULL,
    config_id           TEXT,
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(evaluation_id) ON DELETE CASCADE,
    FOREIGN KEY (model_id) REFERENCES models(model_id) ON DELETE CASCADE,
    FOREIGN KEY (config_id) REFERENCES model_configs(config_id) ON DELETE SET NULL,
    UNIQUE (evaluation_id, model_id)
);
CREATE INDEX IF NOT EXISTS idx_eval_models_evaluation_id ON evaluation_models(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_eval_models_model_id ON evaluation_models(model_id);

-- 7. responses : 모델 답변 원본
CREATE TABLE IF NOT EXISTS responses (
    response_id         TEXT PRIMARY KEY,
    evaluation_id        TEXT NOT NULL,
    question_id           TEXT NOT NULL,
    model_id              TEXT NOT NULL,
    config_id             TEXT,
    response_text         TEXT NOT NULL,
    raw_response          TEXT,           -- JSON
    prompt_tokens         INTEGER,
    completion_tokens     INTEGER,
    latency_ms            INTEGER,
    finish_reason         TEXT,
    api_status            TEXT NOT NULL DEFAULT 'SUCCESS' CHECK (api_status IN ('SUCCESS','FAILED','TIMEOUT')),
    error_message         TEXT,
    created_at            TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(evaluation_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE,
    FOREIGN KEY (model_id) REFERENCES models(model_id),
    FOREIGN KEY (config_id) REFERENCES model_configs(config_id)
);
CREATE INDEX IF NOT EXISTS idx_responses_evaluation_id ON responses(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_responses_question_id ON responses(question_id);
CREATE INDEX IF NOT EXISTS idx_responses_model_id ON responses(model_id);

-- 8. analysis_results : 답변 구조화 분석 결과 (1:1 with responses)
CREATE TABLE IF NOT EXISTS analysis_results (
    analysis_id             TEXT PRIMARY KEY,
    response_id             TEXT NOT NULL UNIQUE,
    stance                  TEXT NOT NULL
                            CHECK (stance IN ('SUPPORT','OPPOSE','NEUTRAL','CONDITIONAL_SUPPORT','CONDITIONAL_OPPOSE','UNDETERMINED')),
    conclusion               TEXT NOT NULL,
    rationale                 TEXT,          -- JSON 배열
    rationale_categories       TEXT,          -- JSON 배열
    strength                  TEXT NOT NULL
                            CHECK (strength IN ('STRONG','MODERATE','CONDITIONAL','RESERVED','UNDETERMINED')),
    conditional_expression     TEXT,
    judge_confidence           REAL,
    created_at                 TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (response_id) REFERENCES responses(response_id) ON DELETE CASCADE
);

-- 9. comparison_scores : 원본-변형 답변 비교 점수
CREATE TABLE IF NOT EXISTS comparison_scores (
    score_id                TEXT PRIMARY KEY,
    evaluation_id            TEXT NOT NULL,
    original_response_id      TEXT NOT NULL,
    variant_response_id       TEXT NOT NULL,
    stance_score              REAL,
    conclusion_score          REAL,
    rationale_score           REAL,
    strength_score            REAL,
    bert_score                REAL CHECK (bert_score IS NULL OR (bert_score >= 0 AND bert_score <= 1)),
    cosine_similarity         REAL CHECK (cosine_similarity IS NULL OR (cosine_similarity >= -1 AND cosine_similarity <= 1)),
    consistency_score         REAL CHECK (consistency_score IS NULL OR (consistency_score >= 0 AND consistency_score <= 100)),
    framing_sensitivity       REAL CHECK (framing_sensitivity IS NULL OR (framing_sensitivity >= 0 AND framing_sensitivity <= 100)),
    mismatch_reasons          TEXT,          -- JSON 배열
    created_at                TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(evaluation_id) ON DELETE CASCADE,
    FOREIGN KEY (original_response_id) REFERENCES responses(response_id) ON DELETE CASCADE,
    FOREIGN KEY (variant_response_id) REFERENCES responses(response_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_comparison_scores_evaluation_id ON comparison_scores(evaluation_id);

-- 10. execution_logs : 평가 실행 로그
CREATE TABLE IF NOT EXISTS execution_logs (
    log_id          TEXT PRIMARY KEY,
    evaluation_id   TEXT NOT NULL,
    log_level       TEXT NOT NULL CHECK (log_level IN ('INFO','WARNING','ERROR','CRITICAL')),
    module          TEXT NOT NULL,
    message         TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(evaluation_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_execution_logs_evaluation_id ON execution_logs(evaluation_id);

-- 11. reports : 평가 리포트 산출물
CREATE TABLE IF NOT EXISTS reports (
    report_id       TEXT PRIMARY KEY,
    evaluation_id   TEXT NOT NULL,
    summary         TEXT,
    file_type       TEXT NOT NULL CHECK (file_type IN ('CSV','JSON','PDF','HTML')),
    file_path       TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(evaluation_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_reports_evaluation_id ON reports(evaluation_id);
"""


def create_schema(db_path: str = DB_PATH, reset: bool = False) -> None:
    if reset and os.path.exists(db_path):
        os.remove(db_path)
        print(f"[migration] 기존 DB 삭제: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        print(f"[migration] 스키마 생성 완료: {db_path}")

        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cur.fetchall() if not row[0].startswith("sqlite_")]
        print(f"[migration] 생성된 테이블 ({len(tables)}개): {', '.join(tables)}")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KoSI DB 스키마 생성")
    parser.add_argument("--reset", action="store_true", help="기존 DB 파일 삭제 후 재생성")
    parser.add_argument("--db-path", default=DB_PATH, help="DB 파일 경로 (기본: backend/database/kosi.db)")
    args = parser.parse_args()

    create_schema(db_path=args.db_path, reset=args.reset)