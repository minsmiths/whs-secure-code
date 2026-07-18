"""메인/랜딩 페이지."""
from flask import Blueprint, render_template

from .db import get_db

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """홈: 최신 등록 상품 몇 개를 보여준다."""
    db = get_db()
    products = db.execute(
        "SELECT p.*, u.username AS seller_name "
        "FROM product p JOIN user u ON p.seller_id = u.id "
        "WHERE p.status = 'active' "
        "ORDER BY p.created_at DESC LIMIT 8"
    ).fetchall()
    return render_template("index.html", products=products)
