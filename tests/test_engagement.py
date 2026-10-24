"""
Unit tests for engagement calculations and XP formulas.
"""

import pytest
from db.repos.engagement import xp_required_for_level, calculate_level_from_xp


def test_xp_curve_progression():
    """Verify that required XP increases quadratically and deterministically."""
    assert xp_required_for_level(0) == 0
    assert xp_required_for_level(1) == 155
    assert xp_required_for_level(2) == 220
    assert xp_required_for_level(5) == 475
    assert xp_required_for_level(10) == 1100

    # Ensure strictly increasing requirement
    prev = 0
    for lvl in range(1, 20):
        req = xp_required_for_level(lvl)
        assert req > prev
        prev = req


def test_calculate_level_from_xp():
    """Verify level deduction matches cumulative XP thresholds."""
    assert calculate_level_from_xp(0) == 0
    assert calculate_level_from_xp(100) == 0
    assert calculate_level_from_xp(155) == 1
    assert calculate_level_from_xp(200) == 1
    assert calculate_level_from_xp(220) == 2
    assert calculate_level_from_xp(1500) >= 10
