"""
backend/database/crud.py
questions 테이블 CRUD 함수 모음
"""
from .database import get_connection, gen_id


def create_original_question(text, category, difficulty="NORMAL",
                            frame_type=None, expected_stance=None):
    """원본 질문(ORIGINAL) 생성"""
    qid = gen_id()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO questions (
                question_id, evaluation_id, parent_question_id, question_text,
                question_type, category, variation_type, equivalence_label,
                difficulty, negation_depth, frame_type, expected_stance, is_active
            ) VALUES (?, NULL, NULL, ?, 'ORIGINAL', ?, NULL, NULL, ?, 0, ?, ?, 1)
            """,
            (qid, text, category, difficulty, frame_type, expected_stance),
        )
        conn.commit()
        return qid
    finally:
        conn.close()


def create_variation(parent_id, text, variation_type, question_type="VARIANT",
                    equivalence_label=None, difficulty="NORMAL",
                    negation_depth=0, frame_type=None, expected_stance=None):
    """변형/프레이밍/비동치 질문 생성. parent_id 존재 여부는 호출부(API)에서 확인."""
    qid = gen_id()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO questions (
                question_id, evaluation_id, parent_question_id, question_text,
                question_type, category, variation_type, equivalence_label,
                difficulty, negation_depth, frame_type, expected_stance, is_active
            )
            SELECT ?, NULL, ?, ?, ?, category, ?, ?, ?, ?, ?, ?, 1
            FROM questions WHERE question_id = ?
            """,
            (qid, parent_id, text, question_type, variation_type,
            equivalence_label, difficulty, negation_depth, frame_type,
            expected_stance, parent_id),
        )
        conn.commit()
        return qid
    finally:
        conn.close()


def get_question_by_id(question_id):
    """단건 조회 (연결된 변형 질문 목록 포함)"""
    conn = get_connection()
    try:
        original = conn.execute(
            "SELECT * FROM questions WHERE question_id = ? AND is_active = 1",
            (question_id,),
        ).fetchone()
        if original is None:
            return None

        variations = conn.execute(
            "SELECT * FROM questions WHERE parent_question_id = ? AND is_active = 1",
            (question_id,),
        ).fetchall()
        return {"original": dict(original), "variations": [dict(v) for v in variations]}
    finally:
        conn.close()


def list_questions(category=None, variation_type=None, difficulty=None,
                    page=1, size=20):
    """목록 조회 (필터 + 페이징). ORIGINAL만 목록에 노출, 변형은 단건 조회 시 함께 반환."""
    conn = get_connection()
    try:
        conditions = ["is_active = 1", "question_type = 'ORIGINAL'"]
        params = []
        if category:
            conditions.append("category = ?")
            params.append(category)
        if variation_type:
            conditions.append("variation_type = ?")
            params.append(variation_type)
        if difficulty:
            conditions.append("difficulty = ?")
            params.append(difficulty)

        where_clause = " AND ".join(conditions)
        total = conn.execute(
            f"SELECT COUNT(*) as cnt FROM questions WHERE {where_clause}", params
        ).fetchone()["cnt"]

        offset = (page - 1) * size
        rows = conn.execute(
            f"""SELECT * FROM questions WHERE {where_clause}
                ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            params + [size, offset],
        ).fetchall()

        return {"items": [dict(r) for r in rows], "total": total}
    finally:
        conn.close()


def update_question(question_id, **fields):
    """부분 수정. fields로 넘어온 것만 업데이트 (None은 무시)."""
    allowed = {"text", "variation_type", "difficulty", "equivalence_label",
               "frame_type", "expected_stance"}
    col_map = {"text": "question_text"}  # API 필드명 -> DB 컬럼명

    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False

    set_clause = ", ".join(f"{col_map.get(k, k)} = ?" for k in updates)
    values = list(updates.values()) + [question_id]

    conn = get_connection()
    try:
        cursor = conn.execute(
            f"UPDATE questions SET {set_clause}, updated_at = CURRENT_TIMESTAMP "
            f"WHERE question_id = ?",
            values,
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_question(question_id):
    """소프트 삭제 (is_active = 0). DB 설계서 'is_active' 컬럼 활용 정책."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE questions SET is_active = 0, updated_at = CURRENT_TIMESTAMP "
            "WHERE question_id = ?",
            (question_id,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def question_exists(question_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM questions WHERE question_id = ? AND is_active = 1",
            (question_id,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()