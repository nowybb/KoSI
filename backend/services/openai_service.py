"""OpenAI GPT API 호출 기능."""

"""OpenAI Responses API 호출 서비스."""

from __future__ import annotations

import time
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

from backend.services.prompt_builder import (
    ANSWER_SYSTEM_PROMPT,
    build_answer_prompt,
)
from backend.utils.config import settings


class OpenAIServiceError(RuntimeError):
    """OpenAI 호출이 최종적으로 실패했을 때 발생하는 예외."""


class OpenAIService:
    """OpenAI API 호출을 담당하는 서비스."""

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=30.0,
            # 자체 재시도 로직을 사용하기 위해 SDK 자동 재시도는 끈다.
            max_retries=0,
        )

        self.model = settings.OPENAI_MODEL
        self.max_output_tokens = settings.MAX_TOKENS

    def generate_answer(
        self,
        question: str,
        *,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """질문을 OpenAI 모델에 전달하고 공통 형식으로 반환한다.

        Args:
            question: 평가할 한국어 질문.
            max_retries: 일시적 오류 발생 시 최대 시도 횟수.

        Returns:
            모델명, 응답, 토큰, 지연시간 등을 포함한 딕셔너리.

        Raises:
            ValueError: 잘못된 입력값이 전달된 경우.
            OpenAIServiceError: 모든 재시도가 실패한 경우.
        """
        if max_retries < 1:
            raise ValueError("max_retries는 1 이상이어야 합니다.")

        prompt = build_answer_prompt(question)
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            started_at = time.perf_counter()

            try:
                response = self.client.responses.create(
                    model=self.model,
                    instructions=ANSWER_SYSTEM_PROMPT,
                    input=prompt,
                    max_output_tokens=self.max_output_tokens,
                )

                latency_ms = round(
                    (time.perf_counter() - started_at) * 1000
                )

                usage = getattr(response, "usage", None)

                input_tokens = (
                    getattr(usage, "input_tokens", 0) if usage else 0
                )
                output_tokens = (
                    getattr(usage, "output_tokens", 0) if usage else 0
                )

                answer = response.output_text.strip()

                if not answer:
                    raise OpenAIServiceError(
                        "OpenAI가 비어 있는 응답을 반환했습니다."
                    )

                return {
                    "provider": "OPENAI",
                    "model": getattr(response, "model", self.model),
                    "answer": answer,
                    "raw_response_id": response.id,
                    "prompt_tokens": input_tokens,
                    "completion_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "latency_ms": latency_ms,
                    "finish_reason": self._get_finish_reason(response),
                    "api_status": "SUCCESS",
                    "attempt_count": attempt,
                    "error": None,
                }

            except (
                RateLimitError,
                APITimeoutError,
                APIConnectionError,
            ) as error:
                last_error = error

                if attempt >= max_retries:
                    break

                # 1초 → 2초 → 4초 방식의 지수 백오프
                wait_seconds = 2 ** (attempt - 1)
                time.sleep(wait_seconds)

            except APIStatusError as error:
                # 5xx 오류만 재시도하고 인증 오류 등은 즉시 종료한다.
                if error.status_code >= 500:
                    last_error = error

                    if attempt >= max_retries:
                        break

                    wait_seconds = 2 ** (attempt - 1)
                    time.sleep(wait_seconds)
                    continue

                raise OpenAIServiceError(
                    f"OpenAI API 요청이 거부되었습니다. "
                    f"status={error.status_code}, "
                    f"message={error.message}"
                ) from error

            except OpenAIServiceError:
                raise

            except Exception as error:
                raise OpenAIServiceError(
                    f"예상하지 못한 OpenAI 호출 오류: {error}"
                ) from error

        raise OpenAIServiceError(
            f"OpenAI API 호출이 {max_retries}회 모두 실패했습니다: "
            f"{last_error}"
        ) from last_error

    @staticmethod
    def _get_finish_reason(response: Any) -> str:
        """Responses API의 종료 상태를 공통 문자열로 변환한다."""
        status = getattr(response, "status", None)

        if status == "completed":
            return "stop"

        incomplete_details = getattr(
            response,
            "incomplete_details",
            None,
        )

        reason = getattr(incomplete_details, "reason", None)

        return reason or status or "unknown"


# 간단한 함수형 호출도 지원한다.
_service: OpenAIService | None = None


def call_openai(question: str) -> dict[str, Any]:
    """OpenAIService 싱글턴을 이용해 질문에 대한 답변을 생성한다."""
    global _service

    if _service is None:
        _service = OpenAIService()

    return _service.generate_answer(question)