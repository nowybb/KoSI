"""질문, 응답, 평가 결과 테이블 모델 정의."""

"""
KoSI - DB 테이블 모델 정의

역할:
    - migration.py에서 만든 테이블 구조를 Python 코드에서도 다루기 쉽게 dataclass로 표현한다.
    - SQLAlchemy 같은 ORM은 쓰지 않는다 (팀 결정: 이 단계에서는 오버엔지니어링).
    대신 sqlite3.Row <-> dataclass 변환만 얇게 지원한다.
    - crud.py는 여기 정의된 모델을 입출력 타입으로 사용한다.

questions 테이블만 정의한다.
(responses/analysis_results 등 나머지 테이블 모델은 추가)
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import sqlite3

# --- migration.py의 CHECK 제약과 동일하게 맞춘 허용값 목록 ---
# (DB가 막아주긴 하지만, API 레이어에서 미리 검증해서 더 친절한 에러 메시지를 주기 위해 코드에도 둔다)

QUESTION_TYPES = ("ORIGINAL", "VARIANT", "FRAMING", "NON_EQUIVALENT")
DOMAINS = ("POLITICS_SOCIETY", "ECONOMY", "SCIENCE_TECH", "ETHICS_VALUES", "DAILY_CULTURE")
QUESTION_FORMS = ("FACT_JUDGMENT", "STANCE_JUDGMENT", "CAUSE_EXPLANATION", "COMPARISON_CHOICE", "CONDITION_JUDGMENT")
VARIATION_TYPES = ("SYNONYM", "WORD_ORDER", "STYLE", "POLARITY", "VOICE", "DOUBLE_NEGATION", "HONORIFIC", "FRAMING")
DIFFICULTIES = ("EASY", "MEDIUM", "HARD")
EXPECTED_STANCES = (
    "SUPPORT", "OPPOSE", "NEUTRAL",
    "CONDITIONAL_SUPPORT", "CONDITIONAL_OPPOSE", "UNDETERMINED",
)
SOURCES = ("auto", "manual")


@dataclass
class Question:
    """questions 테이블 한 행에 대응하는 모델."""

    question_id: str
    question_text: str
    question_type: str                      # QUESTION_TYPES 중 하나
    domain: str                              # DOMAINS 중 하나
    question_form: str                       # QUESTION_FORMS 중 하나

    parent_question_id: Optional[str] = None
    variation_type: Optional[str] = None     # VARIATION_TYPES 중 하나, ORIGINAL이면 None
    equivalence_label: Optional[bool] = None
    equivalence_confidence: Optional[float] = None
    difficulty: str = "MEDIUM"
    negation_depth: int = 0
    frame_type: Optional[str] = None
    expected_stance: Optional[str] = None
    source: str = "manual"
    is_active: bool = True
    created_at: Optional[str] = None         # DB가 자동 채움 (datetime('now'))
    updated_at: Optional[str] = None         # DB가 자동 채움

    def validate(self) -> None:
        """
        migration.py의 CHECK 제약과 동일한 조건을 미리 검증한다.
        여기서 걸러내면 DB IntegrityError 대신 명확한 ValueError 메시지를 API 단에서 바로 줄 수 있다.
        """
        errors = []

        if self.question_type not in QUESTION_TYPES:
            errors.append(f"question_type은 {QUESTION_TYPES} 중 하나여야 합니다: {self.question_type}")
        if self.domain not in DOMAINS:
            errors.append(f"domain은 {DOMAINS} 중 하나여야 합니다: {self.domain}")
        if self.question_form not in QUESTION_FORMS:
            errors.append(f"question_form은 {QUESTION_FORMS} 중 하나여야 합니다: {self.question_form}")
        if self.variation_type is not None and self.variation_type not in VARIATION_TYPES:
            errors.append(f"variation_type은 {VARIATION_TYPES} 중 하나이거나 None이어야 합니다: {self.variation_type}")
        if self.difficulty not in DIFFICULTIES:
            errors.append(f"difficulty는 {DIFFICULTIES} 중 하나여야 합니다: {self.difficulty}")
        if self.expected_stance is not None and self.expected_stance not in EXPECTED_STANCES:
            errors.append(f"expected_stance는 {EXPECTED_STANCES} 중 하나이거나 None이어야 합니다: {self.expected_stance}")
        if self.source not in SOURCES:
            errors.append(f"source는 {SOURCES} 중 하나여야 합니다: {self.source}")

        # 원본 질문인데 parent_question_id가 있으면 앞뒤가 안 맞음
        if self.question_type == "ORIGINAL" and self.parent_question_id is not None:
            errors.append("question_type이 ORIGINAL이면 parent_question_id는 None이어야 합니다.")
        # 변형 질문인데 parent_question_id가 없으면 어떤 원본의 변형인지 알 수 없음
        if self.question_type in ("VARIANT", "FRAMING") and self.parent_question_id is None:
            errors.append(f"question_type이 {self.question_type}이면 parent_question_id가 필요합니다.")

        if errors:
            raise ValueError("Question 유효성 검증 실패:\n- " + "\n- ".join(errors))

    def to_dict(self) -> dict:
        """API 응답이나 JSON 직렬화용으로 dict 변환. None 필드도 그대로 포함."""
        return asdict(self)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Question":
        """DB 조회 결과(sqlite3.Row)를 Question 객체로 변환."""
        data = dict(row)
        # sqlite에는 boolean 타입이 없어 0/1(int)로 저장되므로 bool로 되돌린다
        if "is_active" in data and data["is_active"] is not None:
            data["is_active"] = bool(data["is_active"])
        if "equivalence_label" in data and data["equivalence_label"] is not None:
            data["equivalence_label"] = bool(data["equivalence_label"])
        return cls(**data)