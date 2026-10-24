"""
In-memory token bucket rate limiter for API requests.
Returns HTTP 429 Too Many Requests with Retry-After header when rate is exceeded.
"""

import time
from fastapi import Request, HTTPException, status
from utils.window import SlidingWindowCounter

# Window counter: (client_ip_or_user, endpoint) -> timestamps
api_limiter = SlidingWindowCounter()

DEFAULT_RATE_LIMIT = 60  # 60 requests
DEFAULT_WINDOW = 60       # per 60 seconds


async def rate_limit_dependency(request: Request):
    """Dependency that rate-limits incoming API requests per user or IP address."""
    # Key by user_id if present, otherwise client IP
    user_id = request.headers.get("X-User-Id")
    client_ip = request.client.host if request.client else "unknown"
    client_key = f"user:{user_id}" if user_id else f"ip:{client_ip}"

    path = request.url.path
    key = (client_key, path)

    now = time.time()
    exceeded, count = api_limiter.hit_and_check(
        key,
        limit=DEFAULT_RATE_LIMIT,
        window_seconds=DEFAULT_WINDOW,
        now=now,
    )

    if exceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too Many Requests. Please slow down.",
            headers={"Retry-After": "10"},
        )
