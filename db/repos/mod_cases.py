"""
Repository for moderation action cases and jail records.
"""

import time
from typing import Optional, Any
from db.database import get_db


async def record_mod_case(
    guild_id: int,
    action: str,
    user_id: int,
    user_name: str,
    mod_id: int,
    mod_name: str,
    reason: Optional[str] = None,
    duration_seconds: Optional[int] = None,
) -> int:
    """Inserts a moderation case record and returns the assigned case_id."""
    db = await get_db()
    async with db.execute(
        """INSERT INTO mod_cases
           (guild_id, action, user_id, user_name, mod_id, mod_name, reason, duration_seconds, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            guild_id,
            action,
            user_id,
            user_name,
            mod_id,
            mod_name,
            reason or "No reason provided",
            duration_seconds,
            time.time(),
        ),
    ) as cur:
        case_id = cur.lastrowid
    await db.commit()
    return case_id or 0


async def get_user_mod_cases(
    guild_id: int, user_id: int, limit: int = 15, offset: int = 0
) -> list[dict[str, Any]]:
    """Fetches moderation cases for a specific user in a guild."""
    db = await get_db()
    async with db.execute(
        """SELECT * FROM mod_cases
           WHERE guild_id = ? AND user_id = ?
           ORDER BY case_id DESC
           LIMIT ? OFFSET ?""",
        (guild_id, user_id, limit, offset),
    ) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_guild_mod_cases(
    guild_id: int, limit: int = 25, offset: int = 0
) -> list[dict[str, Any]]:
    """Fetches recent moderation cases for an entire guild (for dashboard and audit)."""
    db = await get_db()
    async with db.execute(
        """SELECT * FROM mod_cases
           WHERE guild_id = ?
           ORDER BY case_id DESC
           LIMIT ? OFFSET ?""",
        (guild_id, limit, offset),
    ) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def count_user_cases(guild_id: int, user_id: int) -> int:
    """Returns the total number of disciplinary cases recorded for a user."""
    db = await get_db()
    async with db.execute(
        "SELECT COUNT(*) FROM mod_cases WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    ) as cur:
        row = await cur.fetchone()
        return row[0] if row else 0


async def save_jail_record(
    guild_id: int, user_id: int, role_ids: list[int], jailed_by: int, reason: Optional[str] = None
) -> None:
    """Stores the roles held by a user before jailing so they can be restored upon unjail."""
    db = await get_db()
    role_ids_str = ",".join(str(r) for r in role_ids)
    await db.execute(
        """INSERT OR REPLACE INTO jail_records
           (guild_id, user_id, role_ids, jailed_at, jailed_by, reason)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (guild_id, user_id, role_ids_str, time.time(), jailed_by, reason or "No reason provided"),
    )
    await db.commit()


async def get_jail_record(guild_id: int, user_id: int) -> Optional[dict[str, Any]]:
    """Fetches active jail record for a member if present."""
    db = await get_db()
    async with db.execute(
        "SELECT * FROM jail_records WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    ) as cur:
        row = await cur.fetchone()
        return dict(row) if row else None


async def delete_jail_record(guild_id: int, user_id: int) -> None:
    """Removes a jail record upon release."""
    db = await get_db()
    await db.execute(
        "DELETE FROM jail_records WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    )
    await db.commit()
