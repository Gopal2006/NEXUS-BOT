"""
Two-layer authentication and authorization for the Nexus Dashboard API.
1. X-API-Key header validated with constant-time HMAC comparison against DASHBOARD_API_KEY.
2. X-User-Id validated server-side against the live bot state and guild bot-role permissions.
"""

import hmac
import logging
from typing import Optional
from fastapi import Header, HTTPException, status, Depends
import discord

from core.config import DASHBOARD_API_KEY, is_bot_owner
from core.bot import bot
from db.database import get_config

log = logging.getLogger("Nexus.API.Auth")


def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
    """Validates the shared secret API key between the Next.js server-side proxy and FastAPI."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    if not DASHBOARD_API_KEY:
        log.error("DASHBOARD_API_KEY is not configured on the bot server!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dashboard API key is not configured",
        )

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(x_api_key.strip(), DASHBOARD_API_KEY.strip()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-API-Key",
        )
    return x_api_key


def get_current_user_id(x_user_id: Optional[str] = Header(None, alias="X-User-Id")) -> int:
    """Extracts and validates the authenticated Discord user ID."""
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header",
        )
    try:
        user_id = int(x_user_id.strip())
        return user_id
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-User-Id format (must be integer)",
        )


async def user_can_manage_guild(user_id: int, guild_id: int) -> bool:
    """
    Checks if a user is authorized to manage a specific guild in the dashboard:
      1. Global bot owners (OWNER_IDS)
      2. Server Owner
      3. Members possessing the configured bot_role_id
    *Note: Server Administrators WITHOUT the bot-role are intentionally BLOCKED.*
    """
    if is_bot_owner(user_id):
        return True

    guild = bot.get_guild(guild_id)
    if not guild:
        return False

    if user_id == guild.owner_id:
        return True

    cfg = await get_config(guild_id)
    bot_role_id = cfg.get("bot_role_id")
    if not bot_role_id:
        return False

    member = guild.get_member(user_id)
    if not member:
        try:
            member = await guild.fetch_member(user_id)
        except Exception:
            member = None

    if member and any(r.id == bot_role_id for r in member.roles):
        return True

    return False


async def verify_guild_access(
    guild_id: int,
    user_id: int = Depends(get_current_user_id),
    _: str = Depends(verify_api_key),
) -> discord.Guild:
    """FastAPI dependency: verifies user has management access to the given guild."""
    guild = bot.get_guild(guild_id)
    if not guild:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guild not found or bot is not in guild",
        )

    allowed = await user_can_manage_guild(user_id, guild_id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You must be the Server Owner or hold the configured Bot-Role",
        )

    return guild


def verify_bot_owner(
    user_id: int = Depends(get_current_user_id),
    _: str = Depends(verify_api_key),
) -> int:
    """FastAPI dependency: verifies user is in OWNER_IDS."""
    if not is_bot_owner(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Global Bot Owners only",
        )
    return user_id

