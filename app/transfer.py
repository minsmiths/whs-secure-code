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


def _parse_amount(amount_raw: str):
    """금액 문자열을 검증. (amount, None) 또는 (None, 에러메시지)."""
    try:
        amount = int(amount_raw)
    except (TypeError, ValueError):
        return None, "금액은 숫자여야 합니다."
    if amount <= 0:
        return None, "송금 금액은 1원 이상이어야 합니다."
    if amount > MAX_AMOUNT:
        return None, "송금 금액이 너무 큽니다."
    return amount, None


def _execute_transfer(db, sender_id: int, receiver_id: int, amount: int) -> str | None:
    """원자적 송금 실행. 성공 시 None, 실패 시 에러 메시지 반환.

    'balance >= amount' 조건부 차감으로 동시 요청에서도 음수 잔액/이중지불을 막는다.
    """
    cur = db.execute(
        "UPDATE user SET balance = balance - ? WHERE id = ? AND balance >= ?",
        (amount, sender_id, amount),
    )
    if cur.rowcount != 1:
        db.rollback()
        return "잔액이 부족합니다."
    db.execute(
        "UPDATE user SET balance = balance + ? WHERE id = ?", (amount, receiver_id)
    )
    db.execute(
        "INSERT INTO transfer (sender_id, receiver_id, amount) VALUES (?, ?, ?)",
        (sender_id, receiver_id, amount),
    )
    db.commit()
    return None


@bp.route("/", methods=("GET", "POST"))
@login_required
def index():
    db = get_db()

    if request.method == "POST":
        to_username = request.form.get("to_username", "").strip()
        amount, error = _parse_amount(request.form.get("amount", "").strip())

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
            error = _execute_transfer(db, g.user["id"], receiver["id"], amount)

        if error is None:
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


@bp.route("/pay/<int:product_id>", methods=("GET", "POST"))
@login_required
def pay(product_id: int):
    """상품 구매 → 해당 판매자에게 송금하는 확인 페이지.

    받는 사람은 상품의 판매자로 서버에서 결정한다(사용자 입력을 신뢰하지 않음).
    """
    db = get_db()
    product = db.execute(
        "SELECT p.*, u.username AS seller_name, u.is_active AS seller_active "
        "FROM product p JOIN user u ON p.seller_id = u.id WHERE p.id = ?",
        (product_id,),
    ).fetchone()

    if product is None or product["status"] == "blocked":
        flash("존재하지 않는 상품입니다.")
        return redirect(url_for("products.index"))
    if product["seller_id"] == g.user["id"]:
        flash("본인 상품은 구매할 수 없습니다.")
        return redirect(url_for("products.detail", product_id=product_id))

    if request.method == "POST":
        amount, error = _parse_amount(request.form.get("amount", "").strip())
        if error is None and product["seller_active"] == 0:
            error = "휴면 계정에는 송금할 수 없습니다."
        if error is None:
            error = _execute_transfer(db, g.user["id"], product["seller_id"], amount)
        if error is None:
            flash(f"{product['seller_name']}님에게 {amount:,}원을 송금했습니다.")
            return redirect(url_for("transfer.index"))
        flash(error)

    me = db.execute("SELECT balance FROM user WHERE id = ?", (g.user["id"],)).fetchone()
    return render_template("transfer/pay.html", product=product, balance=me["balance"])
