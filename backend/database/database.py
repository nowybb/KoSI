# backend/database/database.py
# DB 연결

"""
KoSI - DB 연결 헬퍼

역할:
    - SQLite(kosi.db)에 연결하는 통로를 제공한다.
    - 이 파일 자체는 테이블 구조나 데이터를 다루지 않는다 (그건 migration.py / seed.py / crud.py 몫).
    - dataset_api.py, seed.py, crud.py 등 DB를 쓰는 모든 코드가 이 파일을 통해서만 연결한다.

제공 기능:
    - get_connection()     : sqlite3.Connection 하나를 얻는다.
    - gen_id(prefix)        : UUID 기반 고유 ID 문자열을 만든다. (예: q_a1b2c3d4)
    - DatabaseSession       : with 구문으로 연결을 열고/커밋하고/닫는 걸 자동 처리하는 컨텍스트 매니저.
"""

import sqlite3
import uuid
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "kosi.db")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    SQLite 커넥션을 하나 생성해서 반환한다.

    - row_factory를 sqlite3.Row로 설정해서, 조회 결과를 dict처럼 컬럼명으로 접근 가능하게 한다.
        예: row["question_text"]  (row[0] 같은 인덱스 접근 대신)
    - foreign_keys를 켜서 migration.py에서 정의한 FK/CASCADE 제약이 실제로 동작하게 한다.
        (SQLite는 기본적으로 FK 제약이 꺼져 있어서, 연결할 때마다 켜줘야 함)
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"DB 파일이 없습니다: {db_path}\n"
            f"먼저 'python migration.py'를 실행해서 스키마를 생성하세요."
        )

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def gen_id(prefix: str = "") -> str:
    """
    UUID 기반 고유 ID를 생성한다.

    prefix를 주면 어떤 테이블의 ID인지 눈으로 구분하기 쉬워진다.
        gen_id("q")     -> "q_3f9a1c2b8e7d4a5f"
        gen_id("eval")  -> "eval_3f9a1c2b8e7d4a5f"
        gen_id()        -> "3f9a1c2b8e7d4a5f"

    API명세서.md에는 evaluationId 형식이 eval_{YYYYMMDD}_{seq} 로 되어 있는데,
    이건 별도의 evaluation_id 생성 함수(create_evaluation 쪽)에서 처리하고,
    여기 gen_id()는 question_id/response_id 등 나머지 테이블의 범용 PK 생성용이다.
    """
    short_uuid = uuid.uuid4().hex[:16]
    return f"{prefix}_{short_uuid}" if prefix else short_uuid


@contextmanager
def DatabaseSession(db_path: str = DB_PATH):
    """
    with DatabaseSession() as conn: 형태로 사용하는 컨텍스트 매니저.

    - 정상 종료되면 자동으로 commit() 후 close()
    - 예외가 발생하면 rollback() 후 close() (에러를 그대로 다시 던짐)

    사용 예:
        with DatabaseSession() as conn:
            conn.execute(
                "INSERT INTO questions (question_id, question_text, ...) VALUES (?, ?, ...)",
                (gen_id("q"), "사형제도는 필요한가?", ...)
            )
        # with 블록을 빠져나가는 순간 자동 commit
    """
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()