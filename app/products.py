"""상품 등록 / 조회 / 상세 / 수정 / 삭제."""
import os
import secrets

from flask import (
    Blueprint, current_app, flash, g, redirect, render_template, request, url_for
)
from werkzeug.utils import secure_filename

from .db import get_db
from .security import login_required

bp = Blueprint("products", __name__, url_prefix="/products")

CATEGORIES = ["라켓", "스트링", "테니스화", "의류", "가방", "테니스공", "액세서리", "기타"]


def _allowed_image(filename: str) -> bool:
    """확장자 화이트리스트 검사."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def _save_image(file_storage) -> str | None:
    """업로드 이미지를 안전하게 저장하고 상대 경로를 반환한다.

    - 확장자 화이트리스트 검사
    - 파일명을 무작위로 재생성 (원본 파일명 신뢰하지 않음 → 경로 조작 방지)
    """
    if not file_storage or file_storage.filename == "":
        return None
    if not _allowed_image(file_storage.filename):
        raise ValueError("허용되지 않은 이미지 형식입니다. (png, jpg, jpeg, gif, webp)")

    ext = secure_filename(file_storage.filename).rsplit(".", 1)[1].lower()
    random_name = f"{secrets.token_hex(16)}.{ext}"
    save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], random_name)
    file_storage.save(save_path)
    # 템플릿에서 url_for('static', ...) 로 접근할 상대 경로
    return f"uploads/{random_name}"


@bp.route("/")
def index():
    """전체 상품 목록 + 검색."""
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    db = get_db()

    sql = (
        "SELECT p.*, u.username AS seller_name "
        "FROM product p JOIN user u ON p.seller_id = u.id "
        "WHERE p.status = 'active'"
    )
    params: list = []

    if query:
        # LIKE 검색도 파라미터 바인딩으로 처리 (SQL Injection 방지)
        sql += " AND (p.title LIKE ? OR p.description LIKE ?)"
        like = f"%{query}%"
        params.extend([like, like])

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
    )


@bp.route("/<int:product_id>")
def detail(product_id: int):
    db = get_db()
    product = db.execute(
        "SELECT p.*, u.username AS seller_name "
        "FROM product p JOIN user u ON p.seller_id = u.id "
        "WHERE p.id = ?",
        (product_id,),
    ).fetchone()

    if product is None or product["status"] == "blocked":
        flash("존재하지 않거나 차단된 상품입니다.")
        return redirect(url_for("products.index"))

    return render_template("products/detail.html", product=product)


@bp.route("/new", methods=("GET", "POST"))
@login_required
def new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        price_raw = request.form.get("price", "").strip()
        category = request.form.get("category", "기타").strip()

        error = None
        price = None

        if not title:
            error = "상품명을 입력하세요."
        elif len(title) > 100:
            error = "상품명은 100자 이하여야 합니다."
        elif category not in CATEGORIES:
            error = "올바른 카테고리를 선택하세요."
        else:
            # 가격: 정수, 음수 불가, 상한 검증
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
                image_path = _save_image(request.files.get("image"))
            except ValueError as exc:
                error = str(exc)

        if error is None:
            db = get_db()
            db.execute(
                "INSERT INTO product (title, description, price, category, "
                "image_path, seller_id) VALUES (?, ?, ?, ?, ?, ?)",
                (title, description, price, category, image_path, g.user["id"]),
            )
            db.commit()
            flash("상품을 등록했습니다.")
            return redirect(url_for("products.mine"))

        flash(error)

    return render_template("products/new.html", categories=CATEGORIES)


@bp.route("/mine")
@login_required
def mine():
    """내가 등록한 상품 관리."""
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

    # 소유자 검증 (IDOR 방지): 관리자가 아니면 본인 상품만 삭제 가능
    if product["seller_id"] != g.user["id"] and not g.user["is_admin"]:
        flash("삭제 권한이 없습니다.")
        return redirect(url_for("products.mine"))

    db.execute("DELETE FROM product WHERE id = ?", (product_id,))
    db.commit()
    flash("상품을 삭제했습니다.")
    return redirect(url_for("products.mine"))
