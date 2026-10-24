"""
Unit tests for security components: SlidingWindowCounter and Whitelist logic.
"""

import time
import pytest
from utils.window import SlidingWindowCounter


def test_sliding_window_counter_basic():
    counter = SlidingWindowCounter()
    key = ("guild1", "user1", "ban")

    now = 1000.0
    # First 3 hits
    for i in range(3):
        exceeded, count = counter.hit_and_check(key, limit=3, window_seconds=60, now=now + i)
        assert exceeded is False
        assert count == i + 1

    # 4th hit: exceeds limit 3
    exceeded, count = counter.hit_and_check(key, limit=3, window_seconds=60, now=now + 3)
    assert exceeded is True
    assert count == 4


def test_sliding_window_counter_expiration():
    counter = SlidingWindowCounter()
    key = ("guild1", "user2", "kick")

    now = 1000.0
    # 3 hits at t=1000, 1001, 1002
    counter.hit_and_check(key, limit=3, window_seconds=10, now=now)
    counter.hit_and_check(key, limit=3, window_seconds=10, now=now + 1)
    counter.hit_and_check(key, limit=3, window_seconds=10, now=now + 2)

    # Check count within 10s
    assert counter.get_count(key, window_seconds=10, now=now + 5) == 3

    # Check count after 15s (previous events expired)
    assert counter.get_count(key, window_seconds=10, now=now + 15) == 0

    # New hit at t=1015 should have count 1
    exceeded, count = counter.hit_and_check(key, limit=3, window_seconds=10, now=now + 15)
    assert exceeded is False
    assert count == 1


def test_sliding_window_counter_reset():
    counter = SlidingWindowCounter()
    key = ("guild1", "user3", "channel")

    counter.hit_and_check(key, limit=2, window_seconds=60)
    counter.hit_and_check(key, limit=2, window_seconds=60)
    assert counter.get_count(key, window_seconds=60) == 2

    counter.reset(key)
    assert counter.get_count(key, window_seconds=60) == 0
