"""전체 채팅 (실시간 소켓은 이후 단계에서 추가 예정, 현재는 폼 기반)."""
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

from .db import get_db
from .security import login_required

bp = Blueprint("chat", __name__, url_prefix="/chat")

MAX_MESSAGE_LEN = 500


@bp.route("/", methods=("GET", "POST"))
@login_required
def room():
    """전체 채팅방: 최근 메시지를 보여주고 새 메시지를 전송한다."""
    db = get_db()

    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if not body:
            flash("메시지를 입력하세요.")
        elif len(body) > MAX_MESSAGE_LEN:
            flash(f"메시지는 {MAX_MESSAGE_LEN}자 이하여야 합니다.")
        else:
            db.execute(
                "INSERT INTO message (sender_id, recipient_id, body) "
                "VALUES (?, NULL, ?)",
                (g.user["id"], body),
            )
            db.commit()
        return redirect(url_for("chat.room"))

    messages = db.execute(
        "SELECT m.*, u.username AS sender_name "
        "FROM message m JOIN user u ON m.sender_id = u.id "
        "WHERE m.recipient_id IS NULL "
        "ORDER BY m.created_at ASC "
        "LIMIT 200"
    ).fetchall()

    return render_template("chat/room.html", messages=messages)
