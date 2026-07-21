# backend/database/crud.py
# DB 저장·조회·수정·삭제(CRUD)

"""
KoSI - 질문(questions) CRUD

역할:
    - questions 테이블에 대한 생성/조회/목록/수정/삭제 로직을 담당한다.
    - dataset_api.py(FastAPI 엔드포인트)는 이 파일의 함수들을 그대로 호출해서 쓴다.
    - DB 연결은 database.py, 데이터 형태 검증은 models.py에 위임한다.

API명세서.md 대응 관계:
    create_question           -> POST /questions            (원본 질문 저장)
    create_variation           -> POST /questions/{id}/variations (변형 질문 저장)
    get_question               -> GET  /questions/{id}       (질문 단건 조회, 변형 목록 포함)
    list_questions              -> GET  /questions            (질문 목록 조회, 필터+페이징)
    update_question             -> PATCH /questions/{id}      (질문 수정)
    delete_question             -> DELETE /questions/{id}     (질문 삭제)
"""

from typing import Optional
import sqlite3

from database import DatabaseSession, get_connection, gen_id
from models import Question


class QuestionNotFoundError(Exception):
    """존재하지 않는 question_id를 조회/수정/삭제하려 할 때."""
    pass


# ---------------------------------------------------------------------------
# 생성
# ---------------------------------------------------------------------------

def create_question(question: Question) -> str:
    """
    원본 질문(question_type='ORIGINAL')을 저장한다.
    question.question_id가 비어 있으면 자동 생성한다.

    Returns: 저장된 question_id
    """
    if not question.question_id:
        question.question_id = gen_id("q")

    question.validate()

    with DatabaseSession() as conn:
        conn.execute(
            """
            INSERT INTO questions (
                question_id, parent_question_id, question_text, question_type,
                domain, question_form, variation_type,
                equivalence_label, equivalence_confidence, difficulty,
                negation_depth, frame_type, expected_stance, source, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question.question_id, question.parent_question_id, question.question_text,
                question.question_type, question.domain, question.question_form,
                question.variation_type, question.equivalence_label, question.equivalence_confidence,
                question.difficulty, question.negation_depth, question.frame_type,
                question.expected_stance, question.source, int(question.is_active),
            ),
        )

    return question.question_id


def create_variation(parent_question_id: str, variation: Question) -> str:
    """
    특정 원본 질문(parent_question_id)에 딸린 변형 질문을 저장한다.
    (API명세서 '변형 질문 저장' 대응 — AI 생성 후보 확정 또는 사용자 직접 입력 모두 여기로 옴)

    Raises: QuestionNotFoundError - parent_question_id가 존재하지 않는 경우
    """
    parent = get_question(parent_question_id)
    if parent is None:
        raise QuestionNotFoundError(f"원본 질문을 찾을 수 없습니다: {parent_question_id}")

    variation.parent_question_id = parent_question_id
    if variation.question_type == "ORIGINAL":
        variation.question_type = "VARIANT"  # 변형 저장 경로로 왔으면 강제로 VARIANT 취급

    # 변형 질문은 보통 원본과 같은 도메인/질문형태를 공유한다 (지정 안 했으면 상속)
    if not variation.domain:
        variation.domain = parent.domain
    if not variation.question_form:
        variation.question_form = parent.question_form

    return create_question(variation)


# ---------------------------------------------------------------------------
# 조회
# ---------------------------------------------------------------------------

def get_question(question_id: str) -> Optional[Question]:
    """question_id로 단건 조회. 없으면 None."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM questions WHERE question_id = ?", (question_id,)
        ).fetchone()
        return Question.from_row(row) if row else None
    finally:
        conn.close()


def get_question_with_variations(question_id: str) -> Optional[dict]:
    """
    원본 질문 + 거기 딸린 변형 질문 목록을 함께 반환한다.
    (API명세서 '질문 단건 조회' 응답 형태: { ...question, "variations": [...] })
    """
    question = get_question(question_id)
    if question is None:
        return None

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM questions WHERE parent_question_id = ? ORDER BY created_at",
            (question_id,),
        ).fetchall()
        variations = [Question.from_row(r).to_dict() for r in rows]
    finally:
        conn.close()

    result = question.to_dict()
    result["variations"] = variations
    return result


def list_questions(
    domain: Optional[str] = None,
    question_form: Optional[str] = None,
    variation_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    question_type: Optional[str] = None,
    page: int = 1,
    size: int = 20,
) -> dict:
    """
    필터 + 페이징으로 질문 목록을 조회한다.
    (API명세서 '질문 목록 조회' 대응)

    Returns: { "items": [Question dict, ...], "total": int }
    """
    if page < 1:
        page = 1
    size = max(1, min(size, 100))  # API명세서 공통 규칙: size 기본 20, 최대 100

    filters = []
    params: list = []
    if domain:
        filters.append("domain = ?")
        params.append(domain)
    if question_form:
        filters.append("question_form = ?")
        params.append(question_form)
    if variation_type:
        filters.append("variation_type = ?")
        params.append(variation_type)
    if difficulty:
        filters.append("difficulty = ?")
        params.append(difficulty)
    if question_type:
        filters.append("question_type = ?")
        params.append(question_type)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    conn = get_connection()
    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM questions {where_clause}", params
        ).fetchone()[0]

        offset = (page - 1) * size
        rows = conn.execute(
            f"""
            SELECT * FROM questions {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (*params, size, offset),
        ).fetchall()

        items = [Question.from_row(r).to_dict() for r in rows]
    finally:
        conn.close()

    return {"items": items, "total": total}


# ---------------------------------------------------------------------------
# 수정
# ---------------------------------------------------------------------------

# 프론트에서 수정 가능하도록 허용한 필드만 화이트리스트로 관리
# (question_id, created_at 같은 건 여기 없으므로 수정 요청에 들어와도 무시된다)
UPDATABLE_FIELDS = (
    "question_text", "variation_type", "difficulty", "equivalence_label",
    "equivalence_confidence", "frame_type", "expected_stance", "is_active",
)


def update_question(question_id: str, **fields) -> bool:
    """
    보낸 필드만 부분 수정한다. (API명세서 PATCH /questions/{id} 대응)

    사용 예: update_question("q_101", difficulty="HARD", equivalence_label=True)

    Raises: QuestionNotFoundError
    """
    existing = get_question(question_id)
    if existing is None:
        raise QuestionNotFoundError(f"질문을 찾을 수 없습니다: {question_id}")

    updates = {k: v for k, v in fields.items() if k in UPDATABLE_FIELDS and v is not None}
    if not updates:
        return False  # 수정할 내용이 없으면 아무것도 안 함

    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values())

    with DatabaseSession() as conn:
        conn.execute(
            f"UPDATE questions SET {set_clause}, updated_at = datetime('now') WHERE question_id = ?",
            (*params, question_id),
        )

    return True


# ---------------------------------------------------------------------------
# 삭제
# ---------------------------------------------------------------------------

def delete_question(question_id: str) -> bool:
    """
    질문을 삭제한다. migration.py의 ON DELETE CASCADE에 의해
    이 질문의 변형 질문들(parent_question_id로 연결된 것들)도 함께 삭제된다.

    Raises: QuestionNotFoundError
    """
    existing = get_question(question_id)
    if existing is None:
        raise QuestionNotFoundError(f"질문을 찾을 수 없습니다: {question_id}")

    with DatabaseSession() as conn:
        conn.execute("DELETE FROM questions WHERE question_id = ?", (question_id,))

    return True