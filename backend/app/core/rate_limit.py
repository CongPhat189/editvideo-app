"""Giới hạn tần suất trong bộ nhớ: API đăng nhập (ai cũng gọi được) và API tốn tiền gọi AI.

Chạy nhiều worker thì mỗi worker đếm riêng; khi đó nên chuyển sang Redis.
Chạy sau proxy phải đặt FORWARDED_ALLOW_IPS=<IP của proxy> (uvicorn đọc biến này), nếu không mọi user
chung một IP và đụng giới hạn của nhau. Đừng đặt *, vì client sẽ giả được IP.
"""

import time
from collections import deque

from fastapi import HTTPException, status

MAX_KEYS = 100_000


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}

    def _recent(self, key: str, window_seconds: int, now: float) -> deque[float]:
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - window_seconds:
            hits.popleft()
        return hits

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        """Vượt giới hạn thì trả 429, nhưng không tính thêm lượt."""
        now = time.monotonic()
        hits = self._recent(key, window_seconds, now)
        if len(hits) >= limit:
            retry_after = int(hits[0] + window_seconds - now) + 1
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Bạn thao tác quá nhanh, vui lòng thử lại sau ít phút",
                {"Retry-After": str(retry_after)},
            )

    def record(self, key: str) -> None:
        now = time.monotonic()
        self._hits.setdefault(key, deque()).append(now)
        if len(self._hits) > MAX_KEYS:
            self._hits = {k: v for k, v in self._hits.items() if v and v[-1] > now - 3600}

    def hit(self, key: str, limit: int, window_seconds: int) -> None:
        """Ghi nhận một lần gọi; vượt giới hạn thì trả 429."""
        self.check(key, limit, window_seconds)
        self.record(key)

    def reset(self) -> None:
        self._hits.clear()


limiter = RateLimiter()
