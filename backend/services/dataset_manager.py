"""
KoSI - 데이터셋 관리 로직

역할:
  - 질문 "한 건"을 다루는 crud.py와 달리, 데이터셋 "전체"를 다루는 로직을 담당한다.
  - 도메인/유형별 통계, 검수(동치 라벨링) 진행률, 원본-변형 완성도 점검, CSV 내보내기를 제공한다.
  - dataset_api.py나 프론트 '데이터셋 관리 화면'이 이 모듈의 함수를 그대로 가져다 쓴다.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "database"))
from database import get_connection

EXPECTED_VARIATIONS_PER_ORIGINAL = 8  # SYNONYM~FRAMING 8종


def get_dataset_stats() -> dict:
    """
    전체 데이터셋 현황 요약.

    Returns:
        {
          "totalQuestions": int,
          "totalOriginals": int,
          "totalVariants": int,
          "byDomain": {domain: count, ...},          # 원본 기준
          "byQuestionForm": {form: count, ...},       # 원본 기준
          "byVariationType": {type: count, ...},      # 변형 기준
          "equivalenceReview": {
              "labeled": int, "unlabeled": int, "reviewRate": float  # 0~100
          }
        }
    """
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        total_originals = conn.execute(
            "SELECT COUNT(*) FROM questions WHERE question_type = 'ORIGINAL'"
        ).fetchone()[0]
        total_variants = total - total_originals

        by_domain = dict(conn.execute(
            "SELECT domain, COUNT(*) FROM questions WHERE question_type = 'ORIGINAL' GROUP BY domain"
        ).fetchall())
        by_form = dict(conn.execute(
            "SELECT question_form, COUNT(*) FROM questions WHERE question_type = 'ORIGINAL' GROUP BY question_form"
        ).fetchall())
        by_variation = dict(conn.execute(
            "SELECT variation_type, COUNT(*) FROM questions "
            "WHERE question_type != 'ORIGINAL' GROUP BY variation_type"
        ).fetchall())

        labeled = conn.execute(
            "SELECT COUNT(*) FROM questions WHERE question_type != 'ORIGINAL' AND equivalence_label IS NOT NULL"
        ).fetchone()[0]
        unlabeled = total_variants - labeled
        review_rate = round(labeled / total_variants * 100, 2) if total_variants else 0.0
    finally:
        conn.close()

    return {
        "totalQuestions": total,
        "totalOriginals": total_originals,
        "totalVariants": total_variants,
        "byDomain": by_domain,
        "byQuestionForm": by_form,
        "byVariationType": by_variation,
        "equivalenceReview": {
            "labeled": labeled,
            "unlabeled": unlabeled,
            "reviewRate": review_rate,
        },
    }


def get_completeness_report() -> dict:
    """
    원본마다 변형이 정확히 8개(SYNONYM~FRAMING)씩 다 붙어 있는지 점검한다.

    데이터셋 구축 중 일부만 생성되었거나, 삭제로 인해 빠진 변형이 있는지
    확인할 때 쓴다 (예: 검수 도중 부적절한 변형을 지웠는데 대체를 안 만든 경우).

    Returns:
        {
          "totalOriginals": int,
          "complete": int,                 # 변형이 정확히 8개인 원본 수
          "incomplete": [
              {"questionId": str, "questionText": str, "variationCount": int,
               "missingTypes": [str, ...]},
              ...
          ]
        }
    """
    all_variation_types = {
        "SYNONYM", "WORD_ORDER", "STYLE", "POLARITY",
        "VOICE", "DOUBLE_NEGATION", "HONORIFIC", "FRAMING",
    }

    conn = get_connection()
    try:
        originals = conn.execute(
            "SELECT question_id, question_text FROM questions WHERE question_type = 'ORIGINAL'"
        ).fetchall()

        incomplete = []
        complete_count = 0

        for row in originals:
            variation_rows = conn.execute(
                "SELECT variation_type FROM questions WHERE parent_question_id = ?",
                (row["question_id"],),
            ).fetchall()
            existing_types = {r["variation_type"] for r in variation_rows}

            if len(existing_types) == EXPECTED_VARIATIONS_PER_ORIGINAL:
                complete_count += 1
            else:
                incomplete.append({
                    "questionId": row["question_id"],
                    "questionText": row["question_text"],
                    "variationCount": len(existing_types),
                    "missingTypes": sorted(all_variation_types - existing_types),
                })
    finally:
        conn.close()

    return {
        "totalOriginals": len(originals),
        "complete": complete_count,
        "incomplete": incomplete,
    }


def export_dataset_csv(output_path: str) -> str:
    """
    현재 DB의 questions 테이블 전체를 CSV로 내보낸다.
    (question.csv와 동일한 컬럼 구조 -> seed.py로 다시 적재 가능)

    Returns: 저장된 파일 경로
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT question_id, parent_question_id, question_text, question_type,
                   domain, question_form, variation_type, difficulty, source
            FROM questions
            ORDER BY created_at
            """
        ).fetchall()
    finally:
        conn.close()

    fieldnames = [
        "question_id", "parent_question_id", "question_text", "question_type",
        "domain", "question_form", "variation_type", "difficulty", "source",
    ]

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: (row[k] if row[k] is not None else "") for k in fieldnames})

    return output_path