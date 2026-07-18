"""데모용 초기 데이터 삽입 CLI: `flask seed`.

테스트/시연을 위한 관리자 계정과 샘플 테니스 용품을 생성한다.
관리자 비밀번호는 환경 변수 ADMIN_PASSWORD 로 지정할 수 있다(기본값 제공).
"""
import os

import click
from werkzeug.security import generate_password_hash

from .db import get_db


SAMPLE_PRODUCTS = [
    ("윌슨 프로스태프 97 v14", "거의 새것, 그립 교체 1회. 헤드 297g", 210000, "라켓"),
    ("바볼랏 RPM 블라스트 스트링 12m", "미개봉 컷팩", 15000, "스트링"),
    ("아식스 코트FF3 테니스화 275mm", "3개월 착용, 클레이/하드 겸용", 80000, "테니스화"),
    ("헤드 투어팀 백팩", "라켓 2개 수납, 신발 칸 분리", 45000, "가방"),
    ("던롭 포트폴리오 테니스공 3개입", "미개봉 3캔 일괄", 21000, "테니스공"),
    ("나이키 드라이핏 반팔 티 L", "여름용, 착용감 좋음", 18000, "의류"),
]


@click.command("seed")
def seed_command() -> None:
    db = get_db()

    admin_pw = os.environ.get("ADMIN_PASSWORD", "admin-Deuce-2026!")
    # 관리자 계정
    admin = db.execute("SELECT id FROM user WHERE username = 'admin'").fetchone()
    if admin is None:
        db.execute(
            "INSERT INTO user (username, password_hash, bio, balance, is_admin) "
            "VALUES (?, ?, ?, ?, 1)",
            ("admin", generate_password_hash(admin_pw), "플랫폼 관리자입니다.", 0),
        )
        db.commit()
        click.echo(f"관리자 계정 생성: admin / {admin_pw}")

    # 샘플 판매자
    seller = db.execute("SELECT id FROM user WHERE username = 'tennislover'").fetchone()
    if seller is None:
        db.execute(
            "INSERT INTO user (username, password_hash, bio, balance) VALUES (?, ?, ?, ?)",
            ("tennislover", generate_password_hash("password-1234!"),
             "테니스 6년차, 용품 자주 바꿉니다.", 100000),
        )
        db.commit()
    seller_id = db.execute(
        "SELECT id FROM user WHERE username = 'tennislover'"
    ).fetchone()["id"]

    # 샘플 상품
    count = db.execute("SELECT COUNT(*) AS c FROM product").fetchone()["c"]
    if count == 0:
        for title, desc, price, category in SAMPLE_PRODUCTS:
            db.execute(
                "INSERT INTO product (title, description, price, category, seller_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (title, desc, price, category, seller_id),
            )
        db.commit()
        click.echo(f"샘플 상품 {len(SAMPLE_PRODUCTS)}개 생성 완료")

    click.echo("시드 데이터 준비 완료.")


def init_app(app) -> None:
    app.cli.add_command(seed_command)
