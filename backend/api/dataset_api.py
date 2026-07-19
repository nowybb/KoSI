"""
backend/api/dataset_api.py
질문 CRUD API (원본 질문 저장, 변형 질문 저장, 목록/단건 조회, 수정, 삭제)
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Literal
from database import crud


router = APIRouter(prefix="/api/v1/questions", tags=["questions"])

# ---- Enum 타입 (category.json 기준) ----
CategoryType = Literal["FACT", "LOGIC", "ETHICS", "NEGATION", "KOREAN_CONTEXT", "FRAMING"]
VariationType = Literal["SYNONYM", "WORD_ORDER", "STYLE", "POLARITY", "VOICE",
                        "NEGATION", "HONORIFIC", "FRAMING"]
QuestionType = Literal["VARIANT", "FRAMING", "NON_EQUIVALENT"]
DifficultyType = Literal["EASY", "MEDIUM", "HARD"]


# ---- Request/Response 스키마 ----
class OriginalQuestionCreate(BaseModel):
    text: str = Field(..., max_length=500, description="원본 질문 텍스트")
    category: CategoryType
    difficulty: DifficultyType = "MEDIUM"
    frame_type: Optional[str] = None
    expected_stance: Optional[str] = None


class VariationCreate(BaseModel):
    text: str = Field(..., max_length=500)
    variation_type: Optional[VariationType] = None
    question_type: QuestionType = "VARIANT"
    equivalence_label: Optional[bool] = None
    difficulty: DifficultyType = "MEDIUM"
    negation_depth: int = Field(0, ge=0)
    frame_type: Optional[str] = None
    expected_stance: Optional[str] = None


class QuestionUpdate(BaseModel):
    text: Optional[str] = Field(None, max_length=500)
    variation_type: Optional[VariationType] = None
    difficulty: Optional[DifficultyType] = None
    equivalence_label: Optional[bool] = None
    frame_type: Optional[str] = None
    expected_stance: Optional[str] = None


# ---- 원본 질문 저장 ----
@router.post("", status_code=201)
def create_original_question(payload: OriginalQuestionCreate):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="원본 질문 텍스트가 비어 있습니다.")

    question_id = crud.create_original_question(
        text=payload.text,
        category=payload.category,
        difficulty=payload.difficulty,
        frame_type=payload.frame_type,
        expected_stance=payload.expected_stance,
    )
    return {"questionId": question_id}


# ---- 변형 질문 저장 ----
@router.post("/{question_id}/variations", status_code=201)
def create_variation(question_id: str, payload: VariationCreate):
    if not crud.question_exists(question_id):
        raise HTTPException(status_code=404, detail="존재하지 않는 원본 질문입니다.")

    if payload.question_type == "VARIANT" and payload.variation_type is None:
        raise HTTPException(
            status_code=422,
            detail="question_type이 VARIANT일 때 variation_type은 필수입니다.",
        )

    variation_id = crud.create_variation(
        parent_id=question_id,
        text=payload.text,
        variation_type=payload.variation_type,
        question_type=payload.question_type,
        equivalence_label=payload.equivalence_label,
        difficulty=payload.difficulty,
        negation_depth=payload.negation_depth,
        frame_type=payload.frame_type,
        expected_stance=payload.expected_stance,
    )
    return {"variationId": variation_id}


# ---- 질문 목록 조회 ----
@router.get("")
def list_questions(
    category: Optional[CategoryType] = None,
    variation_type: Optional[VariationType] = None,
    difficulty: Optional[DifficultyType] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    result = crud.list_questions(
        category=category, variation_type=variation_type,
        difficulty=difficulty, page=page, size=size,
    )
    items = [
        {
            "questionId": row["question_id"],
            "text": row["question_text"],
            "category": row["category"],
            "questionType": row["question_type"],
            "difficulty": row["difficulty"],
        }
        for row in result["items"]
    ]
    return {"items": items, "total": result["total"]}


# ---- 질문 단건 조회 ----
@router.get("/{question_id}")
def get_question(question_id: str):
    result = crud.get_question_by_id(question_id)
    if result is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 질문입니다.")

    original = result["original"]
    return {
        "questionId": original["question_id"],
        "text": original["question_text"],
        "category": original["category"],
        "difficulty": original["difficulty"],
        "variations": [
            {
                "variationId": v["question_id"],
                "text": v["question_text"],
                "variationType": v["variation_type"],
                "questionType": v["question_type"],
                "isEquivalent": bool(v["equivalence_label"]) if v["equivalence_label"] is not None else None,
            }
            for v in result["variations"]
        ],
    }


# ---- 질문 수정 ----
@router.patch("/{question_id}")
def update_question(question_id: str, payload: QuestionUpdate):
    if not crud.question_exists(question_id):
        raise HTTPException(status_code=404, detail="존재하지 않는 질문입니다.")

    updated = crud.update_question(
        question_id,
        text=payload.text,
        variation_type=payload.variation_type,
        difficulty=payload.difficulty,
        equivalence_label=payload.equivalence_label,
        frame_type=payload.frame_type,
        expected_stance=payload.expected_stance,
    )
    return {"updated": updated}


# ---- 질문 삭제 ----
@router.delete("/{question_id}")
def delete_question(question_id: str):
    if not crud.question_exists(question_id):
        raise HTTPException(status_code=404, detail="존재하지 않는 질문입니다.")

    deleted = crud.delete_question(question_id)
    return {"deleted": deleted}