"""가벼운 자동 마이그레이션.

git pull 등으로 코드가 갱신되었지만 기존 DB 파일에 새 컬럼이 없을 때,
서버 시작 시 빠진 컬럼을 자동으로 추가한다(데이터 보존, 추가형 변경만 대상).

- 존재하지 않는 테이블은 건너뛴다(최초엔 `flask init-db` 필요).
- ADD COLUMN 만 수행하므로 기존 데이터는 유지된다.
"""
import os
import sqlite3

# 테이블별로 '있어야 하는 컬럼: 컬럼 정의'
EXPECTED_COLUMNS = {
    "user": {
        "region": "TEXT NOT NULL DEFAULT ''",
        "rating": "REAL NOT NULL DEFAULT 5.0",
        "balance": "INTEGER NOT NULL DEFAULT 0",
        "is_active": "INTEGER NOT NULL DEFAULT 1",
        "is_admin": "INTEGER NOT NULL DEFAULT 0",
    },
    "product": {
        "brand": "TEXT NOT NULL DEFAULT ''",
        "condition_grade": "TEXT NOT NULL DEFAULT ''",
        "usage_period": "TEXT NOT NULL DEFAULT ''",
        "grip": "TEXT NOT NULL DEFAULT ''",
        "location": "TEXT NOT NULL DEFAULT ''",
    },
    "message": {
        "image_path": "TEXT",
        "is_deleted": "INTEGER NOT NULL DEFAULT 0",
        "edited_at": "TEXT",
    },
}


def run(app) -> None:
    db_path = os.path.join(app.instance_path, app.config["DB_NAME"])
    if not os.path.exists(db_path):
        return  # 아직 init-db 전 → 스킵

    conn = sqlite3.connect(db_path)
    try:
        added = []
        for table, cols in EXPECTED_COLUMNS.items():
            info = conn.execute(f"PRAGMA table_info({table})").fetchall()
            if not info:
                continue  # 테이블 자체가 없음 → init-db 필요
            existing = {row[1] for row in info}
            for col, decl in cols.items():
                if col not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
                    added.append(f"{table}.{col}")
        if added:
            conn.commit()
            app.logger.info("자동 마이그레이션: 컬럼 추가 %s", ", ".join(added))
    except sqlite3.Error as exc:
        app.logger.warning("자동 마이그레이션 건너뜀: %s", exc)
    finally:
        conn.close()
