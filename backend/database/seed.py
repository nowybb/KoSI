"""
backend/database/seed.py
question.csv 데이터를 questions 테이블에 삽입
"""
import csv
import os
from database import get_connection, gen_id

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "dataset", "question.csv")


def _to_bool_or_none(value):
    if value is None or value == "":
        return None
    return bool(int(value))


def _to_int_or_zero(value):
    if value is None or value == "":
        return 0
    return int(value)


def _none_if_empty(value):
    return value if value not in (None, "") else None


def seed_questions():
    conn = get_connection()
    cursor = conn.cursor()

    # 재실행 시 중복 방지: 기존 데이터 초기화
    cursor.execute("DELETE FROM questions")

    original_id_map = {}
    inserted, skipped = 0, 0

    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # 1차: ORIGINAL
    for row in rows:
        if row["question_type"] != "ORIGINAL":
            continue
        qid = gen_id()
        original_id_map[row["item_id"]] = qid
        try:
            cursor.execute(
                """
                INSERT INTO questions (
                    question_id, evaluation_id, parent_question_id, question_text,
                    question_type, category, variation_type, equivalence_label,
                    difficulty, negation_depth, frame_type, expected_stance, is_active
                ) VALUES (?, NULL, NULL, ?, ?, ?, NULL, NULL, ?, ?, ?, ?, 1)
                """,
                (
                    qid,                                          # question_id
                    row["original_question"],                     # question_text
                    row["question_type"],                         # question_type
                    row["category"],                               # category
                    row["difficulty"] or "NORMAL",                 # difficulty  <- 여기 순서 고정
                    _to_int_or_zero(row["negation_depth"]),        # negation_depth
                    _none_if_empty(row["frame_type"]),             # frame_type
                    _none_if_empty(row["expected_stance"]),        # expected_stance
                ),
            )
            inserted += 1
        except Exception as e:
            print(f"⚠️  원본 삽입 실패 [{row['item_id']}]: {e}")
            skipped += 1

    # 2차: VARIANT / FRAMING / NON_EQUIVALENT
    for row in rows:
        if row["question_type"] == "ORIGINAL":
            continue

        parent_id = original_id_map.get(row["item_id"])
        if parent_id is None:
            print(f"⚠️  부모 질문을 찾을 수 없음 [{row['pair_id']}] - 건너뜀")
            skipped += 1
            continue

        qid = gen_id()
        try:
            cursor.execute(
                """
                INSERT INTO questions (
                    question_id, evaluation_id, parent_question_id, question_text,
                    question_type, category, variation_type, equivalence_label,
                    difficulty, negation_depth, frame_type, expected_stance, is_active
                ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    qid,                                          # question_id
                    parent_id,                                     # parent_question_id
                    row["variant_question"],                       # question_text
                    row["question_type"],                          # question_type
                    row["category"],                               # category
                    _none_if_empty(row["variation_type"]),         # variation_type
                    _to_bool_or_none(row["equivalence_label"]),    # equivalence_label
                    row["difficulty"] or "NORMAL",                  # difficulty
                    _to_int_or_zero(row["negation_depth"]),        # negation_depth
                    _none_if_empty(row["frame_type"]),             # frame_type
                    _none_if_empty(row["expected_stance"]),        # expected_stance
                ),
            )
            inserted += 1
        except Exception as e:
            print(f"⚠️  변형 삽입 실패 [{row['pair_id']}]: {e}")
            skipped += 1

    conn.commit()
    conn.close()
    print(f"✅ 삽입 완료: {inserted}건 성공, {skipped}건 실패/스킵")


if __name__ == "__main__":
    seed_questions()