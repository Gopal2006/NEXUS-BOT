"""
Sliding window counter for rate tracking, antinuke detection, and automod spam prevention.
"""

import time
from collections import defaultdict, deque
from typing import Any, Optional


class SlidingWindowCounter:
    """
    In-memory sliding window event counter.
    Efficiently records event timestamps in a deque and prunes timestamps
    older than the specified window.
    """

    def __init__(self):
        self._buckets: dict[Any, deque[float]] = defaultdict(deque)

    def _prune(self, key: Any, window_seconds: float, now: float) -> deque[float]:
        bucket = self._buckets[key]
        cutoff = now - window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if not bucket and key in self._buckets:
            del self._buckets[key]
            return deque()
        return bucket

    def record_event(self, key: Any, now: Optional[float] = None) -> int:
        """
        Records an event at timestamp `now` (default: current time)
        and returns the total count stored for this key.
        """
        t = now if now is not None else time.time()
        self._buckets[key].append(t)
        return len(self._buckets[key])

    def get_count(self, key: Any, window_seconds: float, now: Optional[float] = None) -> int:
        """
        Returns the number of events that occurred within the trailing `window_seconds`.
        """
        t = now if now is not None else time.time()
        if key not in self._buckets:
            return 0
        bucket = self._prune(key, window_seconds, t)
        return len(bucket)

    def hit_and_check(
        self,
        key: Any,
        limit: int,
        window_seconds: float,
        now: Optional[float] = None,
    ) -> tuple[bool, int]:
        """
        Convenience method: records an event, prunes expired timestamps,
        and returns (is_limit_exceeded, current_count).
        Limit is exceeded if current_count >= limit (or > limit depending on inclusive semantics).
        Here: returns True if current_count > limit.
        """
        t = now if now is not None else time.time()
        self._buckets[key].append(t)
        bucket = self._prune(key, window_seconds, t)
        count = len(bucket)
        return count > limit, count

    def reset(self, key: Any) -> None:
        """Clears recorded events for the given key."""
        self._buckets.pop(key, None)

    def clear(self) -> None:
        """Clears all keys and buckets."""
        self._buckets.clear()
