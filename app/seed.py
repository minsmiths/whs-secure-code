"""데모용 초기 데이터 삽입 CLI: `flask seed`."""
import os

import click
from werkzeug.security import generate_password_hash

from .db import get_db


# username, password, bio, region, rating
SAMPLE_USERS = [
    ("minsmith", "password-1234!", "테니스 8년차, 라켓 컬렉터입니다.", "서울 송파구", 4.9),
    ("courtking", "password-1234!", "동호회 운영 중. 용품 자주 바꿔요.", "서울 강남구", 4.7),
    ("baseliner", "password-1234!", "주말 클레이 코트 러버 🎾", "경기 성남시", 4.8),
]

# title, desc, price, category, brand, condition, usage_period, grip, location, seller(username)
SAMPLE_PRODUCTS = [
    ("Yonex EZONE 100 (2022)", "정품, 실사용 6개월. 스크래치 거의 없습니다. 그로밋 양호.",
     180000, "라켓", "Yonex", "A+", "6개월", "G2", "서울 송파구", "minsmith"),
    ("Nike Vapor Pro 테니스화 270", "3개월 착용, 아웃솔 상태 좋음. 하드코트용.",
     85000, "테니스화", "Nike", "A", "3개월", "", "서울 강남구", "courtking"),
    ("Wilson Pro Staff 97 v14", "페더러 모델. 헤드 297g. 그립 교체 1회.",
     210000, "라켓", "Wilson", "A", "1년", "G2", "경기 성남시", "baseliner"),
    ("Babolat RPM Blast 스트링 12m", "미개봉 컷팩. 블랙 1.25mm.",
     15000, "스트링", "Babolat", "S", "미개봉", "", "서울 송파구", "minsmith"),
    ("Head 투어팀 라켓백 (라켓 6개)", "라켓 6개 수납, 신발 칸 분리. 사용감 적음.",
     55000, "가방", "Head", "A", "8개월", "", "서울 강남구", "courtking"),
    ("Nike 드라이핏 반팔 티 L", "여름용 경량, 착용 5회 미만. 화이트.",
     22000, "의류", "Nike", "A+", "1개월", "", "경기 성남시", "baseliner"),
    ("Dunlop Fort 테니스공 3캔", "미개봉 3캔 일괄. 올코트용.",
     21000, "테니스공", "Dunlop", "S", "미개봉", "", "서울 송파구", "minsmith"),
    ("Babolat Pure Aero 2023", "나달 모델. 스핀 최강. 실사용 4개월.",
     195000, "라켓", "Babolat", "A+", "4개월", "G3", "서울 강남구", "courtking"),
]


@click.command("seed")
def seed_command() -> None:
    db = get_db()

    admin_pw = os.environ.get("ADMIN_PASSWORD", "admin-Deuce-2026!")
    admin = db.execute("SELECT id FROM user WHERE username = 'admin'").fetchone()
    if admin is None:
        db.execute(
            "INSERT INTO user (username, password_hash, bio, region, is_admin) "
            "VALUES (?, ?, ?, ?, 1)",
            ("admin", generate_password_hash(admin_pw), "플랫폼 관리자", "서울"),
        )
        db.commit()
        click.echo(f"관리자 계정 생성: admin / {admin_pw}")

    for username, pw, bio, region, rating in SAMPLE_USERS:
        row = db.execute("SELECT id FROM user WHERE username = ?", (username,)).fetchone()
        if row is None:
            db.execute(
                "INSERT INTO user (username, password_hash, bio, region, rating, balance) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (username, generate_password_hash(pw), bio, region, rating, 500000),
            )
    db.commit()

    def uid(name):
        return db.execute("SELECT id FROM user WHERE username = ?", (name,)).fetchone()["id"]

    count = db.execute("SELECT COUNT(*) AS c FROM product").fetchone()["c"]
    if count == 0:
        for (title, desc, price, cat, brand, cond, period, grip, loc, seller) in SAMPLE_PRODUCTS:
            db.execute(
                "INSERT INTO product (title, description, price, category, brand, "
                "condition_grade, usage_period, grip, location, seller_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (title, desc, price, cat, brand, cond, period, grip, loc, uid(seller)),
            )
        db.commit()
        click.echo(f"샘플 상품 {len(SAMPLE_PRODUCTS)}개 생성 완료")

    # 샘플 1:1 채팅방 + 메시지
    ccount = db.execute("SELECT COUNT(*) AS c FROM conversation").fetchone()["c"]
    if ccount == 0:
        def pid(title_like):
            return db.execute(
                "SELECT id, seller_id FROM product WHERE title LIKE ? LIMIT 1",
                (f"%{title_like}%",),
            ).fetchone()

        # minsmith(구매자) ↔ courtking(판매자): Nike Vapor 신발
        shoes = pid("Vapor")
        if shoes:
            cur = db.execute(
                "INSERT INTO conversation (product_id, buyer_id, seller_id) VALUES (?, ?, ?)",
                (shoes["id"], uid("minsmith"), shoes["seller_id"]),
            )
            cid = cur.lastrowid
            convo = [
                ("minsmith", "안녕하세요! 신발 275도 있을까요?"),
                ("courtking", "네 안녕하세요 :) 270만 남아있어요!"),
                ("minsmith", "아 그렇군요. 상태는 어떤가요?"),
                ("courtking", "3개월 신어서 아웃솔 거의 그대로예요 🎾"),
            ]
            for name, body in convo:
                db.execute(
                    "INSERT INTO message (conversation_id, sender_id, body) VALUES (?, ?, ?)",
                    (cid, uid(name), body),
                )

        # baseliner(구매자) ↔ minsmith(판매자): EZONE 라켓
        racket = pid("EZONE")
        if racket:
            cur = db.execute(
                "INSERT INTO conversation (product_id, buyer_id, seller_id) VALUES (?, ?, ?)",
                (racket["id"], uid("baseliner"), racket["seller_id"]),
            )
            cid = cur.lastrowid
            for name, body in [
                ("baseliner", "EZONE 그립 G2 맞나요?"),
                ("minsmith", "네 맞습니다! 오버그립 새로 감아둘게요~"),
            ]:
                db.execute(
                    "INSERT INTO message (conversation_id, sender_id, body) VALUES (?, ?, ?)",
                    (cid, uid(name), body),
                )
        db.commit()

    click.echo("시드 데이터 준비 완료.")


def init_app(app) -> None:
    app.cli.add_command(seed_command)
