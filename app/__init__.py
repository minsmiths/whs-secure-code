"""Deuce Market 🎾 — 테니스 용품 중고거래 플랫폼.

애플리케이션 팩토리 패턴으로 앱을 구성한다.
"""
import os

from flask import Flask, g
from flask_wtf.csrf import CSRFProtect

from config import Config

csrf = CSRFProtect()


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # instance 폴더(민감 파일·DB 저장 위치) 보장
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "static", "uploads"), exist_ok=True)

    # === 보안 확장 ===
    # 모든 POST 요청에 CSRF 토큰 검증을 강제한다.
    csrf.init_app(app)

    # === DB ===
    from . import db, seed, migrate
    db.init_app(app)
    seed.init_app(app)

    # 기존 DB에 새 컬럼이 없으면 자동으로 추가 (git pull 후 데이터 보존 마이그레이션)
    with app.app_context():
        migrate.run(app)

    # === Jinja 필터 (timeago, krw, placeholder) ===
    from . import filters
    filters.init_app(app)

    # === 요청마다 로그인 사용자 로드 ===
    from .security import load_logged_in_user

    @app.before_request
    def _before_request():
        load_logged_in_user()

    # === 응답 보안 헤더 ===
    @app.after_request
    def _set_security_headers(response):
        # 클릭재킹 방지
        response.headers["X-Frame-Options"] = "DENY"
        # MIME 스니핑 방지
        response.headers["X-Content-Type-Options"] = "nosniff"
        # 레퍼러 최소화
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # 기본 CSP (인라인 스크립트 최소화 정책; 필요 시 조정)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'"
        )
        # 운영(HTTPS) 환경에서는 HSTS 로 전송 구간 암호화를 강제
        if app.config.get("IS_PRODUCTION"):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    # === 블루프린트 등록 ===
    from . import auth, products, main, chat, favorites, transfer, report, admin

    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(products.bp)
    app.register_blueprint(chat.bp)
    app.register_blueprint(favorites.bp)
    app.register_blueprint(transfer.bp)
    app.register_blueprint(report.bp)
    app.register_blueprint(admin.bp)

    return app
