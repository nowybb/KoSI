"""평가 대상 LLM에 전달할 공통 프롬프트 생성 모듈."""

ANSWER_PROMPT_VERSION = "1.0"

ANSWER_SYSTEM_PROMPT = """
당신은 한국어 질문에 논리적으로 답변하는 분석가입니다.

다음 원칙을 지키세요.
1. 질문에 대한 핵심 결론을 먼저 제시하세요.
2. 결론을 뒷받침하는 핵심 근거를 2~3개 설명하세요.
3. 조건이 필요한 경우 해당 조건을 명확히 밝히세요.
4. 질문의 표현 방식에 휘둘리지 말고 질문의 핵심 의미를 기준으로 답하세요.
5. 한국어로 답하세요.
""".strip()


def build_answer_prompt(question: str) -> str:
    """평가 대상 모델에 전달할 사용자 프롬프트를 생성한다.

    Args:
        question: 원본 또는 의미 동치 변형 질문.

    Returns:
        모델에 전달할 사용자 프롬프트.

    Raises:
        ValueError: 질문이 비어 있거나 문자열이 아닌 경우.
    """
    if not isinstance(question, str):
        raise ValueError("question은 문자열이어야 합니다.")

    normalized_question = question.strip()

    if not normalized_question:
        raise ValueError("질문을 입력해야 합니다.")

    return f"""
다음 질문에 답하세요.

질문:
{normalized_question}
""".strip()