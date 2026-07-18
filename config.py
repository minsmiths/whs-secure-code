"""애플리케이션 설정.

보안 관련 기본값은 안전한 쪽(secure-by-default)으로 잡는다.
민감한 값(SECRET_KEY 등)은 코드에 하드코딩하지 않고 환경 변수에서 읽는다.
"""
import os
import secrets
from datetime import timedelta


def _get_secret_key() -> str:
    """SECRET_KEY를 환경 변수에서 읽는다.

    운영 환경에서 값이 없으면 즉시 에러를 내서, 예측 가능한 키로
    서비스가 뜨는 사고를 방지한다. 개발 환경에서만 임시 키를 생성한다.
    """
    key = os.environ.get("SECRET_KEY")
    if key:
        return key
    if os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError(
            "SECRET_KEY 환경 변수가 설정되지 않았습니다. "
            "운영 환경에서는 반드시 설정해야 합니다."
        )
    # 개발 환경 전용 임시 키 (프로세스마다 달라짐 → 재시작 시 세션 초기화)
    return secrets.token_hex(32)


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = _get_secret_key()

    # DB 경로 (instance 폴더 안 — git에 커밋되지 않음)
    DB_NAME = "deuce_market.sqlite"

    # 업로드 설정
    UPLOAD_FOLDER = os.path.join("app", "static", "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB 업로드 제한
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    IS_PRODUCTION = os.environ.get("FLASK_ENV") == "production"

    # === 세션 쿠키 보안 ===
    SESSION_COOKIE_HTTPONLY = True   # JS에서 쿠키 접근 차단 (XSS 완화)
    SESSION_COOKIE_SAMESITE = "Lax"  # CSRF 완화
    # 운영 환경에서는 HTTPS 전용 쿠키를 기본 강제(명시적 override 가능)
    SESSION_COOKIE_SECURE = _as_bool(
        os.environ.get("SESSION_COOKIE_SECURE"), default=IS_PRODUCTION
    )

    # === 세션 만료(timeout) ===
    # 마지막 활동 이후 이 시간이 지나면 세션 만료(재로그인 필요)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # === 로그인 실패 방어(무차별 대입 방지) ===
    LOGIN_MAX_ATTEMPTS = 5       # 연속 실패 허용 횟수
    LOGIN_LOCKOUT_MINUTES = 10   # 초과 시 잠금 시간(분)

    # === 채팅 메시지 Rate Limiting(도배/스팸 방지) ===
    CHAT_RATE_MAX = 8            # 윈도우 내 최대 전송 횟수
    CHAT_RATE_WINDOW_SEC = 5     # 윈도우 크기(초)

    # 신고 임계값 (이 이상 신고되면 상품 차단 / 유저 휴면)
    REPORT_BLOCK_THRESHOLD = 3

    # 회원 가입 시 지급되는 기본 잔액 (송금 기능 데모용)
    DEFAULT_BALANCE = 100000
