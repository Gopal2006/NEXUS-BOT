"""
Shared database manager, migration runner, and cached configuration repository.
Enforces WAL mode, schema migrations, and parameterized safe queries.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional
import aiosqlite

from core.config import DATABASE_PATH

log = logging.getLogger("Nexus.DB")

# Known columns for guild_config to prevent arbitrary SQL injection in dynamic updates
ALLOWED_CONFIG_COLUMNS = {
    "bot_role_id",
    "ticket_role_id",
    "welcome_ch",
    "leave_ch",
    "member_log_ch",
    "welcome_msg",
    "leave_msg",
    "log_ch",
    "mod_log_ch",
    "server_log_ch",
    "activity_log_ch",
    "cmd_log_ch",
}

# In-memory configuration cache: guild_id -> dict
_CONFIG_CACHE: dict[int, dict[str, Any]] = {}
_CACHE_LOCK = asyncio.Lock()

# Global database connection reference
_DB_CONN: Optional[aiosqlite.Connection] = None
_DB_LOCK = asyncio.Lock()


async def get_db() -> aiosqlite.Connection:
    """Returns a shared, WAL-mode SQLite connection."""
    global _DB_CONN
    async with _DB_LOCK:
        if _DB_CONN is None:
            _DB_CONN = await aiosqlite.connect(DATABASE_PATH)
            _DB_CONN.row_factory = aiosqlite.Row
            await _DB_CONN.execute("PRAGMA journal_mode=WAL;")
            await _DB_CONN.execute("PRAGMA synchronous=NORMAL;")
            await _DB_CONN.execute("PRAGMA foreign_keys=ON;")
            await _DB_CONN.commit()
    return _DB_CONN


async def close_db():
    """Gracefully closes the shared database connection."""
    global _DB_CONN
    async with _DB_LOCK:
        if _DB_CONN is not None:
            try:
                await _DB_CONN.close()
            except Exception:
                pass
            _DB_CONN = None


async def run_migrations():
    """Runs all numbered additive SQL migrations from db/migrations/."""
    db = await get_db()

    # Ensure migrations tracking table exists
    await db.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     TEXT PRIMARY KEY,
            applied_at  REAL NOT NULL
        );
    """)
    await db.commit()

    # Fetch already applied migrations
    async with db.execute("SELECT version FROM schema_migrations") as cur:
        applied = {row[0] for row in await cur.fetchall()}

    migrations_dir = Path(__file__).parent / "migrations"
    if migrations_dir.exists():
        sql_files = sorted(migrations_dir.glob("*.sql"))
        for sql_file in sql_files:
            version = sql_file.stem
            if version not in applied:
                log.info(f"Applying database migration: {version}...")
                with open(sql_file, "r", encoding="utf-8") as f:
                    sql_content = f.read()
                try:
                    await db.executescript(sql_content)
                    import time
                    await db.execute(
                        "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                        (version, time.time()),
                    )
                    await db.commit()
                    log.info(f"✓ Applied migration: {version}")
                except Exception as e:
                    log.error(f"Failed to apply migration {version}: {e}")
                    raise

    # Backwards-compatible column verification
    await _auto_migrate_legacy_columns(db)
    log.info("Database migrations complete ✓")


async def _auto_migrate_legacy_columns(db: aiosqlite.Connection):
    """Ensures legacy databases created before migrations have all required columns."""
    try:
        async with db.execute("PRAGMA table_info(guild_config)") as cur:
            existing_cols = [row[1] for row in await cur.fetchall()]

        legacy_cols = [
            ("ticket_role_id", "INTEGER DEFAULT NULL"),
            ("mod_log_ch", "INTEGER DEFAULT NULL"),
            ("server_log_ch", "INTEGER DEFAULT NULL"),
            ("activity_log_ch", "INTEGER DEFAULT NULL"),
            ("member_log_ch", "INTEGER DEFAULT NULL"),
            ("cmd_log_ch", "INTEGER DEFAULT NULL"),
        ]
        for col_name, col_type in legacy_cols:
            if col_name not in existing_cols:
                try:
                    await db.execute(f"ALTER TABLE guild_config ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass

        # Giveaways columns
        async with db.execute("PRAGMA table_info(giveaways)") as cur:
            gw_cols = [row[1] for row in await cur.fetchall()]
        if "required_role_id" not in gw_cols:
            try:
                await db.execute("ALTER TABLE giveaways ADD COLUMN required_role_id INTEGER DEFAULT NULL")
            except Exception:
                pass
        if "required_role_ids" not in gw_cols:
            try:
                await db.execute("ALTER TABLE giveaways ADD COLUMN required_role_ids TEXT DEFAULT NULL")
            except Exception:
                pass

        # welcome_settings columns
        async with db.execute("PRAGMA table_info(welcome_settings)") as cur:
            ws_cols = [row[1] for row in await cur.fetchall()]
        ws_new_cols = [
            ("welcome_image_url", "TEXT DEFAULT NULL"),
            ("leave_image_url", "TEXT DEFAULT NULL"),
            ("welcome_color", "TEXT DEFAULT '#5865F2'"),
            ("welcome_format", "TEXT DEFAULT 'embed'"),
            ("leave_format", "TEXT DEFAULT 'embed'"),
        ]
        for col_name, col_type in ws_new_cols:
            if col_name not in ws_cols:
                try:
                    await db.execute(f"ALTER TABLE welcome_settings ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass

        await db.commit()
    except Exception as e:
        log.warning(f"Legacy auto-migration check note: {e}")


# ── Guild Config Cache & Accessors ───────────────────────────────────────────

async def get_config(guild_id: int) -> dict[str, Any]:
    """
    Fetches the guild configuration with in-memory caching.
    Creates a default row if one does not already exist.
    """
    async with _CACHE_LOCK:
        if guild_id in _CONFIG_CACHE:
            return dict(_CONFIG_CACHE[guild_id])

    db = await get_db()
    async with db.execute("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)) as cur:
        row = await cur.fetchone()

    if row is None:
        await db.execute("INSERT OR IGNORE INTO guild_config (guild_id) VALUES (?)", (guild_id,))
        await db.commit()
        async with db.execute("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)) as cur:
            row = await cur.fetchone()

    config_dict = dict(row) if row else {"guild_id": guild_id}

    async with _CACHE_LOCK:
        _CONFIG_CACHE[guild_id] = config_dict

    return dict(config_dict)


async def set_config(guild_id: int, **kwargs: Any) -> None:
    """
    Updates guild configuration with column whitelist validation and cache invalidation.
    """
    valid_updates = {k: v for k, v in kwargs.items() if k in ALLOWED_CONFIG_COLUMNS}
    if not valid_updates:
        return

    sets = ", ".join(f"{k} = ?" for k in valid_updates)
    vals = list(valid_updates.values()) + [guild_id]

    db = await get_db()
    # Ensure row exists before update
    await db.execute("INSERT OR IGNORE INTO guild_config (guild_id) VALUES (?)", (guild_id,))
    await db.execute(f"UPDATE guild_config SET {sets} WHERE guild_id = ?", vals)
    await db.commit()

    # Invalidate cache so subsequent reads reflect new values
    async with _CACHE_LOCK:
        if guild_id in _CONFIG_CACHE:
            _CONFIG_CACHE[guild_id].update(valid_updates)
        else:
            _CONFIG_CACHE.pop(guild_id, None)


async def invalidate_config_cache(guild_id: Optional[int] = None):
    """Clears the config cache for a specific guild or globally."""
    async with _CACHE_LOCK:
        if guild_id is not None:
            _CONFIG_CACHE.pop(guild_id, None)
        else:
            _CONFIG_CACHE.clear()


# ── Non-Prefix User Store ────────────────────────────────────────────────────

async def get_non_prefix_users() -> set[int]:
    """Loads all authorized non-prefix user IDs from SQLite."""
    db = await get_db()
    try:
        async with db.execute("SELECT user_id FROM non_prefix_users") as cur:
            rows = await cur.fetchall()
            return {row[0] for row in rows}
    except Exception as e:
        log.error(f"Error fetching non-prefix users: {e}")
        return set()


async def add_non_prefix_user(user_id: int, added_by: int) -> None:
    """Grants non-prefix access to a user."""
    import time
    db = await get_db()
    await db.execute(
        "INSERT OR REPLACE INTO non_prefix_users (user_id, added_by, added_at) VALUES (?, ?, ?)",
        (user_id, added_by, time.time()),
    )
    await db.commit()


async def remove_non_prefix_user(user_id: int) -> None:
    """Revokes non-prefix access from a user."""
    db = await get_db()
    await db.execute("DELETE FROM non_prefix_users WHERE user_id = ?", (user_id,))
    await db.commit()
