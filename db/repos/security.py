"""
Repository for Antinuke, Whitelist, and Automod settings with in-memory caching.
"""

import time
import logging
from typing import Any, Optional
import discord

from db.database import get_db

log = logging.getLogger("Nexus.SecurityRepo")

# In-memory caches: guild_id -> settings dict
_ANTINUKE_CACHE: dict[int, dict[str, Any]] = {}
_AUTOMOD_CACHE: dict[int, dict[str, Any]] = {}
# Whitelist cache: guild_id -> list of whitelist row dicts
_WHITELIST_CACHE: dict[int, list[dict[str, Any]]] = {}

DEFAULT_ANTINUKE = {
    "enabled": 0,
    "punishment": "ban",
    "ban_limit": 3,
    "kick_limit": 3,
    "channel_limit": 3,
    "role_limit": 3,
    "webhook_limit": 3,
    "bot_add_limit": 1,
    "prune_limit": 1,
    "window_seconds": 60,
    "anti_dangerous_roles": 1,
}

DEFAULT_AUTOMOD = {
    "enabled": 0,
    "anti_spam": 1,
    "spam_threshold": 5,
    "spam_window": 5,
    "anti_caps": 0,
    "caps_percentage": 70,
    "caps_min_length": 10,
    "anti_links": 0,
    "anti_invites": 1,
    "anti_mass_mentions": 1,
    "mention_limit": 5,
    "anti_emoji_spam": 0,
    "emoji_limit": 6,
    "banned_words": "",
    "action": "delete",
    "timeout_duration": 300,
    "ignored_channels": "",
    "ignored_roles": "",
}


# ── Antinuke ──────────────────────────────────────────────────────────────────

async def get_antinuke_settings(guild_id: int) -> dict[str, Any]:
    if guild_id in _ANTINUKE_CACHE:
        return dict(_ANTINUKE_CACHE[guild_id])

    db = await get_db()
    async with db.execute(
        "SELECT * FROM antinuke_settings WHERE guild_id = ?",
        (guild_id,),
    ) as cursor:
        row = await cursor.fetchone()
        if row:
            data = dict(row)
        else:
            data = {"guild_id": guild_id, **DEFAULT_ANTINUKE}
            await db.execute(
                """
                INSERT OR IGNORE INTO antinuke_settings (guild_id) VALUES (?)
                """,
                (guild_id,),
            )
            await db.commit()

    _ANTINUKE_CACHE[guild_id] = data
    return dict(data)


async def update_antinuke_settings(guild_id: int, **kwargs) -> dict[str, Any]:
    current = await get_antinuke_settings(guild_id)
    allowed = set(DEFAULT_ANTINUKE.keys())
    valid_updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not valid_updates:
        return current

    fields = ", ".join(f"{k} = ?" for k in valid_updates.keys())
    values = list(valid_updates.values()) + [guild_id]

    db = await get_db()
    await db.execute(
        f"UPDATE antinuke_settings SET {fields} WHERE guild_id = ?",
        values,
    )
    await db.commit()

    current.update(valid_updates)
    _ANTINUKE_CACHE[guild_id] = current
    return dict(current)


# ── Whitelist ─────────────────────────────────────────────────────────────────

async def get_guild_whitelist(guild_id: int) -> list[dict[str, Any]]:
    if guild_id in _WHITELIST_CACHE:
        return [dict(x) for x in _WHITELIST_CACHE[guild_id]]

    db = await get_db()
    async with db.execute(
        "SELECT * FROM whitelist WHERE guild_id = ? ORDER BY added_at ASC",
        (guild_id,),
    ) as cursor:
        rows = await cursor.fetchall()
        entries = [dict(r) for r in rows]

    _WHITELIST_CACHE[guild_id] = entries
    return [dict(x) for x in entries]


async def add_whitelist_entry(
    guild_id: int,
    target_id: int,
    target_type: str,
    module: str = "all",
    added_by: Optional[int] = None,
) -> bool:
    db = await get_db()
    now = time.time()
    try:
        await db.execute(
            """
            INSERT OR REPLACE INTO whitelist (guild_id, target_id, target_type, module, added_by, added_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (guild_id, target_id, target_type, module, added_by, now),
        )
        await db.commit()
        _WHITELIST_CACHE.pop(guild_id, None)
        return True
    except Exception as e:
        log.error(f"Failed to add whitelist entry for guild {guild_id}: {e}")
        return False


async def remove_whitelist_entry(
    guild_id: int,
    target_id: int,
    module: Optional[str] = None,
) -> bool:
    db = await get_db()
    try:
        if module:
            await db.execute(
                "DELETE FROM whitelist WHERE guild_id = ? AND target_id = ? AND module = ?",
                (guild_id, target_id, module),
            )
        else:
            await db.execute(
                "DELETE FROM whitelist WHERE guild_id = ? AND target_id = ?",
                (guild_id, target_id),
            )
        await db.commit()
        _WHITELIST_CACHE.pop(guild_id, None)
        return True
    except Exception as e:
        log.error(f"Failed to remove whitelist entry for guild {guild_id}: {e}")
        return False


async def is_whitelisted(
    guild_id: int,
    member_or_user: discord.Member | discord.User,
    module: str = "all",
) -> bool:
    """
    Checks if a user or any of their roles is whitelisted for the given module
    ('antinuke', 'automod', or 'all').
    """
    entries = await get_guild_whitelist(guild_id)
    if not entries:
        return False

    user_id = member_or_user.id
    user_roles = set()
    if isinstance(member_or_user, discord.Member):
        user_roles = {r.id for r in member_or_user.roles}

    for item in entries:
        item_mod = item.get("module", "all")
        if item_mod not in ("all", module):
            continue

        target_id = item["target_id"]
        target_type = item["target_type"]

        if target_type == "user" and target_id == user_id:
            return True
        elif target_type == "role" and target_id in user_roles:
            return True

    return False


# ── Automod ───────────────────────────────────────────────────────────────────

async def get_automod_settings(guild_id: int) -> dict[str, Any]:
    if guild_id in _AUTOMOD_CACHE:
        return dict(_AUTOMOD_CACHE[guild_id])

    db = await get_db()
    async with db.execute(
        "SELECT * FROM automod_settings WHERE guild_id = ?",
        (guild_id,),
    ) as cursor:
        row = await cursor.fetchone()
        if row:
            data = dict(row)
        else:
            data = {"guild_id": guild_id, **DEFAULT_AUTOMOD}
            await db.execute(
                """
                INSERT OR IGNORE INTO automod_settings (guild_id) VALUES (?)
                """,
                (guild_id,),
            )
            await db.commit()

    _AUTOMOD_CACHE[guild_id] = data
    return dict(data)


async def update_automod_settings(guild_id: int, **kwargs) -> dict[str, Any]:
    current = await get_automod_settings(guild_id)
    allowed = set(DEFAULT_AUTOMOD.keys())
    valid_updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not valid_updates:
        return current

    fields = ", ".join(f"{k} = ?" for k in valid_updates.keys())
    values = list(valid_updates.values()) + [guild_id]

    db = await get_db()
    await db.execute(
        f"UPDATE automod_settings SET {fields} WHERE guild_id = ?",
        values,
    )
    await db.commit()

    current.update(valid_updates)
    _AUTOMOD_CACHE[guild_id] = current
    return dict(current)
