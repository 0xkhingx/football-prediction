"""Tiny in-memory sliding-window rate limiter (no new dependencies).

Per (client IP, endpoint): allow BURST requests, then refill at SUSTAINED
requests/second. Over-limit -> 429 with Retry-After. State lives in the
process (fine for 1-2 workers; use Redis if that ever changes).
"""
from __future__ import annotations

import time
from collections import deque

from fastapi import HTTPException, Request

BURST = 30
SUSTAINED_PER_SEC = 2.0

_windows: dict[tuple[str, str], deque] = {}


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check(request: Request, route: str) -> None:
    now = time.monotonic()
    key = (client_ip(request), route)
    window = _windows.setdefault(key, deque())
    horizon = now - BURST / SUSTAINED_PER_SEC
    while window and window[0] < horizon:
        window.popleft()
    if len(window) >= BURST:
        oldest = window[0]
        retry_after = max(1, int((oldest + BURST / SUSTAINED_PER_SEC) - now) + 1)
        raise HTTPException(
            status_code=429,
            detail="rate limit exceeded — slow down",
            headers={"Retry-After": str(retry_after)},
        )
    window.append(now)
