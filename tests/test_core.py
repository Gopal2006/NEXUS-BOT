"""
Tests for core permissions, durations, and safe string placeholders.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from utils.durations import parse_duration, format_duration
from utils.placeholders import safe_format
from core.permissions import has_tier_permission
from core.config import OWNER_IDS, PRIMARY_OWNER_ID


def test_duration_parser():
    assert parse_duration("30s") == 30
    assert parse_duration("10m") == 600
    assert parse_duration("2h") == 7200
    assert parse_duration("1d") == 86400
    assert parse_duration("1d12h") == 129600
    assert parse_duration("2h30m") == 9000
    assert parse_duration("invalid") == 0


def test_duration_formatter():
    assert format_duration(30) == "30s"
    assert format_duration(600) == "10m"
    assert format_duration(7200) == "2h"
    assert format_duration(86400) == "1d"
    assert format_duration(129600) == "1d 12h"


def test_safe_placeholder_formatting():
    template = "Welcome {mention} to **{guild}**! User: {name} (Total: {member_count})"
    result = safe_format(
        template,
        mention="<@123>",
        guild="Nexus HQ",
        name="JohnDoe",
        member_count=42,
    )
    assert result == "Welcome <@123> to **Nexus HQ**! User: JohnDoe (Total: 42)"

    # Malicious or unknown keys must not raise exception
    malicious = "{__class__.__init__} and {unknown_key}"
    safe_result = safe_format(malicious, normal="fine")
    assert safe_result == "{__class__.__init__} and {unknown_key}"


@pytest.mark.asyncio
async def test_permission_tiers():
    # Regular member context
    mock_guild = MagicMock()
    mock_guild.id = 999999
    mock_guild.owner_id = 888888
    mock_guild.get_role.return_value = None

    normal_author = MagicMock()
    normal_author.id = 111111  # Not owner
    normal_author.roles = []

    mock_ctx = MagicMock()
    mock_ctx.guild = mock_guild
    mock_ctx.author = normal_author
    mock_ctx.bot = MagicMock()
    mock_ctx.bot.non_prefix_users = set()

    # Public tier must be allowed for regular member
    assert await has_tier_permission(mock_ctx, tier="public") is True

    # Staff tier must be DENIED for regular member without bot role
    assert await has_tier_permission(mock_ctx, tier="staff") is False

    # Owner tier must be DENIED for regular member
    assert await has_tier_permission(mock_ctx, tier="owner") is False

    # Bot owner tier must be DENIED for regular member
    assert await has_tier_permission(mock_ctx, tier="bot_owner") is False

    # Guild owner context
    guild_owner = MagicMock()
    guild_owner.id = 888888  # Matches mock_guild.owner_id
    guild_owner.roles = []
    mock_ctx.author = guild_owner

    assert await has_tier_permission(mock_ctx, tier="public") is True
    assert await has_tier_permission(mock_ctx, tier="staff") is True
    assert await has_tier_permission(mock_ctx, tier="owner") is True
    assert await has_tier_permission(mock_ctx, tier="bot_owner") is False

    # Global bot owner context
    bot_owner = MagicMock()
    bot_owner.id = PRIMARY_OWNER_ID
    bot_owner.roles = []
    mock_ctx.author = bot_owner

    assert await has_tier_permission(mock_ctx, tier="public") is True
    assert await has_tier_permission(mock_ctx, tier="staff") is True
    assert await has_tier_permission(mock_ctx, tier="owner") is True
    assert await has_tier_permission(mock_ctx, tier="bot_owner") is True
