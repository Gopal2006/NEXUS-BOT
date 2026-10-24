"""
Guild Management and Introspection API Routes.
Provides server picker lists, channels, roles, and guild metadata.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
import discord

from core.bot import bot
from core.config import is_bot_owner
from api.auth import get_current_user_id, verify_api_key, verify_guild_access, user_can_manage_guild

router = APIRouter(prefix="/api/v1", tags=["Guilds"])


@router.get("/me/guilds")
async def get_my_guilds(
    _: str = Depends(verify_api_key),
    user_id: int = Depends(get_current_user_id),
) -> list[dict[str, Any]]:
    """
    Returns all Discord servers where the authenticated user has management access:
      - Global bot owners (OWNER_IDS) see ALL bot guilds.
      - Regular users see guilds where they are Guild Owner or hold the configured Bot-Role.
    """
    results = []
    for g in bot.guilds:
        can_manage = await user_can_manage_guild(user_id, g.id)
        if can_manage:
            icon_url = g.icon.url if g.icon else None
            results.append({
                "id": str(g.id),
                "name": g.name,
                "icon": icon_url,
                "member_count": g.member_count,
                "owner_id": str(g.owner_id),
                "is_owner": g.owner_id == user_id,
            })
    return results


@router.get("/guilds/{guild_id}")
async def get_guild_details(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
) -> dict[str, Any]:
    """Returns basic guild info and verification status."""
    return {
        "id": str(guild.id),
        "name": guild.name,
        "icon": guild.icon.url if guild.icon else None,
        "member_count": guild.member_count,
        "owner_id": str(guild.owner_id),
        "roles_count": len(guild.roles),
        "channels_count": len(guild.channels),
    }


@router.get("/guilds/{guild_id}/channels")
async def get_guild_channels(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
) -> list[dict[str, Any]]:
    """Returns all channels in the guild organized by type."""
    channels = []
    for ch in sorted(guild.channels, key=lambda c: c.position):
        ch_type = "text"
        if isinstance(ch, discord.VoiceChannel):
            ch_type = "voice"
        elif isinstance(ch, discord.CategoryChannel):
            ch_type = "category"
        elif isinstance(ch, discord.StageChannel):
            ch_type = "stage"

        channels.append({
            "id": str(ch.id),
            "name": ch.name,
            "type": ch_type,
            "category_id": str(ch.category_id) if getattr(ch, "category_id", None) else None,
            "position": ch.position,
        })
    return channels


@router.get("/guilds/{guild_id}/roles")
async def get_guild_roles(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
) -> list[dict[str, Any]]:
    """Returns all roles in the guild with hierarchy and assignability metadata."""
    roles = []
    bot_top = guild.me.top_role if guild.me else None

    for r in sorted(guild.roles, key=lambda x: x.position, reverse=True):
        if r.is_default():
            continue  # Exclude @everyone from role assignment selectors

        hex_color = f"#{r.color.value:06x}" if r.color.value != 0 else "#99AAB5"
        roles.append({
            "id": str(r.id),
            "name": r.name,
            "color": hex_color,
            "position": r.position,
            "manageable": (bot_top is not None and r < bot_top) and not r.managed,
        })
    return roles


@router.get("/guilds/{guild_id}/members")
async def get_guild_members(
    guild_id: int,
    query: str | None = None,
    limit: int = 100,
    guild: discord.Guild = Depends(verify_guild_access),
) -> list[dict[str, Any]]:
    if not guild.chunked:
        try:
            await guild.chunk()
        except Exception:
            pass
    members = list(guild.members)
    if query:
        q = query.strip().lower()
        members = [
            m for m in members
            if q in m.name.lower() or (m.nick and q in m.nick.lower()) or q in str(m.id)
        ]

    # Non-bots first, then alphabetical by display name
    members = sorted(members, key=lambda m: (m.bot, m.display_name.lower()))[:limit]

    results = []
    for m in members:
        results.append({
            "id": str(m.id),
            "name": m.name,
            "displayName": m.display_name,
            "bot": m.bot,
            "avatar": m.display_avatar.url if m.display_avatar else None,
            "roles": [str(r.id) for r in m.roles if not r.is_default()],
        })
    return results
