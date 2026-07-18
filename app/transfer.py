"""유저 간 송금 (잔액 이체).

보안 포인트:
- 금액은 양의 정수만 허용 (음수/0/문자 차단) → 잔액 탈취·오버플로우 방지
- 본인에게 송금 불가, 받는 사람 존재 & 활성 계정 확인
- 원자적 처리: 보내는 사람 잔액을 'balance >= amount' 조건부 UPDATE로 차감하여
  동시 요청에서도 잔액이 음수가 되지 않도록 함 (이중지불 방지). 실패 시 전체 롤백.
"""
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

from .db import get_db
from .security import login_required

bp = Blueprint("transfer", __name__, url_prefix="/transfer")

MAX_AMOUNT = 100_000_000


@bp.route("/", methods=("GET", "POST"))
@login_required
def index():
    db = get_db()

    if request.method == "POST":
        to_username = request.form.get("to_username", "").strip()
        amount_raw = request.form.get("amount", "").strip()

        error = None
        amount = None
        try:
            amount = int(amount_raw)
        except (TypeError, ValueError):
            error = "금액은 숫자여야 합니다."
        else:
            if amount <= 0:
                error = "송금 금액은 1원 이상이어야 합니다."
            elif amount > MAX_AMOUNT:
                error = "송금 금액이 너무 큽니다."

        receiver = None
        if error is None:
            receiver = db.execute(
                "SELECT id, is_active FROM user WHERE username = ?", (to_username,)
            ).fetchone()
            if receiver is None:
                error = "받는 사람을 찾을 수 없습니다."
            elif receiver["id"] == g.user["id"]:
                error = "본인에게는 송금할 수 없습니다."
            elif receiver["is_active"] == 0:
                error = "휴면 계정에는 송금할 수 없습니다."

        if error is None:
            # 조건부 차감: 잔액이 충분할 때만 차감되어 rowcount=1
            cur = db.execute(
                "UPDATE user SET balance = balance - ? WHERE id = ? AND balance >= ?",
                (amount, g.user["id"], amount),
            )
            if cur.rowcount != 1:
                db.rollback()
                flash("잔액이 부족합니다.")
                return redirect(url_for("transfer.index"))

            db.execute(
                "UPDATE user SET balance = balance + ? WHERE id = ?",
                (amount, receiver["id"]),
            )
            db.execute(
                "INSERT INTO transfer (sender_id, receiver_id, amount) VALUES (?, ?, ?)",
                (g.user["id"], receiver["id"], amount),
            )
            db.commit()
            flash(f"{to_username}님에게 {amount:,}원을 송금했습니다.")
            return redirect(url_for("transfer.index"))

        flash(error)

    # 최신 잔액 다시 조회
    me = db.execute("SELECT balance FROM user WHERE id = ?", (g.user["id"],)).fetchone()

    history = db.execute(
        "SELECT t.*, "
        "su.username AS sender_name, ru.username AS receiver_name "
        "FROM transfer t "
        "JOIN user su ON t.sender_id = su.id "
        "JOIN user ru ON t.receiver_id = ru.id "
        "WHERE t.sender_id = ? OR t.receiver_id = ? "
        "ORDER BY t.created_at DESC LIMIT 30",
        (g.user["id"], g.user["id"]),
    ).fetchall()

    prefill = request.args.get("to", "").strip()
    return render_template(
        "transfer/index.html",
        balance=me["balance"], history=history, prefill=prefill,
    )
