"""Google Gemini API 호출 서비스."""

from __future__ import annotations

import random
import time
from typing import Any

from google import genai
from google.genai import errors, types

from backend.services.prompt_builder import (
    ANSWER_SYSTEM_PROMPT,
    build_answer_prompt,
)
from backend.utils.config import settings


class GeminiServiceError(RuntimeError):
    """Gemini 호출이 최종적으로 실패했을 때 발생하는 예외."""


class GeminiService:
    """Google Gemini API 호출을 담당하는 서비스."""

    RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
    NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404}

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options=types.HttpOptions(
                timeout=30_000,
            ),
        )

        self.model = settings.GEMINI_MODEL
        self.max_output_tokens = settings.MAX_TOKENS

    def generate_answer(
        self,
        question: str,
        *,
        max_retries: int = 5,
    ) -> dict[str, Any]:
        """질문을 Gemini 모델에 전달하고 공통 형식으로 반환한다.

        Args:
            question: 평가할 한국어 질문.
            max_retries: 일시적 오류 발생 시 최대 시도 횟수.

        Returns:
            모델명, 응답, 토큰 수, 지연시간 등을 포함한 딕셔너리.

        Raises:
            ValueError: 입력값이 올바르지 않은 경우.
            GeminiServiceError: Gemini API 호출이 최종적으로 실패한 경우.
        """
        if not isinstance(question, str):
            raise ValueError("question은 문자열이어야 합니다.")

        question = question.strip()

        if not question:
            raise ValueError("question은 비어 있을 수 없습니다.")

        if max_retries < 1:
            raise ValueError("max_retries는 1 이상이어야 합니다.")

        prompt = build_answer_prompt(question)
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            started_at = time.perf_counter()

            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=ANSWER_SYSTEM_PROMPT,
                        max_output_tokens=self.max_output_tokens,
                        temperature=0.0,
                    ),
                )

                latency_ms = round(
                    (time.perf_counter() - started_at) * 1000
                )

                answer = self._extract_answer(response)

                if not answer:
                    raise GeminiServiceError(
                        "Gemini가 비어 있는 응답을 반환했습니다."
                    )

                usage = getattr(response, "usage_metadata", None)

                prompt_tokens = self._get_int_attribute(
                    usage,
                    "prompt_token_count",
                )
                completion_tokens = self._get_completion_tokens(usage)
                total_tokens = self._get_int_attribute(
                    usage,
                    "total_token_count",
                )

                if total_tokens == 0:
                    total_tokens = prompt_tokens + completion_tokens

                return {
                    "provider": "GEMINI",
                    "model": self.model,
                    "answer": answer,
                    "raw_response_id": self._get_response_id(response),
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "latency_ms": latency_ms,
                    "finish_reason": self._get_finish_reason(response),
                    "api_status": "SUCCESS",
                    "attempt_count": attempt,
                    "error": None,
                }

            except errors.APIError as error:
                last_error = error
                status_code = self._get_status_code(error)

                if status_code in self.NON_RETRYABLE_STATUS_CODES:
                    raise GeminiServiceError(
                        self._format_api_error(error)
                    ) from error

                if status_code in self.RETRYABLE_STATUS_CODES:
                    if attempt >= max_retries:
                        break

                    self._wait_before_retry(
                        attempt=attempt,
                        status_code=status_code,
                    )
                    continue

                raise GeminiServiceError(
                    self._format_api_error(error)
                ) from error

            except GeminiServiceError:
                raise

            except (
                TimeoutError,
                ConnectionError,
            ) as error:
                last_error = error

                if attempt >= max_retries:
                    break

                self._wait_before_retry(
                    attempt=attempt,
                    status_code=None,
                )

            except Exception as error:
                raise GeminiServiceError(
                    f"예상하지 못한 Gemini 호출 오류: {error}"
                ) from error

        raise GeminiServiceError(
            f"Gemini API 호출이 {max_retries}회 모두 실패했습니다: "
            f"{last_error}"
        ) from last_error

    @staticmethod
    def _extract_answer(response: Any) -> str:
        """Gemini 응답에서 텍스트를 안전하게 추출한다."""
        try:
            text = response.text
        except (AttributeError, ValueError):
            text = None

        if isinstance(text, str) and text.strip():
            return text.strip()

        candidates = getattr(response, "candidates", None) or []
        answer_parts: list[str] = []

        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []

            for part in parts:
                part_text = getattr(part, "text", None)

                if isinstance(part_text, str) and part_text.strip():
                    answer_parts.append(part_text.strip())

        return "\n".join(answer_parts).strip()

    @staticmethod
    def _get_finish_reason(response: Any) -> str:
        """Gemini 종료 사유를 공통 문자열로 변환한다."""
        candidates = getattr(response, "candidates", None) or []

        if not candidates:
            return "unknown"

        finish_reason = getattr(candidates[0], "finish_reason", None)

        if finish_reason is None:
            return "unknown"

        value = getattr(finish_reason, "value", None)

        if value is not None:
            return str(value).lower()

        name = getattr(finish_reason, "name", None)

        if name is not None:
            return str(name).lower()

        return str(finish_reason).lower()

    @staticmethod
    def _get_response_id(response: Any) -> str | None:
        """응답 식별자가 있으면 문자열로 반환한다."""
        response_id = getattr(response, "response_id", None)

        if response_id is None:
            return None

        return str(response_id)

    @staticmethod
    def _get_status_code(error: errors.APIError) -> int | None:
        """Gemini API 오류의 HTTP 상태 코드를 안전하게 추출한다."""
        status_code = getattr(error, "code", None)

        try:
            return int(status_code)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _get_int_attribute(
        obj: Any,
        attribute_name: str,
    ) -> int:
        """객체의 숫자 속성을 안전하게 정수로 변환한다."""
        if obj is None:
            return 0

        value = getattr(obj, attribute_name, 0)

        if value is None:
            return 0

        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _get_completion_tokens(cls, usage: Any) -> int:
        """SDK 버전별 출력 토큰 필드 차이를 처리한다."""
        candidates_tokens = cls._get_int_attribute(
            usage,
            "candidates_token_count",
        )

        if candidates_tokens:
            return candidates_tokens

        return cls._get_int_attribute(
            usage,
            "response_token_count",
        )

    @staticmethod
    def _wait_before_retry(
        attempt: int,
        status_code: int | None,
    ) -> None:
        """지수 백오프와 jitter를 적용하여 재시도한다."""
        base_seconds = min(2**attempt, 30)
        jitter_seconds = random.uniform(0.0, 1.0)
        wait_seconds = base_seconds + jitter_seconds

        error_label = (
            str(status_code)
            if status_code is not None
            else "network"
        )

        print(
            f"[Gemini] 일시적 오류({error_label}) 발생. "
            f"{wait_seconds:.1f}초 후 재시도합니다."
        )

        time.sleep(wait_seconds)

    @staticmethod
    def _format_api_error(error: errors.APIError) -> str:
        """Gemini API 오류를 읽기 쉬운 메시지로 변환한다."""
        status_code = getattr(error, "code", "unknown")
        message = getattr(error, "message", str(error))

        if status_code == 400:
            guidance = "요청 형식이나 모델 설정을 확인하세요."
        elif status_code == 401:
            guidance = "GEMINI_API_KEY가 올바른지 확인하세요."
        elif status_code == 403:
            guidance = "API 키 권한과 프로젝트 설정을 확인하세요."
        elif status_code == 404:
            guidance = "GEMINI_MODEL 이름과 모델 사용 가능 여부를 확인하세요."
        elif status_code == 408:
            guidance = "요청 시간이 초과되었습니다."
        elif status_code == 429:
            guidance = "무료 할당량 또는 요청 속도 제한을 확인하세요."
        elif status_code == 503:
            guidance = (
                "현재 모델 요청량이 많습니다. "
                "잠시 후 다시 시도하세요."
            )
        elif isinstance(status_code, int) and status_code >= 500:
            guidance = "Gemini 서버에서 일시적인 오류가 발생했습니다."
        else:
            guidance = "Gemini API 설정과 응답 내용을 확인하세요."

        return (
            "Gemini API 요청에 실패했습니다. "
            f"status={status_code}, "
            f"message={message} "
            f"{guidance}"
        )


_service: GeminiService | None = None


def call_gemini(question: str) -> dict[str, Any]:
    """싱글턴 GeminiService를 이용해 질문에 답한다."""
    global _service

    if _service is None:
        _service = GeminiService()

    return _service.generate_answer(question)