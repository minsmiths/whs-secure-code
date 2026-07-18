"""신고 / 자동 차단.

- 상품 또는 사용자를 사유와 함께 신고
- 같은 사람이 같은 대상을 중복 신고할 수 없음 (DB UNIQUE 제약)
- 누적 신고 수가 임계값(REPORT_BLOCK_THRESHOLD) 이상이면:
    상품 → status='blocked' (목록/상세에서 숨김)
    사용자 → is_active=0 (휴면 계정 전환, 다음 요청에서 자동 로그아웃)
"""
import sqlite3

from flask import (
    Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for
)

from .db import get_db
from .security import login_required

bp = Blueprint("report", __name__, url_prefix="/report")

VALID_TYPES = ("user", "product")
MAX_REASON_LEN = 500


def _target_label(db, target_type: str, target_id: int):
    """신고 대상이 실제로 존재하는지 확인하고 표시용 이름을 반환."""
    if target_type == "product":
        row = db.execute(
            "SELECT title FROM product WHERE id = ?", (target_id,)
        ).fetchone()
        return row["title"] if row else None
    row = db.execute("SELECT username FROM user WHERE id = ?", (target_id,)).fetchone()
    return row["username"] if row else None


@bp.route("/<target_type>/<int:target_id>", methods=("GET", "POST"))
@login_required
def create(target_type: str, target_id: int):
    if target_type not in VALID_TYPES:
        abort(404)

    db = get_db()
    label = _target_label(db, target_type, target_id)
    if label is None:
        flash("존재하지 않는 대상입니다.")
        return redirect(url_for("main.index"))

    # 자기 자신 / 본인 상품 신고 방지
    if target_type == "user" and target_id == g.user["id"]:
        flash("본인은 신고할 수 없습니다.")
        return redirect(url_for("main.index"))
    if target_type == "product":
        owner = db.execute(
            "SELECT seller_id FROM product WHERE id = ?", (target_id,)
        ).fetchone()
        if owner and owner["seller_id"] == g.user["id"]:
            flash("본인 상품은 신고할 수 없습니다.")
            return redirect(url_for("products.detail", product_id=target_id))

    if request.method == "POST":
        reason = request.form.get("reason", "").strip()
        if not reason:
            flash("신고 사유를 입력하세요.")
            return redirect(request.url)
        if len(reason) > MAX_REASON_LEN:
            flash(f"신고 사유는 {MAX_REASON_LEN}자 이하여야 합니다.")
            return redirect(request.url)

        try:
            db.execute(
                "INSERT INTO report (reporter_id, target_type, target_id, reason) "
                "VALUES (?, ?, ?, ?)",
                (g.user["id"], target_type, target_id, reason),
            )
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            flash("이미 신고한 대상입니다.")
            return redirect(url_for("main.index"))

        _apply_block_if_needed(db, target_type, target_id)
        flash("신고가 접수되었습니다.")
        return redirect(url_for("main.index"))

    return render_template(
        "report/form.html",
        target_type=target_type, target_id=target_id, label=label,
    )


def _apply_block_if_needed(db, target_type: str, target_id: int) -> None:
    threshold = current_app.config["REPORT_BLOCK_THRESHOLD"]
    count = db.execute(
        "SELECT COUNT(*) AS n FROM report WHERE target_type = ? AND target_id = ?",
        (target_type, target_id),
    ).fetchone()["n"]
    if count < threshold:
        return
    if target_type == "product":
        db.execute("UPDATE product SET status = 'blocked' WHERE id = ?", (target_id,))
    else:
        db.execute("UPDATE user SET is_active = 0 WHERE id = ?", (target_id,))
    db.commit()
