"""
backend/database/migration.py
DB 초기 테이블 생성 스크립트
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "kosi.db")

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS evaluations (
    evaluation_id       TEXT PRIMARY KEY,
    title               VARCHAR(200) NOT NULL,
    description         TEXT,
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                        CHECK (status IN ('PENDING','RUNNING','ANALYZING','COMPLETED','FAILED','CANCELLED')),
    total_questions     INTEGER NOT NULL DEFAULT 0,
    completed_responses INTEGER NOT NULL DEFAULT 0,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at          DATETIME,
    completed_at        DATETIME,
    updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evaluations_status ON evaluations(status);
CREATE INDEX IF NOT EXISTS idx_evaluations_created_at ON evaluations(created_at);

CREATE TABLE IF NOT EXISTS questions (
    question_id             TEXT PRIMARY KEY,
    evaluation_id           TEXT,
    parent_question_id      TEXT,
    question_text           TEXT NOT NULL,
    question_type           VARCHAR(20) NOT NULL
                            CHECK (question_type IN ('ORIGINAL','VARIANT','FRAMING','NON_EQUIVALENT')),
    category                VARCHAR(50) NOT NULL
                            CHECK (category IN ('FACT','LOGIC','ETHICS','NEGATION','KOREAN_CONTEXT','FRAMING')),
    variation_type          VARCHAR(50)
                            CHECK (variation_type IN ('SYNONYM','WORD_ORDER','STYLE','POLARITY','VOICE','NEGATION','HONORIFIC','FRAMING')),
    equivalence_label       BOOLEAN,
    equivalence_confidence  FLOAT CHECK (equivalence_confidence IS NULL OR (equivalence_confidence >= 0 AND equivalence_confidence <= 1)),
    difficulty              VARCHAR(20) NOT NULL DEFAULT 'NORMAL'
                            CHECK (difficulty IN ('EASY','NORMAL','MEDIUM','HARD')),
    negation_depth          INTEGER NOT NULL DEFAULT 0 CHECK (negation_depth >= 0),
    frame_type              VARCHAR(50),
    expected_stance         VARCHAR(30),
    is_active               BOOLEAN NOT NULL DEFAULT 1,
    created_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (evaluation_id) REFERENCES evaluations(evaluation_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_question_id) REFERENCES questions(question_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_questions_evaluation_id ON questions(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_questions_parent_id ON questions(parent_question_id);
CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category);
CREATE INDEX IF NOT EXISTS idx_questions_variation_type ON questions(variation_type);
CREATE INDEX IF NOT EXISTS idx_questions_eval_category ON questions(evaluation_id, category);

CREATE TABLE IF NOT EXISTS models (
    model_id       TEXT PRIMARY KEY,
    provider       VARCHAR(50) NOT NULL,
    model_name     VARCHAR(100) NOT NULL,
    model_version  VARCHAR(150) NOT NULL,
    description    TEXT,
    is_active      BOOLEAN NOT NULL DEFAULT 1,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (provider, model_version)
);

CREATE TABLE IF NOT EXISTS model_configs (
    config_id       TEXT PRIMARY KEY,
    model_id        TEXT NOT NULL,
    config_name     VARCHAR(100) NOT NULL,
    temperature     FLOAT NOT NULL DEFAULT 0.0 CHECK (temperature >= 0 AND temperature <= 2),
    max_tokens      INTEGER NOT NULL DEFAULT 1000 CHECK (max_tokens >= 1),
    top_p           FLOAT,
    system_prompt   TEXT NOT NULL,
    prompt_version  VARCHAR(30) NOT NULL DEFAULT '1.0',
    is_default      BOOLEAN NOT NULL DEFAULT 0,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_id) REFERENCES models(model_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evaluation_models (
    evaluation_model_id  TEXT PRIMARY KEY,
    evaluation_id        TEXT NOT NULL,
    model_id             TEXT NOT NULL,
    config_id            TEXT NOT NULL,
    status               VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(evaluation_id) ON DELETE CASCADE,
    FOREIGN KEY (model_id) REFERENCES models(model_id),
    FOREIGN KEY (config_id) REFERENCES model_configs(config_id),
    UNIQUE (evaluation_id, model_id)
);

CREATE TABLE IF NOT EXISTS responses (
    response_id         TEXT PRIMARY KEY,
    evaluation_id       TEXT NOT NULL,
    question_id         TEXT NOT NULL,
    model_id            TEXT NOT NULL,
    config_id           TEXT NOT NULL,
    response_text       TEXT NOT NULL,
    raw_response        JSON,
    prompt_tokens       INTEGER CHECK (prompt_tokens IS NULL OR prompt_tokens >= 0),
    completion_tokens   INTEGER CHECK (completion_tokens IS NULL OR completion_tokens >= 0),
    latency_ms          INTEGER,
    finish_reason       VARCHAR(50),
    api_status          VARCHAR(20) NOT NULL DEFAULT 'SUCCESS',
    error_message       TEXT,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(evaluation_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id),
    FOREIGN KEY (model_id) REFERENCES models(model_id),
    FOREIGN KEY (config_id) REFERENCES model_configs(config_id),
    UNIQUE (evaluation_id, question_id, model_id)
);

CREATE INDEX IF NOT EXISTS idx_responses_evaluation_id ON responses(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_responses_question_id ON responses(question_id);
CREATE INDEX IF NOT EXISTS idx_responses_model_id ON responses(model_id);
CREATE INDEX IF NOT EXISTS idx_responses_eval_model ON responses(evaluation_id, model_id);

CREATE TABLE IF NOT EXISTS analysis_results (
    analysis_id             TEXT PRIMARY KEY,
    response_id             TEXT NOT NULL UNIQUE,
    stance                  VARCHAR(30) NOT NULL
                            CHECK (stance IN ('SUPPORT','OPPOSE','NEUTRAL','CONDITIONAL_SUPPORT','CONDITIONAL_OPPOSE','UNDETERMINED')),
    conclusion               TEXT NOT NULL,
    rationale                JSON,
    rationale_categories      JSON,
    strength                 VARCHAR(30) NOT NULL
                            CHECK (strength IN ('STRONG','MODERATE','CONDITIONAL','RESERVED','UNDETERMINED')),
    conditional_expression   TEXT,
    judge_confidence          FLOAT CHECK (judge_confidence IS NULL OR (judge_confidence >= 0 AND judge_confidence <= 1)),
    judge_raw_result         JSON,
    created_at               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (response_id) REFERENCES responses(response_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_analysis_response_id ON analysis_results(response_id);

CREATE TABLE IF NOT EXISTS comparison_scores (
    score_id              TEXT PRIMARY KEY,
    evaluation_id         TEXT NOT NULL,
    model_id              TEXT NOT NULL,
    original_response_id  TEXT NOT NULL,
    variant_response_id   TEXT NOT NULL,
    stance_score          FLOAT NOT NULL DEFAULT 0,
    conclusion_score      FLOAT NOT NULL DEFAULT 0,
    rationale_score       FLOAT NOT NULL DEFAULT 0,
    strength_score        FLOAT NOT NULL DEFAULT 0,
    bert_score            FLOAT CHECK (bert_score IS NULL OR (bert_score >= 0 AND bert_score <= 1)),
    cosine_similarity     FLOAT CHECK (cosine_similarity IS NULL OR (cosine_similarity >= -1 AND cosine_similarity <= 1)),
    semantic_score        FLOAT NOT NULL DEFAULT 0,
    llm_judge_score       FLOAT,
    consistency_score     FLOAT NOT NULL DEFAULT 0 CHECK (consistency_score >= 0 AND consistency_score <= 100),
    framing_sensitivity   FLOAT CHECK (framing_sensitivity IS NULL OR (framing_sensitivity >= 0 AND framing_sensitivity <= 100)),
    mismatch_reason       JSON,
    created_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(evaluation_id) ON DELETE CASCADE,
    FOREIGN KEY (model_id) REFERENCES models(model_id),
    FOREIGN KEY (original_response_id) REFERENCES responses(response_id),
    FOREIGN KEY (variant_response_id) REFERENCES responses(response_id),
    UNIQUE (original_response_id, variant_response_id, model_id)
);

CREATE INDEX IF NOT EXISTS idx_scores_evaluation_id ON comparison_scores(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_scores_model_id ON comparison_scores(model_id);
CREATE INDEX IF NOT EXISTS idx_scores_consistency ON comparison_scores(consistency_score);
CREATE INDEX IF NOT EXISTS idx_scores_eval_model ON comparison_scores(evaluation_id, model_id);
CREATE INDEX IF NOT EXISTS idx_scores_eval_consistency ON comparison_scores(evaluation_id, consistency_score);

CREATE TABLE IF NOT EXISTS reports (
    report_id      TEXT PRIMARY KEY,
    evaluation_id  TEXT NOT NULL,
    report_type    VARCHAR(30) NOT NULL CHECK (report_type IN ('CSV','JSON','PDF','HTML')),
    summary        TEXT,
    insights       JSON,
    file_path      VARCHAR(500),
    file_name      VARCHAR(255),
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(evaluation_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS execution_logs (
    log_id         TEXT PRIMARY KEY,
    evaluation_id  TEXT,
    response_id    TEXT,
    log_level      VARCHAR(20) NOT NULL DEFAULT 'INFO'
                CHECK (log_level IN ('DEBUG','INFO','WARNING','ERROR','CRITICAL')),
    module         VARCHAR(100) NOT NULL,
    message        TEXT NOT NULL,
    details        JSON,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(evaluation_id) ON DELETE CASCADE,
    FOREIGN KEY (response_id) REFERENCES responses(response_id)
);

CREATE INDEX IF NOT EXISTS idx_logs_evaluation_id ON execution_logs(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_logs_level ON execution_logs(log_level);
"""


def run_migration():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    print(f"✅ DB 스키마 생성 완료: {DB_PATH}")


if __name__ == "__main__":
    run_migration()