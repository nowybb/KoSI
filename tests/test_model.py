"""GPT·Claude·Gemini 연동 테스트."""

"""LLM 서비스 테스트."""

import os

import pytest

from backend.services.openai_service import call_openai
from backend.services.prompt_builder import build_answer_prompt


def test_build_answer_prompt() -> None:
    """질문이 프롬프트에 포함되는지 확인한다."""
    question = "정부는 최저임금을 인상해야 하는가?"

    prompt = build_answer_prompt(question)

    assert question in prompt
    assert "질문:" in prompt


def test_build_answer_prompt_rejects_empty_text() -> None:
    """빈 질문을 거부하는지 확인한다."""
    with pytest.raises(ValueError):
        build_answer_prompt("   ")


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY가 없어 통합 테스트를 건너뜁니다.",
)
def test_openai_api_call() -> None:
    """실제 OpenAI API 호출 통합 테스트."""
    result = call_openai(
        "태양광 발전은 태양 에너지를 전기에너지로 변환하는가?"
    )

    assert result["provider"] == "OPENAI"
    assert result["api_status"] == "SUCCESS"
    assert isinstance(result["answer"], str)
    assert result["answer"].strip()
    assert result["latency_ms"] >= 0