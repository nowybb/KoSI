"""
backend/database/database.py
DB 연결 관리
"""
import sqlite3
import uuid
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "kosi.db")


def get_connection():
    """DB 커넥션을 반환한다. 외래키 제약조건 활성화, dict처럼 접근 가능하게 row_factory 설정."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def gen_id() -> str:
    """UUID 문자열 생성 (모든 테이블의 PK로 사용)"""
    return str(uuid.uuid4())


class DatabaseSession:
    """with 문으로 사용하는 커넥션 컨텍스트 매니저.
    사용 예:
        with DatabaseSession() as conn:
            conn.execute(...)
    """
    def __enter__(self):
        self.conn = get_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.conn.close()