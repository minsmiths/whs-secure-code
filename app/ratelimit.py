"""간단한 인메모리 Rate Limiter (슬라이딩 윈도우).

채팅 메시지 도배/스팸을 막기 위해 '키(예: 사용자 id)별로 최근 N초 동안
최대 M회'만 허용한다. 단일 프로세스 개발/데모 환경 기준이며, 다중 프로세스
운영에서는 Redis 등 공유 저장소 기반으로 교체하는 것을 권장한다.
"""
import time
from collections import defaultdict, deque

_buckets: dict = defaultdict(deque)


def allow(key, max_count: int, window_sec: float) -> bool:
    """key 에 대해 window_sec 초 안에 max_count 회까지 허용. 초과하면 False."""
    now = time.monotonic()
    dq = _buckets[key]
    # 윈도우를 벗어난 오래된 타임스탬프 제거
    while dq and now - dq[0] > window_sec:
        dq.popleft()
    if len(dq) >= max_count:
        return False
    dq.append(now)
    return True
