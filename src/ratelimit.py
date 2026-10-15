"""Tiny in-memory sliding-window rate limiter (no new dependencies).

Per (client IP, endpoint): allow BURST requests, then refill at SUSTAINED
requests/second. Over-limit -> 429 with Retry-After. State lives in the
process (fine for 1-2 workers; use Redis if that ever changes).
"""
from __future__ import annotations

import time
from collections import deque
from threading import Lock

from fastapi import HTTPException, Request

BURST = 30
SUSTAINED_PER_SEC = 2.0

_windows: dict[tuple[str, str], deque] = {}
_lock = Lock()
_last_sweep = 0.0
MAX_CLIENTS = 10000


def client_ip(request: Request) -> str:
    # Uvicorn resolves forwarding only from configured trusted proxies.
    # Never interpret raw client-supplied forwarding headers here.
    return request.client.host if request.client else "unknown"


def check(request: Request, route: str) -> None:
    with _lock:
        _check(request, route)


def _check(request: Request, route: str) -> None:
    global _last_sweep
    now = time.monotonic()
    key = (client_ip(request), route)
    horizon = now - BURST / SUSTAINED_PER_SEC
    if now - _last_sweep >= BURST / SUSTAINED_PER_SEC or len(_windows) >= MAX_CLIENTS:
        expired = [k for k, w in _windows.items() if not w or w[-1] < horizon]
        for k in expired:
            del _windows[k]
        _last_sweep = now
    if key not in _windows and len(_windows) >= MAX_CLIENTS:
        raise HTTPException(status_code=429, detail="rate limiter at capacity",
                            headers={"Retry-After": str(int(BURST / SUSTAINED_PER_SEC) + 1)})
    window = _windows.setdefault(key, deque())
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
