"""SQLite 데이터베이스 접근 헬퍼.

- 요청(request)마다 커넥션 하나를 재사용하고 (flask.g), 요청 종료 시 닫는다.
- 모든 쿼리는 파라미터 바인딩(?)을 사용한다 → SQL Injection 방지.
- row_factory 를 sqlite3.Row 로 두어 컬럼명을 키로 접근할 수 있게 한다.
"""
import os
import sqlite3

import click
from flask import current_app, g


def get_db() -> sqlite3.Connection:
    """현재 요청에 연결된 DB 커넥션을 반환한다 (없으면 생성)."""
    if "db" not in g:
        db_path = os.path.join(current_app.instance_path, current_app.config["DB_NAME"])
        g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        # 외래키 제약을 매 커넥션마다 활성화 (SQLite 기본값이 OFF라서 필요)
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exception=None) -> None:
    """요청 종료 시 커넥션을 닫는다."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    """schema.sql 을 실행해 테이블을 (재)생성한다."""
    db = get_db()
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with current_app.open_resource(os.path.relpath(schema_path, current_app.root_path)) as f:
        db.executescript(f.read().decode("utf-8"))


@click.command("init-db")
def init_db_command() -> None:
    """`flask init-db` 로 DB를 초기화한다."""
    init_db()
    click.echo("데이터베이스를 초기화했습니다. (deuce_market.sqlite)")


@click.command("reset-db")
def reset_db_command() -> None:
    """`flask reset-db` 로 DB를 초기화하고 샘플 데이터까지 한 번에 넣는다."""
    from .seed import _seed  # 지연 임포트(순환참조 방지)
    init_db()
    _seed()
    click.echo("DB를 초기화하고 샘플 데이터를 넣었습니다.")


def init_app(app) -> None:
    """앱에 DB 관련 훅과 CLI 명령을 등록한다."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(reset_db_command)
