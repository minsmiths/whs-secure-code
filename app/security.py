"""인증/인가 관련 공통 유틸리티."""
import functools

from flask import g, redirect, session, url_for, flash, abort

from .db import get_db


def load_logged_in_user() -> None:
    """세션의 user_id 로 현재 로그인 사용자를 g.user 에 적재한다.

    각 요청 시작 시 호출되며, 휴면(is_active=0) 계정은 자동 로그아웃한다.
    """
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
        return

    db = get_db()
    user = db.execute(
        "SELECT * FROM user WHERE id = ?", (user_id,)
    ).fetchone()

    if user is None or user["is_active"] == 0:
        # 존재하지 않거나 휴면 처리된 계정 → 세션 파기
        session.clear()
        g.user = None
    else:
        g.user = user


def login_required(view):
    """로그인하지 않은 사용자를 로그인 페이지로 보낸다."""

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("로그인이 필요합니다.")
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view


def admin_required(view):
    """관리자만 접근을 허용한다."""

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        if not g.user["is_admin"]:
            abort(403)
        return view(**kwargs)

    return wrapped_view
