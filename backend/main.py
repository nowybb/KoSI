# backend/main.py
# FastAPI 서버 진입점

from backend.utils.config import validate_settings

validate_settings()

print("Configuration Loaded Successfully")