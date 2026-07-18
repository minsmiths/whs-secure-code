"""회원가입 / 로그인 / 로그아웃 / 마이페이지."""
import re

from flask import (
    Blueprint, current_app, flash, g, redirect, render_template, request,
    session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db
from .security import login_required

bp = Blueprint("auth", __name__, url_prefix="/auth")

# 아이디: 영문/숫자/밑줄 4~20자
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,20}$")
PASSWORD_MIN_LEN = 8


def _validate_credentials(username: str, password: str) -> str | None:
    """자격 증명 형식을 검증한다. 문제가 있으면 에러 메시지, 없으면 None."""
    if not username or not password:
        return "아이디와 비밀번호를 모두 입력하세요."
    if not USERNAME_RE.match(username):
        return "아이디는 영문/숫자/밑줄 4~20자여야 합니다."
    if len(password) < PASSWORD_MIN_LEN:
        return f"비밀번호는 최소 {PASSWORD_MIN_LEN}자 이상이어야 합니다."
    return None


@bp.route("/register", methods=("GET", "POST"))
def register():
    if g.user:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        error = _validate_credentials(username, password)
        db = get_db()

        if error is None:
            # 아이디 중복 검사 (파라미터 바인딩)
            existing = db.execute(
                "SELECT id FROM user WHERE username = ?", (username,)
            ).fetchone()
            if existing is not None:
                error = "이미 사용 중인 아이디입니다."

        if error is None:
            db.execute(
                "INSERT INTO user (username, password_hash, balance) VALUES (?, ?, ?)",
                (username, generate_password_hash(password),
                 current_app.config["DEFAULT_BALANCE"]),
            )
            db.commit()
            flash("회원가입이 완료되었습니다. 로그인해 주세요.")
            return redirect(url_for("auth.login"))

        flash(error)

    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if g.user:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT * FROM user WHERE username = ?", (username,)
        ).fetchone()

        # 아이디 존재 여부와 무관하게 동일한 에러 메시지를 준다
        # (사용자 존재 여부 노출/열거 공격 방지)
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("아이디 또는 비밀번호가 올바르지 않습니다.")
            return render_template("auth/login.html")

        if user["is_active"] == 0:
            flash("휴면 처리된 계정입니다. 관리자에게 문의하세요.")
            return render_template("auth/login.html")

        # 세션 고정 공격 방지: 로그인 시 세션을 새로 만든다
        session.clear()
        session["user_id"] = user["id"]
        flash(f"{user['username']}님, 환영합니다!")
        return redirect(url_for("main.index"))

    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.")
    return redirect(url_for("main.index"))


@bp.route("/profile", methods=("GET", "POST"))
@login_required
def profile():
    """마이페이지: 소개글 및 비밀번호 변경."""
    db = get_db()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_bio":
            bio = request.form.get("bio", "").strip()
            if len(bio) > 500:
                flash("소개글은 500자 이하여야 합니다.")
            else:
                db.execute(
                    "UPDATE user SET bio = ? WHERE id = ?", (bio, g.user["id"])
                )
                db.commit()
                flash("소개글을 업데이트했습니다.")

        elif action == "change_password":
            current_pw = request.form.get("current_password", "")
            new_pw = request.form.get("new_password", "")

            if not check_password_hash(g.user["password_hash"], current_pw):
                flash("현재 비밀번호가 올바르지 않습니다.")
            elif len(new_pw) < PASSWORD_MIN_LEN:
                flash(f"새 비밀번호는 최소 {PASSWORD_MIN_LEN}자 이상이어야 합니다.")
            else:
                db.execute(
                    "UPDATE user SET password_hash = ? WHERE id = ?",
                    (generate_password_hash(new_pw), g.user["id"]),
                )
                db.commit()
                flash("비밀번호를 변경했습니다.")

        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html", user=g.user)


@bp.route("/user/<int:user_id>")
def user_detail(user_id: int):
    """다른 사용자 프로필 조회."""
    db = get_db()
    user = db.execute(
        "SELECT id, username, bio, created_at FROM user WHERE id = ?", (user_id,)
    ).fetchone()
    if user is None:
        flash("존재하지 않는 사용자입니다.")
        return redirect(url_for("main.index"))

    products = db.execute(
        "SELECT * FROM product WHERE seller_id = ? AND status = 'active' "
        "ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return render_template("auth/user_detail.html", user=user, products=products)
