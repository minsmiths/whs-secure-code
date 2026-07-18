"""Jinja2 커스텀 필터/글로벌.

- timeago: '3분 전' 형태 상대 시간
- krw: 1000 -> '1,000' 통화 포맷
- ph_class: 카테고리를 이미지 플레이스홀더 그라디언트 클래스로 매핑
"""
from datetime import datetime, timezone


_CATEGORY_PH = {
    "라켓": "ph-racket",
    "스트링": "ph-string",
    "테니스화": "ph-shoes",
    "의류": "ph-apparel",
    "가방": "ph-bag",
    "테니스공": "ph-ball",
    "액세서리": "ph-acc",
    "기타": "ph-etc",
}

_CATEGORY_EMOJI = {
    "라켓": "🎾",
    "스트링": "🧵",
    "테니스화": "👟",
    "의류": "👕",
    "가방": "🎒",
    "테니스공": "🟡",
    "액세서리": "🧢",
    "기타": "📦",
}


def timeago(value) -> str:
    """SQLite datetime 문자열('YYYY-MM-DD HH:MM:SS', UTC)을 상대시간으로."""
    if not value:
        return ""
    try:
        dt = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
    except (ValueError, TypeError):
        return str(value)

    now = datetime.now(timezone.utc)
    diff = (now - dt).total_seconds()

    if diff < 60:
        return "방금 전"
    if diff < 3600:
        return f"{int(diff // 60)}분 전"
    if diff < 86400:
        return f"{int(diff // 3600)}시간 전"
    if diff < 86400 * 7:
        return f"{int(diff // 86400)}일 전"
    if diff < 86400 * 30:
        return f"{int(diff // (86400 * 7))}주 전"
    if diff < 86400 * 365:
        return f"{int(diff // (86400 * 30))}개월 전"
    return f"{int(diff // (86400 * 365))}년 전"


def krw(value) -> str:
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return str(value)


def ph_class(category) -> str:
    return _CATEGORY_PH.get(category, "ph-etc")


def ph_emoji(category) -> str:
    return _CATEGORY_EMOJI.get(category, "📦")


def init_app(app) -> None:
    app.jinja_env.filters["timeago"] = timeago
    app.jinja_env.filters["krw"] = krw
    app.jinja_env.filters["ph_class"] = ph_class
    app.jinja_env.filters["ph_emoji"] = ph_emoji
