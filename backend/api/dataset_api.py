"""
KoSI - 질문 관리 API

API명세서.md 3. 질문 관리 섹션 중 CRUD 부분을 구현한다.
(자동 생성/검수 라벨/일치도 조회 등은 paraphrase_service, 검수 로직 완성 후 별도 구현)

엔드포인트:
  POST   /api/v1/questions                      원본 질문 저장
  POST   /api/v1/questions/{questionId}/variations   변형 질문 저장
  GET    /api/v1/questions                       질문 목록 조회 (필터+페이징)
  GET    /api/v1/questions/{questionId}          질문 단건 조회 (변형 포함)
  PATCH  /api/v1/questions/{questionId}          질문 수정
  DELETE /api/v1/questions/{questionId}          질문 삭제

실행 (단독 테스트용):
  cd backend/api && uvicorn dataset_api:app --reload
"""

import sys
import os
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# backend/database 를 import 경로에 추가
# (backend/api/dataset_api.py 에서 backend/database/crud.py, models.py 를 바로 가져오기 위함)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "database"))
# backend/services 를 import 경로에 추가 (dataset_manager.py - 통계/완성도/내보내기)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

import crud
import dataset_manager
from models import (
    Question, DOMAINS, QUESTION_FORMS, VARIATION_TYPES,
    DIFFICULTIES, EXPECTED_STANCES, QUESTION_TYPES,
)

app = FastAPI(title="KoSI - 질문 관리 API")


# ---------------------------------------------------------------------------
# 공통 에러 응답 포맷 (API명세서.md 공통 에러 포맷 그대로)
# ---------------------------------------------------------------------------

def error_response(status_code: int, error_code: str, message: str, detail: str = ""):
    raise HTTPException(
        status_code=status_code,
        detail={"status": "error", "error_code": error_code, "message": message, "detail": detail},
    )


# ---------------------------------------------------------------------------
# 요청/응답 스키마 (Pydantic)
# ---------------------------------------------------------------------------

class QuestionCreateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500, description="질문 내용")
    domain: str = Field(..., description=f"{DOMAINS}")
    questionForm: str = Field(..., description=f"{QUESTION_FORMS}")
    difficulty: str = Field("MEDIUM", description=f"{DIFFICULTIES}")
    expectedStance: Optional[str] = Field(None, description=f"{EXPECTED_STANCES}")


class VariationCreateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    variationType: str = Field(..., description=f"{VARIATION_TYPES}")
    source: str = Field("manual", description="auto(AI 생성) / manual(직접 입력)")
    negationDepth: int = Field(0, ge=0)
    frameType: Optional[str] = None


class QuestionUpdateRequest(BaseModel):
    text: Optional[str] = None
    variationType: Optional[str] = None
    difficulty: Optional[str] = None
    isEquivalent: Optional[bool] = None
    equivalenceConfidence: Optional[float] = None
    frameType: Optional[str] = None
    expectedStance: Optional[str] = None
    isActive: Optional[bool] = None


# ---------------------------------------------------------------------------
# 엔드포인트
# ---------------------------------------------------------------------------

@app.post("/api/v1/questions", status_code=201)
def create_question(payload: QuestionCreateRequest):
    """원본 질문 저장."""
    question = Question(
        question_id="",
        question_text=payload.text,
        question_type="ORIGINAL",
        domain=payload.domain,
        question_form=payload.questionForm,
        difficulty=payload.difficulty,
        expected_stance=payload.expectedStance,
    )
    try:
        question.validate()
        question_id = crud.create_question(question)
    except ValueError as e:
        error_response(422, "INVALID_INPUT", "지원하지 않는 값이 포함되어 있습니다.", str(e))

    return {"questionId": question_id}


@app.post("/api/v1/questions/{question_id}/variations", status_code=201)
def create_variation(question_id: str, payload: VariationCreateRequest):
    """변형 질문 저장 (AI 생성 후보 확정 또는 직접 입력)."""
    variation = Question(
        question_id="",
        question_text=payload.text,
        question_type="VARIANT",
        domain="",
        question_form="",
        variation_type=payload.variationType,
        source=payload.source,
        negation_depth=payload.negationDepth,
        frame_type=payload.frameType,
    )
    try:
        variation_id = crud.create_variation(question_id, variation)
    except crud.QuestionNotFoundError as e:
        error_response(404, "NOT_FOUND", "원본 질문을 찾을 수 없습니다.", str(e))
    except ValueError as e:
        error_response(422, "INVALID_INPUT", "지원하지 않는 값이 포함되어 있습니다.", str(e))

    return {"variationId": variation_id}


@app.get("/api/v1/questions")
def list_questions(
    domain: Optional[str] = Query(None),
    questionForm: Optional[str] = Query(None),
    variationType: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    questionType: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """질문 목록 조회 (필터 전부 optional, 페이징 포함)."""
    result = crud.list_questions(
        domain=domain,
        question_form=questionForm,
        variation_type=variationType,
        difficulty=difficulty,
        question_type=questionType,
        page=page,
        size=size,
    )
    return result


@app.get("/api/v1/questions/{question_id}")
def get_question(question_id: str):
    """질문 단건 조회 (딸린 변형 질문 목록 포함)."""
    result = crud.get_question_with_variations(question_id)
    if result is None:
        error_response(404, "NOT_FOUND", "존재하지 않는 질문입니다.", f"questionId: {question_id}")
    return result


@app.patch("/api/v1/questions/{question_id}")
def update_question(question_id: str, payload: QuestionUpdateRequest):
    """질문 부분 수정 (보낸 필드만 반영)."""
    # 프론트/API 쪽 필드명(camelCase) -> DB 컬럼명(snake_case) 매핑
    field_map = {
        "text": "question_text",
        "variationType": "variation_type",
        "difficulty": "difficulty",
        "isEquivalent": "equivalence_label",
        "equivalenceConfidence": "equivalence_confidence",
        "frameType": "frame_type",
        "expectedStance": "expected_stance",
        "isActive": "is_active",
    }
    updates = {
        field_map[k]: v
        for k, v in payload.model_dump(exclude_unset=True).items()
        if v is not None
    }

    try:
        crud.update_question(question_id, **updates)
    except crud.QuestionNotFoundError as e:
        error_response(404, "NOT_FOUND", "존재하지 않는 질문입니다.", str(e))

    return {"updated": True}


@app.delete("/api/v1/questions/{question_id}")
def delete_question(question_id: str):
    """질문 삭제 (딸린 변형 질문도 CASCADE로 함께 삭제됨)."""
    try:
        crud.delete_question(question_id)
    except crud.QuestionNotFoundError as e:
        error_response(404, "NOT_FOUND", "존재하지 않는 질문입니다.", str(e))

    return {"deleted": True}


# ---------------------------------------------------------------------------
# 데이터셋 관리 (dataset_manager.py 연동) - 프론트 '데이터셋 관리 화면' 통계용
# ---------------------------------------------------------------------------

@app.get("/api/v1/dataset/stats")
def get_dataset_stats():
    """전체/도메인별/유형별/변형타입별 개수, 검수(동치 라벨링) 진행률."""
    return dataset_manager.get_dataset_stats()


@app.get("/api/v1/dataset/completeness")
def get_dataset_completeness():
    """원본마다 변형 8종이 다 채워져 있는지 점검. 빠진 원본/타입을 함께 반환."""
    return dataset_manager.get_completeness_report()


@app.get("/api/v1/dataset/export")
def export_dataset():
    """현재 DB의 questions 테이블 전체를 CSV로 내보내고 다운로드 경로를 반환."""
    output_path = "/tmp/kosi_dataset_export.csv"
    path = dataset_manager.export_dataset_csv(output_path)
    return FileResponse(path, filename="question_export.csv", media_type="text/csv")