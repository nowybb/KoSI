"""환경변수와 애플리케이션 설정 관리."""

from dotenv import load_dotenv
import os

load_dotenv()


class Settings:

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")

    TEMPERATURE = float(os.getenv("TEMPERATURE", 0.3))
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", 1000))


settings = Settings()


def validate_settings():

    missing = []

    if not settings.OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")

    if not settings.ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")

    if not settings.GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")

    if missing:
        raise RuntimeError(
            f"Missing environment variables: {', '.join(missing)}"
        )