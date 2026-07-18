"""상품 등록 / 조회 / 상세 / 수정 / 삭제."""
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

from .db import get_db
from .security import login_required
from .uploads import save_image

bp = Blueprint("products", __name__, url_prefix="/products")

CATEGORIES = ["라켓", "스트링", "테니스화", "의류", "가방", "테니스공", "액세서리", "기타"]
CONDITIONS = ["S", "A+", "A", "B+", "B", "C"]


def _favorite_ids() -> set:
    """현재 로그인 유저가 찜한 상품 id 집합 (비로그인 시 빈 집합)."""
    if g.user is None:
        return set()
    rows = get_db().execute(
        "SELECT product_id FROM favorite WHERE user_id = ?", (g.user["id"],)
    ).fetchall()
    return {r["product_id"] for r in rows}


@bp.route("/")
def index():
    """전체 상품 목록 + 검색 + 카테고리 필터."""
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    db = get_db()

    sql = (
        "SELECT p.*, u.username AS seller_name, u.rating AS seller_rating "
        "FROM product p JOIN user u ON p.seller_id = u.id "
        "WHERE p.status = 'active'"
    )
    params: list = []

    if query:
        sql += " AND (p.title LIKE ? OR p.description LIKE ? OR p.brand LIKE ?)"
        like = f"%{query}%"
        params.extend([like, like, like])

    if category and category in CATEGORIES:
        sql += " AND p.category = ?"
        params.append(category)

    sql += " ORDER BY p.created_at DESC"
    products = db.execute(sql, params).fetchall()

    return render_template(
        "products/index.html",
        products=products,
        categories=CATEGORIES,
        query=query,
        selected_category=category,
        favorite_ids=_favorite_ids(),
    )


@bp.route("/<int:product_id>")
def detail(product_id: int):
    db = get_db()
    product = db.execute(
        "SELECT p.*, u.username AS seller_name, u.rating AS seller_rating, "
        "u.region AS seller_region "
        "FROM product p JOIN user u ON p.seller_id = u.id "
        "WHERE p.id = ?",
        (product_id,),
    ).fetchone()

    if product is None or product["status"] == "blocked":
        flash("존재하지 않거나 차단된 상품입니다.")
        return redirect(url_for("products.index"))

    fav_count = db.execute(
        "SELECT COUNT(*) AS c FROM favorite WHERE product_id = ?", (product_id,)
    ).fetchone()["c"]

    return render_template(
        "products/detail.html",
        product=product,
        is_favorited=product_id in _favorite_ids(),
        fav_count=fav_count,
    )


@bp.route("/new", methods=("GET", "POST"))
@login_required
def new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        price_raw = request.form.get("price", "").strip()
        category = request.form.get("category", "기타").strip()
        brand = request.form.get("brand", "").strip()[:40]
        condition_grade = request.form.get("condition_grade", "").strip()
        usage_period = request.form.get("usage_period", "").strip()[:40]
        grip = request.form.get("grip", "").strip()[:20]
        location = request.form.get("location", "").strip()[:60]

        error = None
        price = None

        if not title:
            error = "상품명을 입력하세요."
        elif len(title) > 100:
            error = "상품명은 100자 이하여야 합니다."
        elif category not in CATEGORIES:
            error = "올바른 카테고리를 선택하세요."
        elif condition_grade and condition_grade not in CONDITIONS:
            error = "올바른 상태 등급을 선택하세요."
        else:
            try:
                price = int(price_raw)
            except (TypeError, ValueError):
                error = "가격은 숫자여야 합니다."
            else:
                if price < 0:
                    error = "가격은 0 이상이어야 합니다."
                elif price > 100_000_000:
                    error = "가격이 너무 큽니다."

        image_path = None
        if error is None:
            try:
                image_path = save_image(request.files.get("image"))
            except ValueError as exc:
                error = str(exc)

        if error is None:
            db = get_db()
            db.execute(
                "INSERT INTO product (title, description, price, category, brand, "
                "condition_grade, usage_period, grip, location, image_path, seller_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (title, description, price, category, brand, condition_grade,
                 usage_period, grip, location, image_path, g.user["id"]),
            )
            db.commit()
            flash("상품을 등록했습니다.")
            return redirect(url_for("products.mine"))

        flash(error)

    return render_template(
        "products/new.html", categories=CATEGORIES, conditions=CONDITIONS
    )


@bp.route("/mine")
@login_required
def mine():
    db = get_db()
    products = db.execute(
        "SELECT * FROM product WHERE seller_id = ? ORDER BY created_at DESC",
        (g.user["id"],),
    ).fetchall()
    return render_template("products/mine.html", products=products)


@bp.route("/<int:product_id>/delete", methods=("POST",))
@login_required
def delete(product_id: int):
    db = get_db()
    product = db.execute(
        "SELECT * FROM product WHERE id = ?", (product_id,)
    ).fetchone()

    if product is None:
        flash("존재하지 않는 상품입니다.")
        return redirect(url_for("products.mine"))

    # 소유자 검증(IDOR 방지): 관리자가 아니면 본인 상품만 삭제 가능
    if product["seller_id"] != g.user["id"] and not g.user["is_admin"]:
        flash("삭제 권한이 없습니다.")
        return redirect(url_for("products.mine"))

    db.execute("DELETE FROM product WHERE id = ?", (product_id,))
    db.commit()
    flash("상품을 삭제했습니다.")
    return redirect(url_for("products.mine"))
