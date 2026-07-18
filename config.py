"""애플리케이션 설정.

보안 관련 기본값은 안전한 쪽(secure-by-default)으로 잡는다.
민감한 값(SECRET_KEY 등)은 코드에 하드코딩하지 않고 환경 변수에서 읽는다.
"""
import os
import secrets


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

    # === 세션 쿠키 보안 ===
    SESSION_COOKIE_HTTPONLY = True   # JS에서 쿠키 접근 차단 (XSS 완화)
    SESSION_COOKIE_SAMESITE = "Lax"  # CSRF 완화
    SESSION_COOKIE_SECURE = _as_bool(os.environ.get("SESSION_COOKIE_SECURE"), False)

    # 신고 임계값 (이 이상 신고되면 상품 차단 / 유저 휴면)
    REPORT_BLOCK_THRESHOLD = 3

    # 회원 가입 시 지급되는 기본 잔액 (송금 기능 데모용)
    DEFAULT_BALANCE = 100000
