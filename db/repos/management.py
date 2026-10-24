"""
Repository for Management features: Autorole, Reaction Roles, Verification, Join-To-Create, and Welcome Extras.
"""

import time
import logging
from typing import Any, Optional
from db.database import get_db

log = logging.getLogger("Nexus.ManagementRepo")


# ── Autorole ──────────────────────────────────────────────────────────────────

async def get_autorole_settings(guild_id: int) -> dict[str, Any]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM autorole_settings WHERE guild_id = ?",
        (guild_id,),
    ) as cur:
        row = await cur.fetchone()
        if row:
            return dict(row)
        return {"guild_id": guild_id, "human_role_id": None, "bot_role_id": None}


async def update_autorole_settings(guild_id: int, **kwargs) -> dict[str, Any]:
    allowed = {"human_role_id", "bot_role_id"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return await get_autorole_settings(guild_id)

    db = await get_db()
    current = await get_autorole_settings(guild_id)
    current.update(updates)

    await db.execute(
        """
        INSERT INTO autorole_settings (guild_id, human_role_id, bot_role_id)
        VALUES (?, ?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET
            human_role_id = excluded.human_role_id,
            bot_role_id = excluded.bot_role_id
        """,
        (guild_id, current["human_role_id"], current["bot_role_id"]),
    )
    await db.commit()
    return current


# ── Reaction Roles ────────────────────────────────────────────────────────────

async def add_reaction_role(
    guild_id: int,
    channel_id: int,
    message_id: int,
    role_id: int,
    emoji: Optional[str] = None,
    label: Optional[str] = None,
    style: str = "primary",
) -> bool:
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO reaction_roles (guild_id, channel_id, message_id, role_id, emoji, label, style)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(message_id, role_id) DO UPDATE SET
                emoji = excluded.emoji,
                label = excluded.label,
                style = excluded.style
            """,
            (guild_id, channel_id, message_id, role_id, emoji, label, style),
        )
        await db.commit()
        return True
    except Exception as e:
        log.error(f"Error adding reaction role: {e}")
        return False


async def get_reaction_roles_for_message(message_id: int) -> list[dict[str, Any]]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM reaction_roles WHERE message_id = ?",
        (message_id,),
    ) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_all_reaction_roles(guild_id: int) -> list[dict[str, Any]]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM reaction_roles WHERE guild_id = ?",
        (guild_id,),
    ) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def delete_reaction_role(message_id: int, role_id: int) -> bool:
    db = await get_db()
    try:
        await db.execute(
            "DELETE FROM reaction_roles WHERE message_id = ? AND role_id = ?",
            (message_id, role_id),
        )
        await db.commit()
        return True
    except Exception as e:
        log.error(f"Error deleting reaction role: {e}")
        return False


# ── Verification ──────────────────────────────────────────────────────────────

async def get_verification_settings(guild_id: int) -> Optional[dict[str, Any]]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM verification_settings WHERE guild_id = ?",
        (guild_id,),
    ) as cur:
        row = await cur.fetchone()
        return dict(row) if row else None


async def set_verification_settings(
    guild_id: int,
    role_id: int,
    channel_id: Optional[int] = None,
    message_id: Optional[int] = None,
) -> bool:
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO verification_settings (guild_id, role_id, channel_id, message_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                role_id = excluded.role_id,
                channel_id = excluded.channel_id,
                message_id = excluded.message_id
            """,
            (guild_id, role_id, channel_id, message_id),
        )
        await db.commit()
        return True
    except Exception as e:
        log.error(f"Error saving verification settings: {e}")
        return False


# ── Join-To-Create (JTC) ──────────────────────────────────────────────────────

async def get_jtc_settings(guild_id: int) -> Optional[dict[str, Any]]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM jtc_settings WHERE guild_id = ?",
        (guild_id,),
    ) as cur:
        row = await cur.fetchone()
        return dict(row) if row else None


async def set_jtc_settings(
    guild_id: int,
    channel_id: int,
    category_id: Optional[int] = None,
    user_limit: int = 0,
) -> bool:
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO jtc_settings (guild_id, channel_id, category_id, user_limit)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                channel_id = excluded.channel_id,
                category_id = excluded.category_id,
                user_limit = excluded.user_limit
            """,
            (guild_id, channel_id, category_id, user_limit),
        )
        await db.commit()
        return True
    except Exception as e:
        log.error(f"Error saving JTC settings: {e}")
        return False


async def register_jtc_channel(channel_id: int, guild_id: int, owner_id: int) -> bool:
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO jtc_channels (channel_id, guild_id, owner_id, created_at) VALUES (?, ?, ?, ?)",
            (channel_id, guild_id, owner_id, time.time()),
        )
        await db.commit()
        return True
    except Exception as e:
        log.error(f"Error registering JTC channel: {e}")
        return False


async def remove_jtc_channel(channel_id: int) -> bool:
    db = await get_db()
    try:
        await db.execute("DELETE FROM jtc_channels WHERE channel_id = ?", (channel_id,))
        await db.commit()
        return True
    except Exception as e:
        log.error(f"Error removing JTC channel: {e}")
        return False


async def is_jtc_channel(channel_id: int) -> bool:
    db = await get_db()
    async with db.execute(
        "SELECT 1 FROM jtc_channels WHERE channel_id = ?",
        (channel_id,),
    ) as cur:
        return (await cur.fetchone()) is not None


# ── Welcome Settings (Extras) ─────────────────────────────────────────────────

async def get_welcome_extras(guild_id: int) -> dict[str, Any]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM welcome_settings WHERE guild_id = ?",
        (guild_id,),
    ) as cur:
        row = await cur.fetchone()
        defaults = {
            "guild_id": guild_id,
            "dm_enabled": 0,
            "dm_message": None,
            "role_id": None,
            "welcome_image_url": None,
            "leave_image_url": None,
            "welcome_color": "#5865F2",
            "welcome_format": "embed",
            "leave_format": "embed",
        }
        if row:
            res = dict(row)
            for k, v in defaults.items():
                if k not in res or res[k] is None:
                    res[k] = v
            return res
        return defaults


async def update_welcome_extras(guild_id: int, **kwargs) -> dict[str, Any]:
    current = await get_welcome_extras(guild_id)
    allowed = {
        "dm_enabled",
        "dm_message",
        "role_id",
        "welcome_image_url",
        "leave_image_url",
        "welcome_color",
        "welcome_format",
        "leave_format",
    }
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return current

    current.update(updates)
    db = await get_db()
    await db.execute(
        """
        INSERT INTO welcome_settings (
            guild_id, dm_enabled, dm_message, role_id,
            welcome_image_url, leave_image_url, welcome_color, welcome_format, leave_format
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET
            dm_enabled = excluded.dm_enabled,
            dm_message = excluded.dm_message,
            role_id = excluded.role_id,
            welcome_image_url = excluded.welcome_image_url,
            leave_image_url = excluded.leave_image_url,
            welcome_color = excluded.welcome_color,
            welcome_format = excluded.welcome_format,
            leave_format = excluded.leave_format
        """,
        (
            guild_id,
            current.get("dm_enabled", 0),
            current.get("dm_message"),
            current.get("role_id"),
            current.get("welcome_image_url"),
            current.get("leave_image_url"),
            current.get("welcome_color", "#5865F2"),
            current.get("welcome_format", "embed"),
            current.get("leave_format", "embed"),
        ),
    )
    await db.commit()
    return current
