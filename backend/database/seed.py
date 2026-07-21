# backend/database/seed.py
# 초기 데이터 삽입
"""
KoSI - question.csv -> DB(questions 테이블) 적재 스크립트

사용법:
    python migration.py --reset     # 스키마 먼저 준비 (한 번만)
    python seed.py                  # question.csv 데이터 적재

동작:
    - dataset/question.csv 를 읽는다.
    - 2-pass로 적재한다:
        1st pass: question_type == 'ORIGINAL' 인 행 먼저 삽입
        2nd pass: 'VARIANT'/'FRAMING' 행 삽입 (parent_question_id가 1st pass에서
                   이미 존재해야 FK 제약(questions.parent_question_id -> questions.question_id)을
                   통과하므로 순서가 중요하다)
    - question_id는 question.csv에 이미 생성되어 있는 값을 그대로 사용한다
      (gen_id로 새로 만들지 않음 -> parent_question_id 연결이 깨지지 않게 하기 위함)
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from database import DatabaseSession, get_connection

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "dataset", "question.csv")


def load_csv(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_null(value: str):
    """빈 문자열을 SQL NULL(None)로 변환."""
    return value if value not in (None, "") else None


def insert_rows(conn, rows: list[dict]) -> None:
    for row in rows:
        conn.execute(
            """
            INSERT INTO questions (
                question_id, parent_question_id, question_text, question_type,
                domain, question_form, variation_type, difficulty, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["question_id"],
                to_null(row["parent_question_id"]),
                row["question_text"],
                row["question_type"],
                row["domain"],
                row["question_form"],
                to_null(row["variation_type"]),
                row["difficulty"] or "MEDIUM",
                row["source"] or "manual",
            ),
        )


def main():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(
            f"question.csv를 찾을 수 없습니다: {CSV_PATH}\n"
            f"dataset/question.csv 위치를 확인하거나 CSV_PATH를 수정하세요."
        )

    rows = load_csv(CSV_PATH)
    originals = [r for r in rows if r["question_type"] == "ORIGINAL"]
    variants = [r for r in rows if r["question_type"] != "ORIGINAL"]

    print(f"[seed] CSV 로드: 전체 {len(rows)}행 (원본 {len(originals)} / 변형 {len(variants)})")

    with DatabaseSession() as conn:
        # 기존 데이터가 있으면 먼저 비운다 (재실행 가능하게)
        conn.execute("DELETE FROM questions")

        # 1st pass: 원본 먼저 (parent_question_id가 없어야 하는 행들)
        insert_rows(conn, originals)
        print(f"[seed] 원본 {len(originals)}개 삽입 완료")

        # 2nd pass: 변형 (parent_question_id가 1st pass 데이터를 참조)
        insert_rows(conn, variants)
        print(f"[seed] 변형 {len(variants)}개 삽입 완료")

    # 검증
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    by_domain = conn.execute(
        "SELECT domain, COUNT(*) FROM questions WHERE question_type='ORIGINAL' GROUP BY domain"
    ).fetchall()
    conn.close()

    print(f"\n[seed] DB 적재 후 questions 테이블 총 행 수: {total}")
    print("[seed] 도메인별 원본 개수:")
    for domain, count in by_domain:
        print(f"  {domain}: {count}")


if __name__ == "__main__":
    main()