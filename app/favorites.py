"""찜(좋아요) 기능."""
from flask import (
    Blueprint, g, jsonify, redirect, render_template, request, url_for
)

from .db import get_db
from .security import login_required

bp = Blueprint("favorites", __name__, url_prefix="/favorites")


@bp.route("/toggle/<int:product_id>", methods=("POST",))
@login_required
def toggle(product_id: int):
    """찜 토글. 이미 찜했으면 해제, 아니면 추가."""
    db = get_db()
    product = db.execute(
        "SELECT id FROM product WHERE id = ?", (product_id,)
    ).fetchone()
    if product is None:
        return jsonify({"error": "not_found"}), 404

    existing = db.execute(
        "SELECT id FROM favorite WHERE user_id = ? AND product_id = ?",
        (g.user["id"], product_id),
    ).fetchone()

    if existing:
        db.execute("DELETE FROM favorite WHERE id = ?", (existing["id"],))
        favorited = False
    else:
        db.execute(
            "INSERT INTO favorite (user_id, product_id) VALUES (?, ?)",
            (g.user["id"], product_id),
        )
        favorited = True
    db.commit()

    count = db.execute(
        "SELECT COUNT(*) AS c FROM favorite WHERE product_id = ?", (product_id,)
    ).fetchone()["c"]

    # fetch API 호출이면 JSON, 일반 폼 제출이면 이전 페이지로 리다이렉트
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify({"favorited": favorited, "count": count})

    return redirect(request.referrer or url_for("products.detail", product_id=product_id))


@bp.route("/")
@login_required
def index():
    """내 찜 목록."""
    db = get_db()
    products = db.execute(
        "SELECT p.*, u.username AS seller_name, u.rating AS seller_rating "
        "FROM favorite f "
        "JOIN product p ON f.product_id = p.id "
        "JOIN user u ON p.seller_id = u.id "
        "WHERE f.user_id = ? AND p.status = 'active' "
        "ORDER BY f.created_at DESC",
        (g.user["id"],),
    ).fetchall()
    fav_ids = {p["id"] for p in products}
    return render_template("favorites/index.html", products=products, favorite_ids=fav_ids)
