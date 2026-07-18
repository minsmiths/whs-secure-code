"""메인/홈 페이지."""
from flask import Blueprint, g, render_template

from .db import get_db

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """홈: 인사말 + 카테고리 + 최신 상품 피드."""
    db = get_db()
    products = db.execute(
        "SELECT p.*, u.username AS seller_name, u.rating AS seller_rating "
        "FROM product p JOIN user u ON p.seller_id = u.id "
        "WHERE p.status = 'active' "
        "ORDER BY p.created_at DESC LIMIT 20"
    ).fetchall()

    favorite_ids = set()
    if g.user is not None:
        rows = db.execute(
            "SELECT product_id FROM favorite WHERE user_id = ?", (g.user["id"],)
        ).fetchall()
        favorite_ids = {r["product_id"] for r in rows}

    categories = ["라켓", "테니스화", "의류", "가방", "스트링", "테니스공"]
    return render_template(
        "index.html",
        products=products,
        categories=categories,
        favorite_ids=favorite_ids,
    )
