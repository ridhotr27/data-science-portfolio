from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque

from dotenv import load_dotenv
from fastapi import HTTPException, Request


class UploadRateLimiter:
    def __init__(self, maximum: int = 20, window_seconds: int = 60):
        self.maximum = maximum
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> None:
        current = time.monotonic() if now is None else now
        cutoff = current - self.window_seconds
        with self._lock:
            attempts = self._attempts[key]
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            if len(attempts) >= self.maximum:
                raise HTTPException(
                    429,
                    f"Too many uploads. Please wait {self.window_seconds} seconds and try again.",
                )
            attempts.append(current)

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()


load_dotenv()
upload_limiter = UploadRateLimiter(
    maximum=int(os.getenv("UPLOAD_RATE_LIMIT", "20")),
    window_seconds=int(os.getenv("UPLOAD_RATE_WINDOW_SECONDS", "60")),
)


def check_upload_rate(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    upload_limiter.check(client)
