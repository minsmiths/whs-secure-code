"""관리자 페이지.

모든 라우트는 admin_required 로 보호된다(관리자만 접근, 그 외 403).
- 대시보드: 통계 + 신고 목록 + 사용자/상품 관리
- 사용자 휴면/복구, 상품 차단/해제/삭제
"""
from flask import (
    Blueprint, abort, flash, g, redirect, render_template, request, url_for
)

from .db import get_db
from .security import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _audit(db, action: str, target_type: str = None, target_id: int = None,
           detail: str = "") -> None:
    """관리자 조치를 감사 로그에 기록한다."""
    db.execute(
        "INSERT INTO admin_log (admin_id, action, target_type, target_id, detail) "
        "VALUES (?, ?, ?, ?, ?)",
        (g.user["id"], action, target_type, target_id, detail),
    )


@bp.route("/")
@admin_required
def dashboard():
    db = get_db()

    stats = {
        "users": db.execute("SELECT COUNT(*) AS n FROM user").fetchone()["n"],
        "products": db.execute("SELECT COUNT(*) AS n FROM product").fetchone()["n"],
        "blocked": db.execute(
            "SELECT COUNT(*) AS n FROM product WHERE status = 'blocked'"
        ).fetchone()["n"],
        "reports": db.execute("SELECT COUNT(*) AS n FROM report").fetchone()["n"],
    }

    # 신고 목록 (대상 라벨 포함)
    reports = db.execute(
        "SELECT r.*, u.username AS reporter_name "
        "FROM report r JOIN user u ON r.reporter_id = u.id "
        "ORDER BY r.created_at DESC LIMIT 50"
    ).fetchall()
    reports_view = []
    for r in reports:
        if r["target_type"] == "product":
            t = db.execute(
                "SELECT title FROM product WHERE id = ?", (r["target_id"],)
            ).fetchone()
            label = t["title"] if t else "(삭제된 상품)"
        else:
            t = db.execute(
                "SELECT username FROM user WHERE id = ?", (r["target_id"],)
            ).fetchone()
            label = t["username"] if t else "(삭제된 사용자)"
        reports_view.append({**dict(r), "label": label})

    users = db.execute(
        "SELECT u.*, "
        "(SELECT COUNT(*) FROM report r WHERE r.target_type='user' AND r.target_id=u.id) AS report_count "
        "FROM user u ORDER BY u.id"
    ).fetchall()

    products = db.execute(
        "SELECT p.*, u.username AS seller_name, "
        "(SELECT COUNT(*) FROM report r WHERE r.target_type='product' AND r.target_id=p.id) AS report_count "
        "FROM product p JOIN user u ON p.seller_id = u.id "
        "ORDER BY p.created_at DESC"
    ).fetchall()

    logs = db.execute(
        "SELECT l.*, u.username AS admin_name "
        "FROM admin_log l JOIN user u ON l.admin_id = u.id "
        "ORDER BY l.id DESC LIMIT 30"
    ).fetchall()

    return render_template(
        "admin/dashboard.html",
        stats=stats, reports=reports_view, users=users, products=products,
        logs=logs,
    )


@bp.route("/user/<int:user_id>/toggle-active", methods=("POST",))
@admin_required
def toggle_user(user_id: int):
    db = get_db()
    user = db.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        abort(404)
    if user["is_admin"]:
        flash("관리자 계정은 변경할 수 없습니다.")
        return redirect(url_for("admin.dashboard"))
    new_state = 0 if user["is_active"] else 1
    db.execute("UPDATE user SET is_active = ? WHERE id = ?", (new_state, user_id))
    _audit(db, "user_activate" if new_state else "user_dormant",
           "user", user_id, user["username"])
    db.commit()
    flash(f"{user['username']} 계정을 {'활성화' if new_state else '휴면 처리'}했습니다.")
    return redirect(url_for("admin.dashboard"))


@bp.route("/product/<int:product_id>/status", methods=("POST",))
@admin_required
def product_status(product_id: int):
    """action=block|unblock|delete"""
    db = get_db()
    product = db.execute("SELECT * FROM product WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        abort(404)

    action = request.form.get("action")
    if action == "block":
        db.execute("UPDATE product SET status = 'blocked' WHERE id = ?", (product_id,))
        msg = "상품을 차단했습니다."
    elif action == "unblock":
        db.execute("UPDATE product SET status = 'active' WHERE id = ?", (product_id,))
        msg = "상품 차단을 해제했습니다."
    elif action == "delete":
        db.execute("DELETE FROM product WHERE id = ?", (product_id,))
        msg = "상품을 삭제했습니다."
    else:
        abort(400)
    _audit(db, f"product_{action}", "product", product_id, product["title"])
    db.commit()
    flash(msg)
    return redirect(url_for("admin.dashboard"))
