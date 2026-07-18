"""1:1 채팅 (구매자 ↔ 판매자).

- 채팅 목록 / 채팅방 / 메시지 전송 / 방 나가기
- 메시지 수정 / 삭제 / 공감 (본인 메시지만 수정·삭제 가능 → IDOR 방지)
모든 라우트는 로그인 필수이며, 채팅방 접근은 '참여자(구매자 또는 판매자)'인지 검증한다.
"""
from datetime import datetime, timezone

from flask import (
    Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for
)

from .db import get_db
from .security import login_required

bp = Blueprint("chat", __name__, url_prefix="/chat")

MAX_MESSAGE_LEN = 1000


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _get_conversation(conv_id: int):
    """채팅방을 가져오되, 현재 유저가 참여자가 아니면 403."""
    conv = get_db().execute(
        "SELECT * FROM conversation WHERE id = ?", (conv_id,)
    ).fetchone()
    if conv is None:
        abort(404)
    if g.user["id"] not in (conv["buyer_id"], conv["seller_id"]):
        abort(403)
    return conv


def _other_side(conv):
    """상대방 역할과 id를 반환."""
    if g.user["id"] == conv["buyer_id"]:
        return "buyer", conv["seller_id"]
    return "seller", conv["buyer_id"]


@bp.route("/")
@login_required
def index():
    """채팅 목록: 내가 참여 중이고 숨기지 않은 방들."""
    db = get_db()
    me = g.user["id"]
    convs = db.execute(
        "SELECT c.*, p.title AS product_title, p.image_path AS product_image, "
        "p.category AS product_category "
        "FROM conversation c JOIN product p ON c.product_id = p.id "
        "WHERE (c.buyer_id = ? AND c.buyer_hidden = 0) "
        "   OR (c.seller_id = ? AND c.seller_hidden = 0)",
        (me, me),
    ).fetchall()

    rooms = []
    for c in convs:
        other_id = c["seller_id"] if me == c["buyer_id"] else c["buyer_id"]
        other = db.execute(
            "SELECT username FROM user WHERE id = ?", (other_id,)
        ).fetchone()
        last = db.execute(
            "SELECT * FROM message WHERE conversation_id = ? "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (c["id"],),
        ).fetchone()
        read_at = c["buyer_read_at"] if me == c["buyer_id"] else c["seller_read_at"]
        if read_at:
            unread = db.execute(
                "SELECT COUNT(*) AS n FROM message WHERE conversation_id = ? "
                "AND sender_id != ? AND created_at > ?",
                (c["id"], me, read_at),
            ).fetchone()["n"]
        else:
            unread = db.execute(
                "SELECT COUNT(*) AS n FROM message WHERE conversation_id = ? "
                "AND sender_id != ?",
                (c["id"], me),
            ).fetchone()["n"]

        rooms.append({
            "id": c["id"],
            "other_name": other["username"] if other else "(탈퇴한 사용자)",
            "product_title": c["product_title"],
            "product_image": c["product_image"],
            "product_category": c["product_category"],
            "last_body": (last["body"] if last and not last["is_deleted"]
                          else ("삭제된 메시지입니다" if last else "대화를 시작해보세요")),
            "last_at": last["created_at"] if last else c["created_at"],
            "unread": unread,
        })

    # 최근 메시지 순 정렬
    rooms.sort(key=lambda r: r["last_at"], reverse=True)
    return render_template("chat/list.html", rooms=rooms)


@bp.route("/start/<int:product_id>", methods=("POST",))
@login_required
def start(product_id: int):
    """상품 상세에서 '채팅하기' → 판매자와의 방을 만들거나 기존 방으로 이동."""
    db = get_db()
    product = db.execute(
        "SELECT * FROM product WHERE id = ?", (product_id,)
    ).fetchone()
    if product is None or product["status"] == "blocked":
        flash("존재하지 않는 상품입니다.")
        return redirect(url_for("products.index"))

    if product["seller_id"] == g.user["id"]:
        flash("본인 상품에는 채팅할 수 없습니다.")
        return redirect(url_for("products.detail", product_id=product_id))

    conv = db.execute(
        "SELECT * FROM conversation WHERE product_id = ? AND buyer_id = ?",
        (product_id, g.user["id"]),
    ).fetchone()

    if conv is None:
        cur = db.execute(
            "INSERT INTO conversation (product_id, buyer_id, seller_id) VALUES (?, ?, ?)",
            (product_id, g.user["id"], product["seller_id"]),
        )
        db.commit()
        conv_id = cur.lastrowid
    else:
        conv_id = conv["id"]
        # 이전에 나갔더라도 다시 들어오면 목록에 복구
        db.execute("UPDATE conversation SET buyer_hidden = 0 WHERE id = ?", (conv_id,))
        db.commit()

    return redirect(url_for("chat.room", conv_id=conv_id))


@bp.route("/<int:conv_id>", methods=("GET", "POST"))
@login_required
def room(conv_id: int):
    conv = _get_conversation(conv_id)
    db = get_db()
    role, other_id = _other_side(conv)

    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if not body:
            flash("메시지를 입력하세요.")
        elif len(body) > MAX_MESSAGE_LEN:
            flash(f"메시지는 {MAX_MESSAGE_LEN}자 이하여야 합니다.")
        else:
            db.execute(
                "INSERT INTO message (conversation_id, sender_id, body) VALUES (?, ?, ?)",
                (conv_id, g.user["id"], body),
            )
            # 상대가 방을 나갔더라도 새 메시지가 오면 다시 보이게
            other_hidden = "seller_hidden" if role == "buyer" else "buyer_hidden"
            db.execute(f"UPDATE conversation SET {other_hidden} = 0 WHERE id = ?", (conv_id,))
            db.commit()
        return redirect(url_for("chat.room", conv_id=conv_id))

    # 읽음 처리
    read_col = "buyer_read_at" if role == "buyer" else "seller_read_at"
    db.execute(f"UPDATE conversation SET {read_col} = ? WHERE id = ?", (_now(), conv_id))
    db.commit()

    product = db.execute(
        "SELECT * FROM product WHERE id = ?", (conv["product_id"],)
    ).fetchone()
    other = db.execute("SELECT * FROM user WHERE id = ?", (other_id,)).fetchone()

    rows = db.execute(
        "SELECT m.*, "
        "(SELECT COUNT(*) FROM message_reaction r WHERE r.message_id = m.id) AS react_count, "
        "(SELECT COUNT(*) FROM message_reaction r WHERE r.message_id = m.id AND r.user_id = ?) AS reacted "
        "FROM message m WHERE m.conversation_id = ? "
        "ORDER BY m.created_at ASC, m.id ASC",
        (g.user["id"], conv_id),
    ).fetchall()

    return render_template(
        "chat/room.html",
        conv=conv, product=product, other=other, messages=rows,
    )


@bp.route("/<int:conv_id>/leave", methods=("POST",))
@login_required
def leave(conv_id: int):
    conv = _get_conversation(conv_id)
    role, _ = _other_side(conv)
    col = "buyer_hidden" if role == "buyer" else "seller_hidden"
    db = get_db()
    db.execute(f"UPDATE conversation SET {col} = 1 WHERE id = ?", (conv_id,))
    db.commit()
    flash("채팅방을 나갔습니다.")
    return redirect(url_for("chat.index"))


def _load_message_for_owner(message_id: int):
    """메시지를 가져오되 본인이 보낸 것이 아니면 403."""
    db = get_db()
    msg = db.execute("SELECT * FROM message WHERE id = ?", (message_id,)).fetchone()
    if msg is None:
        abort(404)
    if msg["sender_id"] != g.user["id"]:
        abort(403)
    return msg


@bp.route("/message/<int:message_id>/edit", methods=("POST",))
@login_required
def edit_message(message_id: int):
    msg = _load_message_for_owner(message_id)
    if msg["is_deleted"]:
        return jsonify({"error": "deleted"}), 400
    body = (request.form.get("body") or "").strip()
    if not body or len(body) > MAX_MESSAGE_LEN:
        return jsonify({"error": "invalid"}), 400
    db = get_db()
    db.execute(
        "UPDATE message SET body = ?, edited_at = ? WHERE id = ?",
        (body, _now(), message_id),
    )
    db.commit()
    return jsonify({"ok": True, "body": body, "edited": True})


@bp.route("/message/<int:message_id>/delete", methods=("POST",))
@login_required
def delete_message(message_id: int):
    _load_message_for_owner(message_id)
    db = get_db()
    db.execute("UPDATE message SET is_deleted = 1 WHERE id = ?", (message_id,))
    db.commit()
    return jsonify({"ok": True})


@bp.route("/message/<int:message_id>/react", methods=("POST",))
@login_required
def react_message(message_id: int):
    """공감 토글. 방 참여자만 가능."""
    db = get_db()
    msg = db.execute("SELECT * FROM message WHERE id = ?", (message_id,)).fetchone()
    if msg is None:
        abort(404)
    # 참여자 검증
    _get_conversation(msg["conversation_id"])

    existing = db.execute(
        "SELECT id FROM message_reaction WHERE message_id = ? AND user_id = ?",
        (message_id, g.user["id"]),
    ).fetchone()
    if existing:
        db.execute("DELETE FROM message_reaction WHERE id = ?", (existing["id"],))
        reacted = False
    else:
        db.execute(
            "INSERT INTO message_reaction (message_id, user_id) VALUES (?, ?)",
            (message_id, g.user["id"]),
        )
        reacted = True
    db.commit()
    count = db.execute(
        "SELECT COUNT(*) AS n FROM message_reaction WHERE message_id = ?", (message_id,)
    ).fetchone()["n"]
    return jsonify({"ok": True, "reacted": reacted, "count": count})
