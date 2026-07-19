"""
backend/main.py
FastAPI 서버 진입점
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import dataset_api

app = FastAPI(title="KoSI API", version="0.1.0")

# Streamlit이 별도 포트(보통 8501)에서 이 API(보통 8000)를 호출하므로 CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dataset_api.router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "KoSI API"}