import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


class RateLimiter:
    """Simple in-memory sliding-window rate limiter.

    This is sufficient for a demo/technical assessment. A production deployment
    would use a distributed store such as Redis.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = 0.0

    def _cleanup_stale_keys(self, now: float) -> None:
        """Drop keys whose newest timestamp fell out of the window.

        Without this, every client IP ever seen would stay in memory forever.
        Runs at most once per window to keep the hot path cheap.
        """
        if now - self._last_cleanup < self.window_seconds:
            return
        self._last_cleanup = now
        window_start = now - self.window_seconds
        stale = [
            k for k, ts_list in self._requests.items() if not ts_list or ts_list[-1] <= window_start
        ]
        for k in stale:
            del self._requests[k]

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds
        self._cleanup_stale_keys(now)
        self._requests[key] = [ts for ts in self._requests[key] if ts > window_start]

        if len(self._requests[key]) >= self.max_requests:
            return False

        self._requests[key].append(now)
        return True


# Shared limiter instances.
CHAT_RATE_LIMITER = RateLimiter(max_requests=30, window_seconds=60)
UPLOAD_RATE_LIMITER = RateLimiter(max_requests=10, window_seconds=60)


def check_chat_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    if not CHAT_RATE_LIMITER.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Chat rate limit exceeded. Please slow down.",
        )


def check_upload_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    if not UPLOAD_RATE_LIMITER.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Upload rate limit exceeded. Please slow down.",
        )
