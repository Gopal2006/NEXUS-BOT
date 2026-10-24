"""
Repository for Engagement Systems: Leveling (XP), Birthdays, AFK, Autoresponder,
Sticky Messages, and Counting.
"""

import time
import json
import logging
from typing import Any, Optional
from db.database import get_db

log = logging.getLogger("Nexus.EngagementRepo")


# ── Leveling & XP Formulas ───────────────────────────────────────────────────

def xp_required_for_level(level: int) -> int:
    """Calculates total cumulative XP required to reach a specific level."""
    if level <= 0:
        return 0
    # Standard quadratic leveling curve
    return int(5 * (level ** 2) + 50 * level + 100)


def calculate_level_from_xp(total_xp: int) -> int:
    """Calculates the user's level based on cumulative XP."""
    level = 0
    while True:
        next_cost = xp_required_for_level(level + 1)
        if total_xp >= next_cost:
            level += 1
        else:
            break
    return level


async def get_level_settings(guild_id: int) -> dict[str, Any]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM level_settings WHERE guild_id = ?",
        (guild_id,),
    ) as cur:
        row = await cur.fetchone()
        if row:
            d = dict(row)
            d["role_rewards"] = json.loads(d.get("role_rewards_json") or "{}")
            return d

        default = {
            "guild_id": guild_id,
            "enabled": 1,
            "min_xp": 15,
            "max_xp": 25,
            "cooldown_seconds": 60,
            "channel_id": None,
            "levelup_message": "Congratulations {user}! You leveled up to **Level {level}**! 🎉",
            "role_rewards": {},
        }
        await db.execute(
            """INSERT OR IGNORE INTO level_settings (guild_id) VALUES (?)""",
            (guild_id,),
        )
        await db.commit()
        return default


async def update_level_settings(guild_id: int, **kwargs) -> dict[str, Any]:
    current = await get_level_settings(guild_id)
    if "role_rewards" in kwargs:
        kwargs["role_rewards_json"] = json.dumps(kwargs.pop("role_rewards"))

    allowed = {"enabled", "min_xp", "max_xp", "cooldown_seconds", "channel_id", "levelup_message", "role_rewards_json"}
    valid = {k: v for k, v in kwargs.items() if k in allowed}
    if not valid:
        return current

    fields = ", ".join(f"{k} = ?" for k in valid.keys())
    values = list(valid.values()) + [guild_id]

    db = await get_db()
    await db.execute(f"UPDATE level_settings SET {fields} WHERE guild_id = ?", values)
    await db.commit()
    return await get_level_settings(guild_id)


async def add_xp(guild_id: int, user_id: int, amount: int) -> tuple[bool, int, int]:
    """
    Adds XP to a user and updates message count.
    Returns (leveled_up: bool, new_level: int, current_xp: int).
    """
    now = time.time()
    db = await get_db()
    async with db.execute(
        "SELECT xp, level, messages FROM levels WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    ) as cur:
        row = await cur.fetchone()

    if row:
        current_xp = row["xp"] + amount
        old_level = row["level"]
        messages = row["messages"] + 1
    else:
        current_xp = amount
        old_level = 0
        messages = 1

    new_level = calculate_level_from_xp(current_xp)
    leveled_up = new_level > old_level

    await db.execute(
        """
        INSERT INTO levels (guild_id, user_id, xp, level, last_xp, messages)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(guild_id, user_id) DO UPDATE SET
            xp = excluded.xp,
            level = excluded.level,
            last_xp = excluded.last_xp,
            messages = excluded.messages
        """,
        (guild_id, user_id, current_xp, new_level, now, messages),
    )
    await db.commit()
    return leveled_up, new_level, current_xp


async def get_user_level(guild_id: int, user_id: int) -> dict[str, Any]:
    db = await get_db()
    async with db.execute(
        "SELECT xp, level, messages, last_xp FROM levels WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    ) as cur:
        row = await cur.fetchone()

    if not row:
        return {"xp": 0, "level": 0, "messages": 0, "rank": 1}

    data = dict(row)
    # Calculate rank
    async with db.execute(
        "SELECT COUNT(*) as rank FROM levels WHERE guild_id = ? AND xp > ?",
        (guild_id, data["xp"]),
    ) as cur:
        rank_row = await cur.fetchone()
        data["rank"] = (rank_row["rank"] if rank_row else 0) + 1

    return data


async def get_leaderboard(guild_id: int, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
    db = await get_db()
    async with db.execute(
        "SELECT user_id, xp, level, messages FROM levels WHERE guild_id = ? ORDER BY xp DESC LIMIT ? OFFSET ?",
        (guild_id, limit, offset),
    ) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# ── Birthdays ─────────────────────────────────────────────────────────────────

async def get_birthday(guild_id: int, user_id: int) -> Optional[dict[str, int]]:
    db = await get_db()
    async with db.execute(
        "SELECT month, day FROM birthdays WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    ) as cur:
        row = await cur.fetchone()
        return dict(row) if row else None


async def set_birthday(guild_id: int, user_id: int, month: int, day: int) -> bool:
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO birthdays (guild_id, user_id, month, day)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                month = excluded.month,
                day = excluded.day
            """,
            (guild_id, user_id, month, day),
        )
        await db.commit()
        return True
    except Exception as e:
        log.error(f"Error setting birthday: {e}")
        return False


async def get_birthday_settings(guild_id: int) -> dict[str, Any]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM birthday_settings WHERE guild_id = ?",
        (guild_id,),
    ) as cur:
        row = await cur.fetchone()
        if row:
            return dict(row)
        return {
            "guild_id": guild_id,
            "channel_id": None,
            "role_id": None,
            "message": "🎉 Happy Birthday {user}! 🎂 Hope you have an amazing day!",
        }


async def update_birthday_settings(guild_id: int, **kwargs) -> dict[str, Any]:
    current = await get_birthday_settings(guild_id)
    allowed = {"channel_id", "role_id", "message"}
    valid = {k: v for k, v in kwargs.items() if k in allowed}
    if not valid:
        return current

    current.update(valid)
    db = await get_db()
    await db.execute(
        """
        INSERT INTO birthday_settings (guild_id, channel_id, role_id, message)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET
            channel_id = excluded.channel_id,
            role_id = excluded.role_id,
            message = excluded.message
        """,
        (guild_id, current["channel_id"], current["role_id"], current["message"]),
    )
    await db.commit()
    return current


# ── AFK System ────────────────────────────────────────────────────────────────

async def set_afk(guild_id: int, user_id: int, reason: str = "AFK") -> None:
    db = await get_db()
    await db.execute(
        """
        INSERT INTO afk (guild_id, user_id, reason, timestamp)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(guild_id, user_id) DO UPDATE SET
            reason = excluded.reason,
            timestamp = excluded.timestamp
        """,
        (guild_id, user_id, reason, time.time()),
    )
    await db.commit()


async def get_afk(guild_id: int, user_id: int) -> Optional[dict[str, Any]]:
    db = await get_db()
    async with db.execute(
        "SELECT reason, timestamp FROM afk WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    ) as cur:
        row = await cur.fetchone()
        return dict(row) if row else None


async def remove_afk(guild_id: int, user_id: int) -> bool:
    db = await get_db()
    cur = await db.execute(
        "DELETE FROM afk WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    )
    await db.commit()
    return cur.rowcount > 0


# ── Autoresponder ─────────────────────────────────────────────────────────────

async def get_autoresponders(guild_id: int) -> list[dict[str, Any]]:
    db = await get_db()
    async with db.execute(
        "SELECT id, trigger, response, match_type FROM autoresponders WHERE guild_id = ?",
        (guild_id,),
    ) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def add_autoresponder(guild_id: int, trigger: str, response: str, match_type: str = "exact") -> bool:
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO autoresponders (guild_id, trigger, response, match_type)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, trigger) DO UPDATE SET
                response = excluded.response,
                match_type = excluded.match_type
            """,
            (guild_id, trigger.lower().strip(), response, match_type),
        )
        await db.commit()
        return True
    except Exception as e:
        log.error(f"Error adding autoresponder: {e}")
        return False


async def delete_autoresponder(guild_id: int, trigger: str) -> bool:
    db = await get_db()
    cur = await db.execute(
        "DELETE FROM autoresponders WHERE guild_id = ? AND trigger = ?",
        (guild_id, trigger.lower().strip()),
    )
    await db.commit()
    return cur.rowcount > 0


# ── Sticky Messages ───────────────────────────────────────────────────────────

async def get_sticky(channel_id: int) -> Optional[dict[str, Any]]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM sticky_messages WHERE channel_id = ?",
        (channel_id,),
    ) as cur:
        row = await cur.fetchone()
        return dict(row) if row else None


async def set_sticky(channel_id: int, guild_id: int, message: str, last_message_id: Optional[int] = None) -> None:
    db = await get_db()
    await db.execute(
        """
        INSERT INTO sticky_messages (channel_id, guild_id, message, last_message_id)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(channel_id) DO UPDATE SET
            message = excluded.message,
            last_message_id = excluded.last_message_id
        """,
        (channel_id, guild_id, message, last_message_id),
    )
    await db.commit()


async def remove_sticky(channel_id: int) -> bool:
    db = await get_db()
    cur = await db.execute("DELETE FROM sticky_messages WHERE channel_id = ?", (channel_id,))
    await db.commit()
    return cur.rowcount > 0


# ── Counting ──────────────────────────────────────────────────────────────────

async def get_counting(channel_id: int) -> Optional[dict[str, Any]]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM counting WHERE channel_id = ?",
        (channel_id,),
    ) as cur:
        row = await cur.fetchone()
        return dict(row) if row else None


async def set_counting(channel_id: int, guild_id: int, current_number: int = 0, last_user_id: Optional[int] = None) -> None:
    db = await get_db()
    await db.execute(
        """
        INSERT INTO counting (channel_id, guild_id, current_number, last_user_id)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(channel_id) DO UPDATE SET
            current_number = excluded.current_number,
            last_user_id = excluded.last_user_id
        """,
        (channel_id, guild_id, current_number, last_user_id),
    )
    await db.commit()


async def reset_counting(channel_id: int) -> None:
    db = await get_db()
    await db.execute("UPDATE counting SET current_number = 0, last_user_id = NULL WHERE channel_id = ?", (channel_id,))
    await db.commit()
