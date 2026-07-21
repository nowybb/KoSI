"""
KoSI - CSV 업로드 API

역할:
  - question.csv와 같은 형식의 CSV 파일을 업로드받아 questions 테이블에 일괄 등록한다.
  - seed.py가 "로컬 스크립트로 한 번에 밀어넣는" 용도라면,
    이 API는 "팀원이 웹 화면(프론트 데이터셋 관리 화면)에서 CSV를 골라 업로드"하는 용도다.
  - 원본(ORIGINAL)과 변형(VARIANT/FRAMING)이 같은 파일에 섞여 있어도,
    원본을 먼저 넣고 변형을 나중에 넣는 2-pass 처리로 FK 제약을 지킨다.

CSV 필수 컬럼:
    question_text, question_type, domain, question_form
CSV 선택 컬럼 (없으면 기본값 처리):
    question_id, parent_question_id, variation_type, difficulty, source

행 단위로 검증하고, 실패한 행은 건너뛰면서 이유를 리포트에 남긴다
(전체 업로드가 한 행의 오류 때문에 통째로 실패하지 않도록).
"""

import csv
import io
import sys
import os
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "database"))

import crud
from models import Question, DOMAINS, QUESTION_FORMS

app = FastAPI(title="KoSI - CSV 업로드 API")

REQUIRED_COLUMNS = {"question_text", "question_type", "domain", "question_form"}
MAX_ROWS = 5000  # 한 번에 업로드 가능한 최대 행 수 (안전장치)


def _row_to_question(row: dict, line_no: int) -> Question:
    """CSV 한 행을 Question 객체로 변환. 실패하면 ValueError를 던진다."""
    question_text = (row.get("question_text") or "").strip()
    if not question_text:
        raise ValueError("question_text가 비어 있습니다.")

    question_type = (row.get("question_type") or "").strip().upper()
    domain = (row.get("domain") or "").strip().upper()
    question_form = (row.get("question_form") or "").strip().upper()

    if domain not in DOMAINS:
        raise ValueError(f"domain 값이 올바르지 않습니다: {domain!r} (허용값: {DOMAINS})")
    if question_form not in QUESTION_FORMS:
        raise ValueError(f"question_form 값이 올바르지 않습니다: {question_form!r} (허용값: {QUESTION_FORMS})")

    question = Question(
        question_id=(row.get("question_id") or "").strip(),
        parent_question_id=(row.get("parent_question_id") or "").strip() or None,
        question_text=question_text,
        question_type=question_type,
        domain=domain,
        question_form=question_form,
        variation_type=(row.get("variation_type") or "").strip() or None,
        difficulty=(row.get("difficulty") or "MEDIUM").strip().upper(),
        source=(row.get("source") or "manual").strip().lower(),
    )
    question.validate()  # models.py의 CHECK 제약 사전 검증 (여기서 ValueError 나면 위로 전파)
    return question


@app.post("/api/v1/questions/upload")
async def upload_questions_csv(file: UploadFile = File(...)):
    """
    CSV 파일을 업로드받아 questions 테이블에 일괄 등록한다.

    응답 형식:
        {
          "totalRows": int,
          "insertedOriginals": int,
          "insertedVariants": int,
          "skipped": int,
          "errors": [ {"line": int, "reason": str}, ... ]   # 최대 50개까지만 반환
        }
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail={"status": "error", "message": "CSV 파일만 업로드 가능합니다."})

    raw_bytes = await file.read()
    try:
        text = raw_bytes.decode("utf-8-sig")  # 엑셀에서 저장한 CSV의 BOM 대응
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=422,
            detail={"status": "error", "message": "UTF-8 인코딩된 CSV만 지원합니다."},
        )

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        raise HTTPException(
            status_code=422,
            detail={
                "status": "error",
                "message": f"필수 컬럼이 누락되었습니다. 필요한 컬럼: {sorted(REQUIRED_COLUMNS)}",
            },
        )

    rows = list(reader)
    if len(rows) > MAX_ROWS:
        raise HTTPException(
            status_code=422,
            detail={"status": "error", "message": f"한 번에 최대 {MAX_ROWS}행까지만 업로드할 수 있습니다."},
        )

    errors = []
    valid_questions: list[Question] = []

    for i, row in enumerate(rows, start=2):  # 2행부터 (1행은 헤더)
        try:
            valid_questions.append(_row_to_question(row, i))
        except ValueError as e:
            errors.append({"line": i, "reason": str(e)})

    # 1st pass: 원본(ORIGINAL) 먼저 삽입 -> parent_question_id FK가 걸리는 변형보다 항상 먼저 존재해야 함
    originals = [q for q in valid_questions if q.question_type == "ORIGINAL"]
    variants = [q for q in valid_questions if q.question_type != "ORIGINAL"]

    inserted_originals = 0
    inserted_variants = 0

    for q in originals:
        try:
            crud.create_question(q)
            inserted_originals += 1
        except Exception as e:
            errors.append({"line": "-", "reason": f"저장 실패 ({q.question_text[:20]}...): {e}"})

    for q in variants:
        try:
            crud.create_question(q)  # parent_question_id는 CSV에 이미 명시되어 있다고 가정
            inserted_variants += 1
        except Exception as e:
            errors.append({"line": "-", "reason": f"저장 실패 ({q.question_text[:20]}...): {e}"})

    return {
        "totalRows": len(rows),
        "insertedOriginals": inserted_originals,
        "insertedVariants": inserted_variants,
        "skipped": len(rows) - inserted_originals - inserted_variants,
        "errors": errors[:50],
    }