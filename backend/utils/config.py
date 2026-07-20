import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")

    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.3"))
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1000"))

    APP_ENV = os.getenv("APP_ENV", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()


def validate_api_key(provider: str) -> None:
    """지정한 제공자의 API 키가 설정됐는지 검증한다."""
    api_keys = {
        "openai": settings.OPENAI_API_KEY,
        "anthropic": settings.ANTHROPIC_API_KEY,
        "gemini": settings.GEMINI_API_KEY,
    }

    normalized_provider = provider.strip().lower()

    if normalized_provider not in api_keys:
        raise ValueError(
            "provider는 openai, anthropic, gemini 중 하나여야 합니다."
        )

    if not api_keys[normalized_provider]:
        env_names = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
        }

        raise RuntimeError(
            f"{env_names[normalized_provider]}가 설정되지 않았습니다."
        )


def validate_settings() -> None:
    """모든 API 키를 한꺼번에 검증한다."""
    for provider in ("openai", "anthropic", "gemini"):
        validate_api_key(provider)