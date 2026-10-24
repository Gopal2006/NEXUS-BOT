"""
Nexus Discord Bot — Web Control Dashboard Server
Provides a modern REST API, WebSocket live streaming, and static web interface
to manage, configure, and control Nexus Bot in real-time.
"""

import os
import sys
import time
import json
import asyncio
import threading
import logging
import datetime
import secrets
import hashlib
import math
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from aiohttp import web, WSMsgType
import aiosqlite
import discord

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DB_PATH = Path("nexus.db")
GLOBAL_OWNER_ID = int(os.getenv("OWNER_ID") or 1201050377911554061)
DEFAULT_OWNER_PASSCODE = os.getenv("DASHBOARD_PASSCODE") or os.getenv("ADMIN_PASSCODE") or "nexus-owner-2026"


# ── Global Bot Instance Reference ─────────────────────────────────────────────
_BOT_INSTANCE: Optional[Any] = None
_SERVER_START_TIME = time.time()

def set_bot(bot: Any):
    global _BOT_INSTANCE
    _BOT_INSTANCE = bot

def get_bot() -> Optional[Any]:
    return _BOT_INSTANCE

async def call_bot(coro):
    """Safely execute a coroutine on the bot's event loop from the dashboard thread."""
    bot = get_bot()
    if not bot:
        return await coro
    loop = getattr(bot, "loop", None)
    if not loop or not loop.is_running():
        return await coro
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if current_loop is loop:
        return await coro

    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return await asyncio.wrap_future(future)


# ── Circular Log Buffer & Streaming Handler ───────────────────────────────────
class WebSocketLogHandler(logging.Handler):
    """Captures log records and broadcasts them to connected WebSocket clients."""

    def __init__(self, max_records: int = 500):
        super().__init__()
        self.max_records = max_records
        self.records: List[Dict[str, Any]] = []
        self.ws_clients: set = set()

    def emit(self, record: logging.LogRecord):
        # Don't buffer or broadcast access logs to avoid infinite loop cascades
        if record.name.startswith("aiohttp.access"):
            return

        try:
            msg = self.format(record)
            log_entry = {
                "timestamp": datetime.datetime.fromtimestamp(record.created).strftime("%H:%M:%S"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "formatted": msg,
            }
            self.records.append(log_entry)
            if len(self.records) > self.max_records:
                self.records.pop(0)

            # Broadcast to active WebSockets in asyncio loop if running
            if self.ws_clients:
                payload = json.dumps({"type": "log", "data": log_entry})
                try:
                    loop = asyncio.get_running_loop()
                    for ws in list(self.ws_clients):
                        if not ws.closed:
                            loop.create_task(ws.send_str(payload))
                except (RuntimeError, Exception):
                    pass
        except Exception:
            self.handleError(record)


log_handler = WebSocketLogHandler()
log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S"))
logging.getLogger().addHandler(log_handler)
log = logging.getLogger("Nexus.Dashboard")


# ── Database Utilities ────────────────────────────────────────────────────────
async def init_dashboard_db():
    """Ensure database tables exist so dashboard works even before bot starts."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id        INTEGER PRIMARY KEY,
                bot_role_id     INTEGER DEFAULT NULL,
                ticket_role_id  INTEGER DEFAULT NULL,
                welcome_ch      INTEGER DEFAULT NULL,
                leave_ch        INTEGER DEFAULT NULL,
                member_log_ch   INTEGER DEFAULT NULL,
                welcome_msg     TEXT    DEFAULT 'Welcome {mention} to **{guild}**! 🎉',
                leave_msg       TEXT    DEFAULT '**{name}** has left the server. Goodbye! 👋',
                log_ch          INTEGER DEFAULT NULL,
                mod_log_ch      INTEGER DEFAULT NULL,
                server_log_ch   INTEGER DEFAULT NULL,
                activity_log_ch INTEGER DEFAULT NULL,
                cmd_log_ch      INTEGER DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS non_prefix_users (
                user_id   INTEGER PRIMARY KEY,
                added_by  INTEGER NOT NULL,
                added_at  REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS giveaways (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id         INTEGER NOT NULL,
                channel_id       INTEGER NOT NULL,
                message_id       INTEGER NOT NULL,
                host_id          INTEGER NOT NULL,
                prize            TEXT    NOT NULL,
                winners          INTEGER NOT NULL DEFAULT 1,
                ends_at          REAL    NOT NULL,
                ended            INTEGER NOT NULL DEFAULT 0,
                required_role_id INTEGER DEFAULT NULL,
                required_role_ids TEXT DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS giveaway_ineligible_dms (
                giveaway_id INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                notified_at REAL NOT NULL,
                PRIMARY KEY (giveaway_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS warns (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id  INTEGER NOT NULL,
                user_id   INTEGER NOT NULL,
                mod_id    INTEGER NOT NULL,
                reason    TEXT,
                timestamp REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tickets (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id   INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                status     TEXT NOT NULL DEFAULT 'open'
            );

            CREATE TABLE IF NOT EXISTS mutes (
                guild_id INTEGER NOT NULL,
                user_id  INTEGER NOT NULL,
                ends_at  REAL,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS dashboard_users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER UNIQUE NOT NULL,
                username   TEXT NOT NULL,
                role       TEXT NOT NULL DEFAULT 'operator',
                passcode   TEXT NOT NULL,
                is_active  INTEGER NOT NULL DEFAULT 1,
                created_by INTEGER NOT NULL,
                created_at REAL NOT NULL,
                last_login REAL DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS dashboard_sessions (
                token       TEXT PRIMARY KEY,
                user_id     INTEGER NOT NULL,
                username    TEXT NOT NULL,
                role        TEXT NOT NULL,
                ip_address  TEXT NOT NULL,
                user_agent  TEXT,
                created_at  REAL NOT NULL,
                last_active REAL NOT NULL,
                expires_at  REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS dashboard_audit_logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp  REAL NOT NULL,
                user_id    INTEGER NOT NULL,
                username   TEXT NOT NULL,
                role       TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                action     TEXT NOT NULL,
                guild_id   INTEGER DEFAULT NULL,
                target_id  TEXT DEFAULT NULL,
                details    TEXT NOT NULL,
                status     TEXT NOT NULL DEFAULT 'SUCCESS'
            );
        """)
        await db.commit()

        # Seed Master Bot Owner
        now = time.time()
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM dashboard_users WHERE user_id = ?", (GLOBAL_OWNER_ID,)) as cur:
            owner_entry = await cur.fetchone()

        bot = get_bot()
        owner_name = "Nexus Owner"
        if bot and bot.user:
            owner_user = bot.get_user(GLOBAL_OWNER_ID)
            if owner_user:
                owner_name = f"{owner_user.name} (Owner)"

        if not owner_entry:
            await db.execute(
                """INSERT INTO dashboard_users (user_id, username, role, passcode, is_active, created_by, created_at)
                   VALUES (?, ?, 'owner', ?, 1, ?, ?)""",
                (GLOBAL_OWNER_ID, owner_name, DEFAULT_OWNER_PASSCODE, GLOBAL_OWNER_ID, now)
            )
            await db.commit()
            log.info(f"👑 Dashboard Master Owner seeded: ID={GLOBAL_OWNER_ID} | Passcode={DEFAULT_OWNER_PASSCODE}")
        else:
            # Keep owner role and active
            await db.execute(
                "UPDATE dashboard_users SET role = 'owner', is_active = 1 WHERE user_id = ?",
                (GLOBAL_OWNER_ID,)
            )
            await db.commit()


# ── Client Identity & Audit Trail Helpers ─────────────────────────────────────

def get_client_ip(request: Optional[web.Request]) -> str:
    if not request:
        return "127.0.0.1"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote or "127.0.0.1"


async def get_session_user(request: web.Request) -> Optional[Dict[str, Any]]:
    """Validates session token from Header, Cookie, or Query param."""
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "nexus_session" in request.cookies:
        token = request.cookies.get("nexus_session")
    elif "token" in request.query:
        token = request.query.get("token")

    if not token:
        return None

    await init_dashboard_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        now = time.time()
        async with db.execute(
            "SELECT * FROM dashboard_sessions WHERE token = ? AND expires_at > ?",
            (token, now)
        ) as cur:
            session = await cur.fetchone()

        if not session:
            return None

        async with db.execute(
            "SELECT * FROM dashboard_users WHERE user_id = ? AND is_active = 1",
            (session["user_id"],)
        ) as cur:
            user_row = await cur.fetchone()

        if not user_row:
            return None

        # Update activity timestamp
        await db.execute(
            "UPDATE dashboard_sessions SET last_active = ? WHERE token = ?",
            (now, token)
        )
        await db.commit()

        role = str(user_row["role"]).lower()
        return {
            "user_id": int(user_row["user_id"]),
            "username": str(user_row["username"]),
            "role": role,
            "is_admin": (role in ("owner", "admin") or int(user_row["user_id"]) == GLOBAL_OWNER_ID),
            "token": token,
            "ip_address": get_client_ip(request),
        }


async def require_auth(request: web.Request) -> Tuple[Optional[Dict[str, Any]], Optional[web.Response]]:
    """Middleware guard ensuring caller is an active authenticated user."""
    user = await get_session_user(request)
    if not user:
        return None, web.json_response(
            {"success": False, "error": "Authentication required. Please sign in to Nexus Control Center.", "requires_login": True},
            status=401
        )
    return user, None


async def require_admin(request: web.Request) -> Tuple[Optional[Dict[str, Any]], Optional[web.Response]]:
    """Middleware guard ensuring caller has Administrator or Owner privileges."""
    user, err_resp = await require_auth(request)
    if err_resp:
        return None, err_resp
    if not user.get("is_admin"):
        return None, web.json_response(
            {"success": False, "error": "Access denied: Administrator permissions required to access the Admin Panel."},
            status=403
        )
    return user, None


async def record_audit(
    user: Optional[Dict[str, Any]],
    action: str,
    details: str,
    guild_id: Optional[int] = None,
    target_id: Optional[str] = None,
    status: str = "SUCCESS",
    request: Optional[web.Request] = None
):
    """Logs action into SQLite database and broadcasts to live streaming terminal."""
    ip = get_client_ip(request) if request else (user.get("ip_address", "127.0.0.1") if user else "127.0.0.1")
    u_id = user.get("user_id", 0) if user else 0
    u_name = user.get("username", "System") if user else "System"
    u_role = user.get("role", "system") if user else "system"

    now = time.time()
    try:
        await init_dashboard_db()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO dashboard_audit_logs 
                   (timestamp, user_id, username, role, ip_address, action, guild_id, target_id, details, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (now, u_id, u_name, u_role, ip, action, guild_id, str(target_id) if target_id else None, details, status)
            )
            await db.commit()
    except Exception as e:
        log.error(f"Failed to write audit log: {e}")

    log.info(f"[AUDIT] {u_name} ({u_id}) - {action}: {details}")



async def get_guild_config(guild_id: int) -> dict:
    await init_dashboard_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)) as cur:
            row = await cur.fetchone()
        if row is None:
            await db.execute("INSERT INTO guild_config (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
            async with db.execute("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)) as cur:
                row = await cur.fetchone()
        return dict(row)


async def save_guild_config(guild_id: int, **kwargs):
    await init_dashboard_db()
    valid_cols = {
        "bot_role_id", "ticket_role_id", "welcome_ch", "leave_ch",
        "member_log_ch", "welcome_msg", "leave_msg", "log_ch",
        "mod_log_ch", "server_log_ch", "activity_log_ch", "cmd_log_ch"
    }
    filtered = {k: v for k, v in kwargs.items() if k in valid_cols}
    if not filtered:
        return
    sets = ", ".join(f"{k} = ?" for k in filtered)
    vals = list(filtered.values()) + [guild_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE guild_config SET {sets} WHERE guild_id = ?", vals)
        await db.commit()


# ── Color Presets & Helpers ───────────────────────────────────────────────────
COLOR_PRESETS = {
    "blurple": 0x5865F2,
    "blue":    0x3498DB,
    "red":     0xED4245,
    "green":   0x57F287,
    "gold":    0xFEE75C,
    "yellow":  0xFFFF00,
    "purple":  0x9B59B6,
    "fuchsia": 0xEB459E,
    "pink":    0xFF70A6,
    "cyan":    0x1ABC9C,
    "teal":    0x008080,
    "orange":  0xE67E22,
    "black":   0x23272A,
    "dark":    0x2B2D31,
    "white":   0xFFFFFF,
}

def parse_color(color_val: str, default: int = 0x5865F2) -> int:
    if not color_val:
        return default
    cleaned = str(color_val).strip().lower()
    if cleaned in COLOR_PRESETS:
        return COLOR_PRESETS[cleaned]
    clean_hex = cleaned.lstrip("#")
    try:
        return int(clean_hex, 16)
    except ValueError:
        return default

def build_button_view(button_str: str) -> Optional[discord.ui.View]:
    if not button_str:
        return None
    raw = button_str.strip()
    if "|" in raw:
        parts = raw.split("|", 1)
        label = parts[0].strip()[:80]
        url = parts[1].strip()
    else:
        label = "Open Link"
        url = raw

    if not (url.startswith("http://") or url.startswith("https://") or url.startswith("discord://")):
        return None

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label=label, url=url, style=discord.ButtonStyle.link))
    return view


# ── Memory & Process Info ─────────────────────────────────────────────────────
def get_system_stats() -> dict:
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem_mb = round(process.memory_info().rss / (1024 * 1024), 1)
        cpu_pct = process.cpu_percent(interval=None)
    except ImportError:
        mem_mb = "N/A"
        cpu_pct = "N/A"

    uptime_sec = time.time() - _SERVER_START_TIME
    d, rem = divmod(int(uptime_sec), 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    uptime_str = f"{d}d {h}h {m}m" if d else (f"{h}h {m}m {s}s" if h else f"{m}m {s}s")

    return {
        "uptime_str": uptime_str,
        "uptime_sec": int(uptime_sec),
        "memory_mb": mem_mb,
        "cpu_pct": cpu_pct,
    }


# ── Authentication & Session Handlers ────────────────────────────────────────

async def api_auth_login(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"success": False, "error": "Invalid request body"}, status=400)

    user_id_raw = data.get("user_id")
    passcode = str(data.get("passcode", "")).strip()

    if not user_id_raw or not passcode:
        return web.json_response({"success": False, "error": "User ID and passcode are required."}, status=400)

    try:
        user_id = int(str(user_id_raw).strip())
    except ValueError:
        return web.json_response({"success": False, "error": "Discord User ID must be numerical."}, status=400)

    await init_dashboard_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM dashboard_users WHERE user_id = ?", (user_id,)) as cur:
            user = await cur.fetchone()

    if not user:
        return web.json_response({"success": False, "error": "User not authorized. Please ask an Administrator to add you to the dashboard."}, status=403)

    if not user["is_active"]:
        return web.json_response({"success": False, "error": "This account is currently deactivated by the administrator."}, status=403)

    if user["passcode"] != passcode:
        await record_audit(None, "FAILED_LOGIN", f"Invalid passcode attempt for User ID {user_id}", target_id=str(user_id), status="FAILED", request=request)
        return web.json_response({"success": False, "error": "Invalid passcode."}, status=401)

    # Validated — create session
    token = secrets.token_urlsafe(32)
    now = time.time()
    expires_at = now + (7 * 86400)
    ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "Unknown")[:250]

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO dashboard_sessions (token, user_id, username, role, ip_address, user_agent, created_at, last_active, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (token, user_id, user["username"], user["role"], ip, user_agent, now, now, expires_at)
        )
        await db.execute("UPDATE dashboard_users SET last_login = ? WHERE user_id = ?", (now, user_id))
        await db.commit()

    bot = get_bot()
    avatar_url = None
    if bot:
        discord_user = bot.get_user(user_id)
        if discord_user and hasattr(discord_user, "display_avatar"):
            avatar_url = str(discord_user.display_avatar.url)

    role = str(user["role"]).lower()
    is_admin = (role in ("owner", "admin") or user_id == GLOBAL_OWNER_ID)

    session_user_dict = {
        "user_id": user_id,
        "username": user["username"],
        "name": user["username"],
        "role": role,
        "ip_address": ip,
    }
    await record_audit(session_user_dict, "USER_LOGIN", f"User logged into dashboard from {ip}", request=request)

    resp = web.json_response({
        "success": True,
        "token": token,
        "user": {
            "user_id": str(user_id),
            "username": user["username"],
            "name": user["username"],
            "role": role,
            "is_admin": is_admin,
            "avatar_url": avatar_url,
        }
    })
    resp.set_cookie("nexus_session", token, max_age=7*86400, httponly=True, samesite="Lax")
    return resp


async def api_auth_me(request: web.Request) -> web.Response:
    user = await get_session_user(request)
    if not user:
        return web.json_response({"authenticated": False})

    bot = get_bot()
    avatar_url = None
    if bot:
        discord_user = bot.get_user(user["user_id"])
        if discord_user and hasattr(discord_user, "display_avatar"):
            avatar_url = str(discord_user.display_avatar.url)

    return web.json_response({
        "authenticated": True,
        "user": {
            "user_id": str(user["user_id"]),
            "username": user["username"],
            "name": user["username"],
            "role": user["role"],
            "is_admin": user["is_admin"],
            "avatar_url": avatar_url,
        }
    })


async def api_auth_logout(request: web.Request) -> web.Response:
    user = await get_session_user(request)
    if user:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM dashboard_sessions WHERE token = ?", (user["token"],))
            await db.commit()
        await record_audit(user, "USER_LOGOUT", f"User logged out from {user['ip_address']}", request=request)

    resp = web.json_response({"success": True})
    resp.del_cookie("nexus_session")
    return resp


# ── Admin Panel Endpoints (Owner & Manually Added Admins Only) ────────────────

async def api_admin_users(request: web.Request) -> web.Response:
    admin_user, err = await require_admin(request)
    if err:
        return err

    await init_dashboard_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, user_id, username, role, is_active, created_by, created_at, last_login, passcode FROM dashboard_users ORDER BY (role='owner') DESC, id ASC"
        ) as cur:
            rows = await cur.fetchall()

    bot = get_bot()
    user_list = []
    for r in rows:
        u_id = r["user_id"]
        avatar = None
        if bot:
            u_obj = bot.get_user(u_id)
            if u_obj and hasattr(u_obj, "display_avatar"):
                avatar = str(u_obj.display_avatar.url)

        user_list.append({
            "id": r["id"],
            "user_id": str(u_id),
            "username": r["username"],
            "name": r["username"],
            "role": r["role"],
            "is_active": bool(r["is_active"]),
            "created_by": str(r["created_by"]),
            "added_by": str(r["created_by"]),
            "created_at": datetime.datetime.fromtimestamp(r["created_at"]).strftime("%Y-%m-%d %H:%M") if r["created_at"] else "N/A",
            "last_login": datetime.datetime.fromtimestamp(r["last_login"]).strftime("%Y-%m-%d %H:%M") if r["last_login"] else "Never",
            "avatar_url": avatar,
            "passcode": r["passcode"] if (admin_user["role"] == "owner" or admin_user["user_id"] == u_id) else "••••••••",
        })
    return web.json_response({"success": True, "users": user_list})


async def api_admin_users_add(request: web.Request) -> web.Response:
    admin_user, err = await require_admin(request)
    if err:
        return err

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"success": False, "error": "Invalid JSON"}, status=400)

    user_id_raw = data.get("user_id")
    username = str(data.get("username", "") or data.get("name", "")).strip()
    role = str(data.get("role", "operator")).strip().lower()
    passcode = str(data.get("passcode", "")).strip()

    if not user_id_raw:
        return web.json_response({"success": False, "error": "Discord User ID is required"}, status=400)

    try:
        user_id = int(str(user_id_raw).strip())
    except ValueError:
        return web.json_response({"success": False, "error": "User ID must be numerical"}, status=400)

    if role not in ("admin", "operator"):
        role = "operator"

    # Only owner can add admins
    if role == "admin" and admin_user["role"] != "owner" and admin_user["user_id"] != GLOBAL_OWNER_ID:
        return web.json_response({"success": False, "error": "Only the bot owner can assign Administrator access."}, status=403)

    if not passcode:
        passcode = secrets.token_hex(4)

    bot = get_bot()
    if not username and bot:
        u_obj = bot.get_user(user_id)
        if u_obj:
            username = str(u_obj.name)
    if not username:
        username = f"User {user_id}"

    now = time.time()
    await init_dashboard_db()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO dashboard_users (user_id, username, role, passcode, is_active, created_by, created_at)
               VALUES (?, ?, ?, ?, 1, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
               username = excluded.username,
               role = excluded.role,
               passcode = excluded.passcode,
               is_active = 1""",
            (user_id, username, role, passcode, admin_user["user_id"], now)
        )
        await db.commit()

    await record_audit(
        admin_user, "ADMIN_ADD_USER",
        f"Added/Updated user {username} ({user_id}) with role '{role}' and passcode '{passcode}'",
        target_id=str(user_id),
        request=request
    )
    return web.json_response({
        "success": True,
        "passcode": passcode,
        "username": username,
        "name": username,
        "user_id": str(user_id),
        "role": role
    })


async def api_admin_users_toggle(request: web.Request) -> web.Response:
    admin_user, err = await require_admin(request)
    if err:
        return err

    data = await request.json()
    user_id = int(data.get("user_id"))
    is_active = 1 if data.get("is_active", True) else 0

    if user_id == GLOBAL_OWNER_ID:
        return web.json_response({"success": False, "error": "Cannot deactivate the Bot Owner."}, status=400)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE dashboard_users SET is_active = ? WHERE user_id = ?", (is_active, user_id))
        if not is_active:
            await db.execute("DELETE FROM dashboard_sessions WHERE user_id = ?", (user_id,))
        await db.commit()

    await record_audit(
        admin_user, "ADMIN_TOGGLE_USER",
        f"{'Activated' if is_active else 'Deactivated'} access for User ID {user_id}",
        target_id=str(user_id),
        request=request
    )
    return web.json_response({"success": True})


async def api_admin_users_delete(request: web.Request) -> web.Response:
    admin_user, err = await require_admin(request)
    if err:
        return err

    data = await request.json()
    user_id = int(data.get("user_id"))

    if user_id == GLOBAL_OWNER_ID:
        return web.json_response({"success": False, "error": "Cannot delete the Bot Owner."}, status=400)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM dashboard_users WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM dashboard_sessions WHERE user_id = ?", (user_id,))
        await db.commit()

    await record_audit(
        admin_user, "ADMIN_DELETE_USER",
        f"Deleted User ID {user_id} from dashboard access",
        target_id=str(user_id),
        request=request
    )
    return web.json_response({"success": True})


async def api_admin_users_reset_passcode(request: web.Request) -> web.Response:
    admin_user, err = await require_admin(request)
    if err:
        return err

    data = await request.json()
    user_id = int(data.get("user_id"))
    new_passcode = str(data.get("passcode", "")).strip() or secrets.token_hex(4)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE dashboard_users SET passcode = ? WHERE user_id = ?", (new_passcode, user_id))
        await db.execute("DELETE FROM dashboard_sessions WHERE user_id = ?", (user_id,))
        await db.commit()

    await record_audit(
        admin_user, "ADMIN_RESET_PASSCODE",
        f"Reset passcode for User ID {user_id}",
        target_id=str(user_id),
        request=request
    )
    return web.json_response({"success": True, "passcode": new_passcode})


async def api_admin_sessions(request: web.Request) -> web.Response:
    admin_user, err = await require_admin(request)
    if err:
        return err

    await init_dashboard_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT token, user_id, username, role, ip_address, user_agent, created_at, last_active, expires_at FROM dashboard_sessions ORDER BY last_active DESC"
        ) as cur:
            rows = await cur.fetchall()

    sessions = []
    now = time.time()
    for r in rows:
        token_str = r["token"]
        sessions.append({
            "token_masked": token_str[:8] + "..." + token_str[-4:] if len(token_str) > 12 else token_str,
            "token": token_str,
            "token_hash": token_str,
            "user_id": str(r["user_id"]),
            "username": r["username"],
            "name": r["username"],
            "role": r["role"],
            "ip_address": r["ip_address"],
            "user_agent": r["user_agent"] or "Unknown",
            "created_at": datetime.datetime.fromtimestamp(r["created_at"]).strftime("%Y-%m-%d %H:%M"),
            "last_active": datetime.datetime.fromtimestamp(r["last_active"]).strftime("%H:%M:%S"),
            "active_ago_sec": max(0, int(now - r["last_active"])),
            "is_current": token_str == admin_user.get("token"),
        })
    return web.json_response({"success": True, "sessions": sessions})


async def api_admin_sessions_terminate(request: web.Request) -> web.Response:
    admin_user, err = await require_admin(request)
    if err:
        return err

    data = await request.json()
    token = data.get("token") or data.get("token_hash")
    user_id = data.get("user_id")

    async with aiosqlite.connect(DB_PATH) as db:
        if token:
            await db.execute("DELETE FROM dashboard_sessions WHERE token = ?", (token,))
        elif user_id:
            await db.execute("DELETE FROM dashboard_sessions WHERE user_id = ?", (int(user_id),))
        await db.commit()

    await record_audit(
        admin_user, "ADMIN_TERMINATE_SESSION",
        f"Force-terminated active session(s) (token={token[:8] if token else None}, user_id={user_id})",
        request=request
    )
    return web.json_response({"success": True})


async def api_admin_audit_logs(request: web.Request) -> web.Response:
    admin_user, err = await require_admin(request)
    if err:
        return err

    limit = min(200, max(10, int(request.query.get("limit", 100))))
    action_filter = request.query.get("action")
    user_filter = request.query.get("user_id")

    query = "SELECT * FROM dashboard_audit_logs"
    params = []
    conditions = []
    if action_filter:
        conditions.append("action LIKE ?")
        params.append(f"{action_filter}%")
    if user_filter:
        conditions.append("user_id = ?")
        params.append(int(user_filter))

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    await init_dashboard_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cur:
            rows = await cur.fetchall()

    logs = []
    for r in rows:
        logs.append({
            "id": r["id"],
            "timestamp": datetime.datetime.fromtimestamp(r["timestamp"]).strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": str(r["user_id"]),
            "username": r["username"],
            "user_name": r["username"],
            "role": r["role"],
            "ip_address": r["ip_address"],
            "action": r["action"],
            "guild_id": str(r["guild_id"]) if r["guild_id"] else None,
            "target_id": str(r["target_id"]) if r["target_id"] else None,
            "details": r["details"],
            "status": r["status"],
        })
    return web.json_response({"success": True, "logs": logs})


# ── REST API Handlers ─────────────────────────────────────────────────────────


async def api_status(request: web.Request) -> web.Response:
    bot = get_bot()
    sys_stats = get_system_stats()

    bot_ready = getattr(bot, "is_ready", lambda: False)() if bot else False
    bot_closed = getattr(bot, "is_closed", lambda: True)() if bot else True
    bot_user = getattr(bot, "user", None) if bot else None

    lat = getattr(bot, "latency", None) if bot else None
    valid_latency = (
        lat is not None
        and not math.isinf(lat)
        and not math.isnan(lat)
        and 0 <= lat < 60.0
    )

    is_online = (
        bot is not None
        and not bot_closed
        and (bot_ready or bot_user is not None)
        and valid_latency
    )

    ping_ms = round(lat * 1000) if (valid_latency and lat > 0) else None

    bot_info = {
        "online": is_online,
        "uptime": sys_stats["uptime_str"],
        "uptime_seconds": sys_stats["uptime_sec"],
        "memory_mb": sys_stats["memory_mb"],
        "cpu_pct": sys_stats["cpu_pct"],
        "ping_ms": ping_ms,
        "guild_count": len(bot.guilds) if (is_online and bot and hasattr(bot, "guilds")) else 0,
        "user_count": sum(g.member_count or 0 for g in bot.guilds) if (is_online and bot and hasattr(bot, "guilds")) else 0,
        "bot_user": {
            "name": bot_user.name if bot_user else "Nexus Bot",
            "discriminator": bot_user.discriminator if bot_user else "0000",
            "id": str(bot_user.id) if bot_user else None,
            "avatar_url": str(bot_user.display_avatar.url) if bot_user and hasattr(bot_user, "display_avatar") else None,
        } if bot_user else None,
        "status": str(bot.status) if (is_online and bot and hasattr(bot, "status")) else "offline",
        "activity": {
            "type": str(bot.activity.type.name) if (is_online and bot and bot.activity and hasattr(bot.activity, "type")) else "None",
            "name": str(bot.activity.name) if (is_online and bot and bot.activity and hasattr(bot.activity, "name")) else "",
        } if (is_online and bot and bot.activity) else None,
    }

    # Count database items (fast read queries)
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM giveaways WHERE ended=0") as cur:
                active_giveaways = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM tickets WHERE status='open'") as cur:
                open_tickets = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM warns") as cur:
                total_warns = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM non_prefix_users") as cur:
                non_prefix_count = (await cur.fetchone())[0]
        bot_info["db_stats"] = {
            "active_giveaways": active_giveaways,
            "open_tickets": open_tickets,
            "total_warns": total_warns,
            "non_prefix_users": non_prefix_count,
        }
    except Exception:
        bot_info["db_stats"] = {"active_giveaways": 0, "open_tickets": 0, "total_warns": 0, "non_prefix_users": 0}

    return web.json_response(bot_info)


async def api_set_presence(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    if not bot or not bot.is_ready():
        return web.json_response({"success": False, "error": "Bot is currently offline"}, status=400)

    try:
        data = await request.json()
        status_str = data.get("status", "online").lower()
        act_type = data.get("activity_type", "playing").lower()
        act_name = data.get("activity_name", "").strip()

        status_map = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible,
        }
        target_status = status_map.get(status_str, discord.Status.online)

        activity = None
        if act_name:
            if act_type == "watching":
                activity = discord.Activity(type=discord.ActivityType.watching, name=act_name)
            elif act_type == "listening":
                activity = discord.Activity(type=discord.ActivityType.listening, name=act_name)
            elif act_type == "competing":
                activity = discord.Activity(type=discord.ActivityType.competing, name=act_name)
            elif act_type == "streaming":
                activity = discord.Streaming(name=act_name, url=data.get("stream_url", "https://twitch.tv/discord"))
            else:
                activity = discord.Game(name=act_name)

        await call_bot(bot.change_presence(status=target_status, activity=activity))
        await record_audit(
            user, "SET_PRESENCE",
            f"Set bot presence: status={status_str}, type={act_type}, name='{act_name}'",
            request=request
        )
        return web.json_response({"success": True})
    except Exception as e:
        log.error(f"Failed to set bot presence: {e}")
        return web.json_response({"success": False, "error": str(e)}, status=500)


async def api_guilds(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    if not bot or not bot.is_ready():
        # Fallback to guilds in database
        guilds_data = []
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM guild_config") as cur:
                    rows = await cur.fetchall()
                for r in rows:
                    guilds_data.append({
                        "id": str(r["guild_id"]),
                        "name": f"Guild {r['guild_id']}",
                        "icon": None,
                        "member_count": 0,
                        "owner_id": None,
                        "channels": [],
                        "roles": [],
                    })
        except Exception:
            pass
        return web.json_response({"online": False, "guilds": guilds_data})

    guilds_data = []
    for g in bot.guilds:
        text_channels = [
            {"id": str(ch.id), "name": ch.name, "type": "text"}
            for ch in g.text_channels
        ]
        voice_channels = [
            {"id": str(ch.id), "name": ch.name, "type": "voice"}
            for ch in g.voice_channels
        ]
        roles = [
            {
                "id": str(r.id),
                "name": r.name,
                "color": f"#{r.color.value:06x}" if r.color.value else "#99AAB5",
                "position": r.position,
                "managed": r.managed,
            }
            for r in sorted(g.roles, key=lambda x: x.position, reverse=True)
            if not r.is_default()
        ]

        members = []
        try:
            for m in list(g.members)[:300]:
                members.append({
                    "id": str(m.id),
                    "name": m.name,
                    "displayName": getattr(m, "display_name", m.name),
                    "avatar": str(m.display_avatar.url) if hasattr(m, "display_avatar") else None,
                    "bot": m.bot,
                })
        except Exception:
            pass

        guilds_data.append({
            "id": str(g.id),
            "name": g.name,
            "icon": str(g.icon.url) if g.icon else None,
            "member_count": g.member_count or len(members),
            "owner_id": str(g.owner_id),
            "channels": text_channels + voice_channels,
            "roles": roles,
            "members": members,
        })

    return web.json_response({"online": True, "guilds": guilds_data})


async def api_guild_config(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    guild_id_str = request.match_info.get("guild_id")
    try:
        guild_id = int(guild_id_str)
    except (ValueError, TypeError):
        return web.json_response({"error": "Invalid guild_id"}, status=400)

    if request.method == "GET":
        cfg = await get_guild_config(guild_id)
        safe_cfg = {k: (str(v) if isinstance(v, int) and ("ch" in k or "role" in k or k == "guild_id") else v) for k, v in cfg.items()}
        return web.json_response(safe_cfg)

    elif request.method == "POST":
        try:
            body = await request.json()
            parsed = {}
            for k, v in body.items():
                if v == "" or v is None:
                    parsed[k] = None
                elif k in ("bot_role_id", "ticket_role_id", "welcome_ch", "leave_ch", "member_log_ch", "log_ch", "mod_log_ch", "server_log_ch", "activity_log_ch", "cmd_log_ch"):
                    try:
                        parsed[k] = int(v)
                    except (ValueError, TypeError):
                        parsed[k] = None
                else:
                    parsed[k] = v

            await save_guild_config(guild_id, **parsed)
            await record_audit(
                user, "SAVE_GUILD_CONFIG",
                f"Saved server config for Guild {guild_id}",
                guild_id=guild_id,
                request=request
            )
            return web.json_response({"success": True})
        except Exception as e:
            log.error(f"Failed to save guild config: {e}")
            return web.json_response({"success": False, "error": str(e)}, status=500)


async def api_guild_setup(request: web.Request) -> web.Response:
    """Equivalent to /setupbot — creates audit log channels."""
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    if not bot or not bot.is_ready():
        return web.json_response({"success": False, "error": "Bot is offline"}, status=400)

    try:
        guild_id = int(request.match_info.get("guild_id"))
    except (ValueError, TypeError):
        return web.json_response({"success": False, "error": "Invalid guild ID"}, status=400)

    guild = bot.get_guild(guild_id)
    if not guild:
        return web.json_response({"success": False, "error": "Guild not found"}, status=404)

    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me:           discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        category = await guild.create_category("📁 NEXUS LOGS", overwrites=overwrites)
        mod_log_ch      = await guild.create_text_channel("🔒・mod-logs",      category=category)
        server_log_ch   = await guild.create_text_channel("🔒・server-logs",   category=category)
        activity_log_ch = await guild.create_text_channel("🔒・activity-logs", category=category)

        await save_guild_config(
            guild.id,
            mod_log_ch=mod_log_ch.id,
            server_log_ch=server_log_ch.id,
            activity_log_ch=activity_log_ch.id,
        )

        await record_audit(
            user, "SETUP_AUDIT_LOGS",
            f"Auto-setup audit channels in {guild.name} ({guild.id})",
            guild_id=guild.id,
            request=request
        )
        return web.json_response({
            "success": True,
            "mod_log_ch": str(mod_log_ch.id),
            "server_log_ch": str(server_log_ch.id),
            "activity_log_ch": str(activity_log_ch.id),
        })
    except Exception as e:
        log.error(f"Setup bot failed: {e}")
        return web.json_response({"success": False, "error": str(e)}, status=500)



# ── Moderation API Handlers ───────────────────────────────────────────────────

async def log_mod_action(guild: discord.Guild, embed: discord.Embed):
    cfg = await get_guild_config(guild.id)
    ch_id = cfg.get("mod_log_ch") or cfg.get("log_ch")
    if not ch_id:
        return
    ch = guild.get_channel(ch_id)
    if ch:
        try:
            await ch.send(embed=embed)
        except Exception:
            pass


async def api_moderation_kick(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    if not bot or not bot.is_ready():
        return web.json_response({"success": False, "error": "Bot is offline"}, status=400)

    try:
        data = await request.json()
        guild_id = int(data.get("guild_id"))
        user_id = int(data.get("user_id"))
        reason = data.get("reason", "Kicked via Web Dashboard").strip()
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"success": False, "error": "Invalid guild or user ID"}, status=400)

    guild = bot.get_guild(guild_id)
    if not guild:
        return web.json_response({"success": False, "error": "Guild not found"}, status=404)

    member = guild.get_member(user_id) or await guild.fetch_member(user_id)
    if not member:
        return web.json_response({"success": False, "error": "Member not found in server"}, status=404)

    try:
        try:
            await member.send(f"⚠️ You have been **kicked** from **{guild.name}**.\n**Reason:** {reason}")
        except Exception:
            pass

        await member.kick(reason=f"{reason} (by {user['username']})")

        embed = discord.Embed(title="👢 Member Kicked", color=0xE67E22, timestamp=discord.utils.utcnow())
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=True)
        embed.add_field(name="Moderator", value=f"{user['username']} (<@{user['user_id']}>) [Web]", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await log_mod_action(guild, embed)

        await record_audit(
            user, "MEMBER_KICK",
            f"Kicked {member.name} ({member.id}) from {guild.name}. Reason: {reason}",
            guild_id=guild_id, target_id=str(user_id), request=request
        )
        return web.json_response({"success": True})
    except Exception as e:
        log.error(f"Kick error: {e}")
        return web.json_response({"success": False, "error": str(e)}, status=500)


async def api_moderation_ban(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    if not bot or not bot.is_ready():
        return web.json_response({"success": False, "error": "Bot is offline"}, status=400)

    try:
        data = await request.json()
        guild_id = int(data.get("guild_id"))
        user_id = int(data.get("user_id"))
        reason = data.get("reason", "Banned via Web Dashboard").strip()
        delete_days = int(data.get("delete_days", 0))
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"success": False, "error": "Invalid guild or user ID"}, status=400)

    guild = bot.get_guild(guild_id)
    if not guild:
        return web.json_response({"success": False, "error": "Guild not found"}, status=404)

    try:
        target_user = bot.get_user(user_id) or await bot.fetch_user(user_id)
        if not target_user:
            return web.json_response({"success": False, "error": "User not found"}, status=404)

        try:
            await target_user.send(f"🔨 You have been **permanently banned** from **{guild.name}**.\n**Reason:** {reason}")
        except Exception:
            pass

        await guild.ban(target_user, reason=f"{reason} (by {user['username']})", delete_message_seconds=min(7, max(0, delete_days)) * 86400)

        embed = discord.Embed(title="🔨 Member Banned", color=0xED4245, timestamp=discord.utils.utcnow())
        embed.add_field(name="User", value=f"{target_user.mention} (`{target_user.id}`)", inline=True)
        embed.add_field(name="Moderator", value=f"{user['username']} (<@{user['user_id']}>) [Web]", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await log_mod_action(guild, embed)

        await record_audit(
            user, "MEMBER_BAN",
            f"Banned {target_user.name} ({target_user.id}) from {guild.name}. Reason: {reason}",
            guild_id=guild_id, target_id=str(user_id), request=request
        )
        return web.json_response({"success": True})
    except Exception as e:
        log.error(f"Ban error: {e}")
        return web.json_response({"success": False, "error": str(e)}, status=500)


async def api_moderation_unban(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    if not bot or not bot.is_ready():
        return web.json_response({"success": False, "error": "Bot is offline"}, status=400)

    try:
        data = await request.json()
        guild_id = int(data.get("guild_id"))
        user_id = int(data.get("user_id"))
        reason = data.get("reason", "Unbanned via Web Dashboard").strip()
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"success": False, "error": "Invalid guild or user ID"}, status=400)

    guild = bot.get_guild(guild_id)
    if not guild:
        return web.json_response({"success": False, "error": "Guild not found"}, status=404)

    try:
        target_user = await bot.fetch_user(user_id)
        await guild.unban(target_user, reason=f"{reason} (by {user['username']})")

        embed = discord.Embed(title="🔓 Member Unbanned", color=0x57F287, timestamp=discord.utils.utcnow())
        embed.add_field(name="User", value=f"{target_user.mention} (`{target_user.id}`)", inline=True)
        embed.add_field(name="Moderator", value=f"{user['username']} (<@{user['user_id']}>) [Web]", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await log_mod_action(guild, embed)

        await record_audit(
            user, "MEMBER_UNBAN",
            f"Unbanned user {target_user.name} ({target_user.id}) in {guild.name}",
            guild_id=guild_id, target_id=str(user_id), request=request
        )
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)


async def api_moderation_mute(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    if not bot or not bot.is_ready():
        return web.json_response({"success": False, "error": "Bot is offline"}, status=400)

    try:
        data = await request.json()
        guild_id = int(data.get("guild_id"))
        user_id = int(data.get("user_id"))
        duration_secs = int(data.get("duration", 600))
        reason = data.get("reason", "Timed out via Web Dashboard").strip()
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"success": False, "error": "Invalid parameters"}, status=400)

    guild = bot.get_guild(guild_id)
    if not guild:
        return web.json_response({"success": False, "error": "Guild not found"}, status=404)

    member = guild.get_member(user_id) or await guild.fetch_member(user_id)
    if not member:
        return web.json_response({"success": False, "error": "Member not found in server"}, status=404)

    try:
        until = discord.utils.utcnow() + datetime.timedelta(seconds=duration_secs)
        await member.timeout(until, reason=f"{reason} (by {user['username']})")

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO mutes (guild_id, user_id, ends_at) VALUES (?, ?, ?)",
                (guild_id, user_id, time.time() + duration_secs)
            )
            await db.commit()

        embed = discord.Embed(title="⏳ Member Timed Out", color=0xFEE75C, timestamp=discord.utils.utcnow())
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=True)
        embed.add_field(name="Moderator", value=f"{user['username']} (<@{user['user_id']}>) [Web]", inline=True)
        embed.add_field(name="Duration", value=f"{duration_secs // 60} minutes", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await log_mod_action(guild, embed)

        await record_audit(
            user, "MEMBER_TIMEOUT",
            f"Timed out {member.name} ({member.id}) for {duration_secs}s in {guild.name}. Reason: {reason}",
            guild_id=guild_id, target_id=str(user_id), request=request
        )
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)


async def api_moderation_unmute(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    if not bot or not bot.is_ready():
        return web.json_response({"success": False, "error": "Bot is offline"}, status=400)

    try:
        data = await request.json()
        guild_id = int(data.get("guild_id"))
        user_id = int(data.get("user_id"))
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"success": False, "error": "Invalid parameters"}, status=400)

    guild = bot.get_guild(guild_id)
    if not guild:
        return web.json_response({"success": False, "error": "Guild not found"}, status=404)

    member = guild.get_member(user_id) or await guild.fetch_member(user_id)
    if not member:
        return web.json_response({"success": False, "error": "Member not found"}, status=404)

    try:
        await member.remove_timeout(reason=f"Timeout removed via Web Dashboard (by {user['username']})")
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM mutes WHERE guild_id=? AND user_id=?", (guild_id, user_id))
            await db.commit()

        embed = discord.Embed(title="🔊 Timeout Removed", color=0x57F287, timestamp=discord.utils.utcnow())
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=True)
        embed.add_field(name="Moderator", value=f"{user['username']} (<@{user['user_id']}>) [Web]", inline=True)
        await log_mod_action(guild, embed)

        await record_audit(
            user, "REMOVE_TIMEOUT",
            f"Removed timeout for {member.name} ({member.id}) in {guild.name}",
            guild_id=guild_id, target_id=str(user_id), request=request
        )
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)


async def api_moderation_warn(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    try:
        data = await request.json()
        guild_id = int(data.get("guild_id"))
        user_id = int(data.get("user_id"))
        reason = data.get("reason", "Warning logged via Web Dashboard").strip()
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"success": False, "error": "Invalid parameters"}, status=400)

    mod_id = user["user_id"]
    await init_dashboard_db()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO warns (guild_id, user_id, mod_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, mod_id, reason, time.time())
        )
        await db.commit()

    bot = get_bot()
    if bot and bot.is_ready():
        guild = bot.get_guild(guild_id)
        if guild:
            member = guild.get_member(user_id)
            if member:
                try:
                    await member.send(f"⚠️ You received a formal **warning** in **{guild.name}**.\n**Reason:** {reason}")
                except Exception:
                    pass
            embed = discord.Embed(title="⚠️ Warning Issued", color=0xFEE75C, timestamp=discord.utils.utcnow())
            embed.add_field(name="User", value=f"<@{user_id}> (`{user_id}`)", inline=True)
            embed.add_field(name="Moderator", value=f"{user['username']} (<@{mod_id}>) [Web]", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            await log_mod_action(guild, embed)

    await record_audit(
        user, "MEMBER_WARN",
        f"Issued warning to user {user_id}. Reason: {reason}",
        guild_id=guild_id, target_id=str(user_id), request=request
    )
    return web.json_response({"success": True})


async def api_moderation_clearwarns(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    try:
        data = await request.json()
        guild_id = int(data.get("guild_id"))
        user_id = int(data.get("user_id"))
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"success": False, "error": "Invalid parameters"}, status=400)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM warns WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        await db.commit()

    await record_audit(
        user, "CLEAR_WARNS",
        f"Cleared all active warnings for User ID {user_id}",
        guild_id=guild_id, target_id=str(user_id), request=request
    )
    return web.json_response({"success": True})


async def api_moderation_getwarns(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    try:
        guild_id = int(request.match_info.get("guild_id"))
    except (ValueError, TypeError):
        return web.json_response({"error": "Invalid guild_id"}, status=400)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, user_id, mod_id, reason, timestamp FROM warns WHERE guild_id=? ORDER BY id DESC LIMIT 100",
            (guild_id,)
        ) as cur:
            rows = await cur.fetchall()

    warns_list = []
    for r in rows:
        warns_list.append({
            "id": r["id"],
            "user_id": str(r["user_id"]),
            "mod_id": str(r["mod_id"]),
            "reason": r["reason"],
            "date": datetime.datetime.fromtimestamp(r["timestamp"]).strftime("%Y-%m-%d %H:%M"),
        })
    return web.json_response(warns_list)


async def api_moderation_purge(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    if not bot or not bot.is_ready():
        return web.json_response({"success": False, "error": "Bot is offline"}, status=400)

    try:
        data = await request.json()
        channel_id = int(data.get("channel_id"))
        amount = min(100, max(1, int(data.get("amount", 10))))
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"success": False, "error": "Invalid parameters"}, status=400)

    channel = bot.get_channel(channel_id)
    if not channel or not isinstance(channel, discord.TextChannel):
        return web.json_response({"success": False, "error": "Text channel not found"}, status=404)

    try:
        deleted = await channel.purge(limit=amount)
        await record_audit(
            user, "CHANNEL_PURGE",
            f"Purged {len(deleted)} messages in #{channel.name}",
            guild_id=channel.guild.id, target_id=str(channel_id), request=request
        )
        return web.json_response({"success": True, "count": len(deleted)})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)


async def api_moderation_lock(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    if not bot or not bot.is_ready():
        return web.json_response({"success": False, "error": "Bot is offline"}, status=400)

    try:
        data = await request.json()
        channel_id = int(data.get("channel_id"))
        lock = bool(data.get("lock", True))
        reason = data.get("reason", "Locked via Dashboard").strip()
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"success": False, "error": "Invalid parameters"}, status=400)

    channel = bot.get_channel(channel_id)
    if not channel or not isinstance(channel, discord.TextChannel):
        return web.json_response({"success": False, "error": "Text channel not found"}, status=404)

    try:
        await channel.set_permissions(
            channel.guild.default_role,
            send_messages=(not lock),
            reason=f"{reason} (by {user['username']})"
        )
        status_text = "locked 🔒" if lock else "unlocked 🔓"
        embed = discord.Embed(
            title=f"Channel {status_text.title()}",
            description=f"This channel has been {status_text} by {user['username']}.\n**Reason:** {reason}",
            color=0xED4245 if lock else 0x57F287
        )
        await channel.send(embed=embed)

        await record_audit(
            user, "CHANNEL_LOCK" if lock else "CHANNEL_UNLOCK",
            f"{'Locked' if lock else 'Unlocked'} channel #{channel.name} in {channel.guild.name}. Reason: {reason}",
            guild_id=channel.guild.id, target_id=str(channel_id), request=request
        )
        return web.json_response({"success": True, "locked": lock})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)


async def api_moderation_slowmode(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    if not bot or not bot.is_ready():
        return web.json_response({"success": False, "error": "Bot is offline"}, status=400)

    try:
        data = await request.json()
        channel_id = int(data.get("channel_id"))
        seconds = max(0, min(21600, int(data.get("seconds", 0))))
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"success": False, "error": "Invalid parameters"}, status=400)

    channel = bot.get_channel(channel_id)
    if not channel or not isinstance(channel, discord.TextChannel):
        return web.json_response({"success": False, "error": "Text channel not found"}, status=404)

    try:
        await channel.edit(slowmode_delay=seconds, reason=f"Slowmode set by {user['username']} via Web")
        await record_audit(
            user, "SET_SLOWMODE",
            f"Set slowmode to {seconds}s in #{channel.name}",
            guild_id=channel.guild.id, target_id=str(channel_id), request=request
        )
        return web.json_response({"success": True, "slowmode": seconds})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)



# ── Announcements & DM Handlers ───────────────────────────────────────────────

# ── Announcements & DM Handlers ───────────────────────────────────────────────

async def api_announce(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    if not bot or not bot.is_ready():
        return web.json_response({"success": False, "error": "Bot is offline"}, status=400)

    try:
        data = await request.json()
        channel_id = int(data.get("channel_id"))
        msg_type = data.get("type", "embed")
        ping = data.get("ping", "none").lower()
        title = data.get("title", "").strip()
        content = data.get("content", "").strip()
        color_val = data.get("color", "blurple")
        banner_url = data.get("banner_url", "").strip()
        thumbnail_url = data.get("thumbnail_url", "").strip()
        button_str = data.get("button", "").strip()
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"success": False, "error": "Invalid announcement parameters"}, status=400)

    if not title and not content:
        return web.json_response({"success": False, "error": "Announcement requires at least a title or text content."}, status=400)

    channel = bot.get_channel(channel_id)
    if not channel or not isinstance(channel, discord.TextChannel):
        return web.json_response({"success": False, "error": "Channel not found"}, status=404)

    mention_prefix = ""
    if ping == "everyone":
        mention_prefix = "@everyone\n"
    elif ping == "here":
        mention_prefix = "@here\n"

    view = build_button_view(button_str)

    try:
        if msg_type == "plain":
            body = f"{mention_prefix}{content}"
            if banner_url:
                body += f"\n{banner_url}"
            await channel.send(body, view=view if view else discord.utils.MISSING)
        else:
            embed_color = parse_color(color_val)
            embed = discord.Embed(
                title=title if title else None,
                description=content if content else None,
                color=embed_color,
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(
                text=f"{channel.guild.name} • Posted by {user['username']}",
                icon_url=channel.guild.icon.url if channel.guild.icon else None
            )
            if banner_url:
                embed.set_image(url=banner_url)
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)

            await channel.send(
                content=mention_prefix if mention_prefix else None,
                embed=embed,
                view=view if view else discord.utils.MISSING
            )

        await record_audit(
            user, "DISPATCH_ANNOUNCEMENT",
            f"Published announcement '{title or content[:30]}' to #{channel.name}",
            guild_id=channel.guild.id, target_id=str(channel_id), request=request
        )
        return web.json_response({"success": True})
    except Exception as e:
        log.error(f"Failed to send announcement: {e}")
        return web.json_response({"success": False, "error": str(e)}, status=500)


async def api_dm(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    if not bot or not bot.is_ready():
        return web.json_response({"success": False, "error": "Bot is offline"}, status=400)

    try:
        data = await request.json()
        target_type = data.get("target_type", "user")
        guild_id = int(data.get("guild_id"))
        target_id = int(data.get("target_id"))
        title = data.get("title", "").strip()
        content = data.get("content", "").strip()
        color_val = data.get("color", "blurple")
        button_str = data.get("button", "").strip()
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"success": False, "error": "Invalid DM parameters"}, status=400)

    if not content:
        return web.json_response({"success": False, "error": "Message content cannot be empty"}, status=400)

    guild = bot.get_guild(guild_id)
    if not guild:
        return web.json_response({"success": False, "error": "Guild not found"}, status=404)

    embed_color = parse_color(color_val)
    view = build_button_view(button_str)

    embed = discord.Embed(
        title=title if title else f"📬 Official Notice from {guild.name}",
        description=content,
        color=embed_color,
        timestamp=discord.utils.utcnow(),
    )
    if guild.icon:
        embed.set_author(name=guild.name, icon_url=guild.icon.url)
    embed.set_footer(text=f"Nexus Direct Dispatch • Dispatched by {user['username']}")

    sent_count = 0
    failed_count = 0

    if target_type == "user":
        target_usr = bot.get_user(target_id) or await bot.fetch_user(target_id)
        if not target_usr:
            return web.json_response({"success": False, "error": "Target user not found"}, status=404)
        try:
            await target_usr.send(embed=embed, view=view if view else discord.utils.MISSING)
            sent_count = 1
        except Exception as e:
            return web.json_response({"success": False, "error": f"Failed to deliver DM: {e}"}, status=400)
    else:
        role = guild.get_role(target_id)
        if not role:
            return web.json_response({"success": False, "error": "Target role not found"}, status=404)

        members_with_role = [m for m in guild.members if role in m.roles and not m.bot]
        for m in members_with_role:
            try:
                await m.send(embed=embed, view=view if view else discord.utils.MISSING)
                sent_count += 1
                await asyncio.sleep(0.3)
            except Exception:
                failed_count += 1

    await record_audit(
        user, "DISPATCH_DM",
        f"Dispatched direct messages ({target_type}={target_id}): Sent: {sent_count}, Failed: {failed_count}",
        guild_id=guild_id, target_id=str(target_id), request=request
    )
    return web.json_response({"success": True, "sent": sent_count, "failed": failed_count})


# ── Giveaways API Handlers ───────────────────────────────────────────────────

def parse_duration_str(s: str) -> int:
    s = s.strip().lower()
    total = 0
    buf = ""
    for c in s:
        if c.isdigit():
            buf += c
        elif c in "dhms" and buf:
            n = int(buf)
            total += n * {"d": 86400, "h": 3600, "m": 60, "s": 1}[c]
            buf = ""
    return total or 3600


async def api_giveaways_list(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    await init_dashboard_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM giveaways ORDER BY id DESC LIMIT 50") as cur:
            rows = await cur.fetchall()

    res = []
    now = time.time()
    for r in rows:
        ends_at = r["ends_at"]
        rem = ends_at - now
        res.append({
            "id": r["id"],
            "guild_id": str(r["guild_id"]),
            "channel_id": str(r["channel_id"]),
            "message_id": str(r["message_id"]),
            "host_id": str(r["host_id"]),
            "prize": r["prize"],
            "winners": r["winners"],
            "ends_at": ends_at,
            "ended": bool(r["ended"]),
            "remaining_sec": max(0, int(rem)),
            "required_roles": r["required_role_ids"] or (str(r["required_role_id"]) if r["required_role_id"] else None),
        })
    return web.json_response(res)


async def api_giveaways_create(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    if not bot or not bot.is_ready():
        return web.json_response({"success": False, "error": "Bot is offline"}, status=400)

    try:
        data = await request.json()
        guild_id = int(data.get("guild_id"))
        channel_id = int(data.get("channel_id"))
        prize = data.get("prize", "Discord Nitro").strip()
        winners = max(1, int(data.get("winners", 1)))
        duration_str = data.get("duration", "1h")
        duration_sec = parse_duration_str(duration_str)
        required_roles_str = data.get("required_roles", "").strip()
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"success": False, "error": "Invalid giveaway parameters"}, status=400)

    guild = bot.get_guild(guild_id)
    if not guild:
        return web.json_response({"success": False, "error": "Guild not found"}, status=404)

    channel = guild.get_channel(channel_id)
    if not channel or not isinstance(channel, discord.TextChannel):
        return web.json_response({"success": False, "error": "Text channel not found"}, status=404)

    ends_at = time.time() + duration_sec

    req_ids = []
    if required_roles_str:
        for p in required_roles_str.split(","):
            p = p.strip()
            if p.isdigit():
                req_ids.append(int(p))

    embed = discord.Embed(
        title=f"🎉 GIVEAWAY — {prize}",
        color=0x57F287,
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="🏆 Winners", value=str(winners), inline=True)
    embed.add_field(name="👤 Hosted by", value=f"{user['username']} (<@{user['user_id']}>)", inline=True)
    if req_ids:
        embed.add_field(name="🔒 Required Roles", value=", ".join(f"<@&{rid}>" for rid in req_ids), inline=True)
    else:
        embed.add_field(name="👥 Eligibility", value="Everyone", inline=True)

    embed.description = f"React with 🎉 to enter!\n\n**Ends:** <t:{int(ends_at)}:R>"
    msg = await channel.send(embed=embed)
    await msg.add_reaction("🎉")

    req_str = ",".join(str(i) for i in req_ids) if req_ids else None
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO giveaways (guild_id, channel_id, message_id, host_id, prize, winners, ends_at, ended, required_role_ids)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (guild_id, channel_id, msg.id, user["user_id"], prize, winners, ends_at, req_str)
        )
        await db.commit()

    await record_audit(
        user, "GIVEAWAY_CREATE",
        f"Launched giveaway '{prize}' ({winners} winner{'s' if winners > 1 else ''}) in #{channel.name}",
        guild_id=guild_id, target_id=str(channel_id), request=request
    )
    return web.json_response({"success": True, "message_id": str(msg.id)})


async def api_giveaways_end(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    try:
        data = await request.json()
        gw_id = int(data.get("id"))
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"success": False, "error": "Invalid giveaway ID"}, status=400)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM giveaways WHERE id=?", (gw_id,)) as cur:
            row = await cur.fetchone()

    if not row:
        return web.json_response({"success": False, "error": "Giveaway not found"}, status=404)

    if bot and bot.is_ready():
        cog = bot.get_cog("Giveaway")
        if cog and hasattr(cog, "_end_giveaway"):
            await cog._end_giveaway(dict(row))
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE giveaways SET ended=1 WHERE id=?", (gw_id,))
                await db.commit()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE giveaways SET ended=1 WHERE id=?", (gw_id,))
            await db.commit()

    await record_audit(
        user, "GIVEAWAY_END",
        f"Force-ended giveaway #{gw_id} ('{row['prize']}')",
        guild_id=row["guild_id"], target_id=str(gw_id), request=request
    )
    return web.json_response({"success": True})


# ── Tickets API Handlers ─────────────────────────────────────────────────────

async def api_tickets_list(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    await init_dashboard_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tickets ORDER BY id DESC LIMIT 50") as cur:
            rows = await cur.fetchall()

    tickets_data = [
        {
            "id": r["id"],
            "guild_id": str(r["guild_id"]),
            "channel_id": str(r["channel_id"]),
            "user_id": str(r["user_id"]),
            "status": r["status"]
        }
        for r in rows
    ]
    return web.json_response(tickets_data)


async def api_tickets_close(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    try:
        data = await request.json()
        channel_id = int(data.get("channel_id"))
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"success": False, "error": "Invalid channel ID"}, status=400)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET status='closed' WHERE channel_id=?", (channel_id,))
        await db.commit()

    if bot and bot.is_ready():
        channel = bot.get_channel(channel_id)
        if channel:
            try:
                await channel.send(f"🔒 Ticket closed by {user['username']} via Web Dashboard. Channel deleting in 5 seconds...")
                await asyncio.sleep(5)
                await channel.delete(reason=f"Ticket closed by {user['username']} via Web Dashboard")
            except Exception:
                pass

    await record_audit(
        user, "TICKET_CLOSE",
        f"Closed ticket channel {channel_id}",
        target_id=str(channel_id), request=request
    )
    return web.json_response({"success": True})


async def api_tickets_setup(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    if not bot or not bot.is_ready():
        return web.json_response({"success": False, "error": "Bot is offline"}, status=400)

    try:
        data = await request.json()
        guild_id = int(data.get("guild_id"))
        channel_id = int(data.get("channel_id"))
        title = data.get("title", "📩 Open a Support Ticket").strip()
        description = data.get("description", "Click the button below to open a private ticket with staff.").strip()
        btn_label = data.get("button_label", "Open Ticket").strip()
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"success": False, "error": "Invalid ticket setup parameters"}, status=400)

    channel = bot.get_channel(channel_id)
    if not channel or not isinstance(channel, discord.TextChannel):
        return web.json_response({"success": False, "error": "Channel not found"}, status=404)

    from cogs.tickets import TicketLaunchView

    embed = discord.Embed(
        title=title,
        description=description,
        color=0x5865F2,
    )
    embed.set_footer(text="Nexus Support Desk")
    view = TicketLaunchView()
    if btn_label and len(view.children) > 0:
        view.children[0].label = btn_label

    await channel.send(embed=embed, view=view)

    await record_audit(
        user, "TICKET_SETUP",
        f"Deployed support intake panel '{title}' in #{channel.name}",
        guild_id=guild_id, target_id=str(channel_id), request=request
    )
    return web.json_response({"success": True})


# ── Polls API Handlers ───────────────────────────────────────────────────────

async def api_polls_create(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    bot = get_bot()
    if not bot or not bot.is_ready():
        return web.json_response({"success": False, "error": "Bot is offline"}, status=400)

    try:
        data = await request.json()
        channel_id = int(data.get("channel_id"))
        question = data.get("question", "").strip()
        options_raw = data.get("options", [])
        duration_min = int(data.get("duration", 60))
    except (ValueError, TypeError, AttributeError):
        return web.json_response({"success": False, "error": "Invalid poll parameters"}, status=400)

    if not question:
        return web.json_response({"success": False, "error": "Question is required"}, status=400)

    options = [o.strip() for o in options_raw if o.strip()]
    if len(options) < 2 or len(options) > 10:
        return web.json_response({"success": False, "error": "Provide between 2 and 10 options"}, status=400)

    channel = bot.get_channel(channel_id)
    if not channel or not isinstance(channel, discord.TextChannel):
        return web.json_response({"success": False, "error": "Channel not found"}, status=404)

    from cogs.polls import InteractivePollView, build_poll_embed

    view = InteractivePollView(question, options, host_id=user["user_id"], duration_min=duration_min)
    embed = view.build_embed()

    msg = await channel.send(embed=embed, view=view)

    await record_audit(
        user, "POLL_CREATE",
        f"Deployed interactive poll '{question}' with {len(options)} options in #{channel.name}",
        guild_id=channel.guild.id, target_id=str(channel_id), request=request
    )
    return web.json_response({"success": True, "message_id": str(msg.id)})


# ── Non-Prefix Users API Handlers ─────────────────────────────────────────────

async def api_non_prefix(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err

    await init_dashboard_db()
    if request.method == "GET":
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM non_prefix_users ORDER BY added_at DESC") as cur:
                rows = await cur.fetchall()

        bot = get_bot()
        result = []
        for r in rows:
            u_id = r["user_id"]
            user_obj = bot.get_user(u_id) if bot else None
            result.append({
                "user_id": str(u_id),
                "name": str(user_obj) if user_obj else f"User {u_id}",
                "added_by": str(r["added_by"]),
                "added_at": datetime.datetime.fromtimestamp(r["added_at"]).strftime("%Y-%m-%d %H:%M"),
            })
        return web.json_response(result)

    elif request.method == "POST":
        try:
            data = await request.json()
            action = data.get("action", "add")
            user_id = int(data.get("user_id"))
        except (ValueError, TypeError, AttributeError):
            return web.json_response({"success": False, "error": "Invalid user ID"}, status=400)

        bot = get_bot()
        async with aiosqlite.connect(DB_PATH) as db:
            if action == "add":
                await db.execute(
                    "INSERT OR REPLACE INTO non_prefix_users (user_id, added_by, added_at) VALUES (?, ?, ?)",
                    (user_id, user["user_id"], time.time())
                )
                if bot and hasattr(bot, "non_prefix_users"):
                    bot.non_prefix_users.add(user_id)
            elif action == "remove":
                await db.execute("DELETE FROM non_prefix_users WHERE user_id=?", (user_id,))
                if bot and hasattr(bot, "non_prefix_users"):
                    bot.non_prefix_users.discard(user_id)
            await db.commit()

        await record_audit(
            user, "NON_PREFIX_MODIFY",
            f"{action.capitalize()} non-prefix permissions for User ID {user_id}",
            target_id=str(user_id), request=request
        )
        return web.json_response({"success": True})


# ── Logs & WebSocket ──────────────────────────────────────────────────────────

async def api_logs(request: web.Request) -> web.Response:
    user, err = await require_auth(request)
    if err:
        return err
    return web.json_response(log_handler.records)


async def ws_handler(request: web.Request) -> web.WebSocketResponse:
    user = await get_session_user(request)
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    log_handler.ws_clients.add(ws)
    caller = f"{user['username']} ({user['user_id']})" if user else "Visitor"
    log.info(f"WebSocket client connected: {caller} from {get_client_ip(request)}")

    # Send initial history batch
    await ws.send_str(json.dumps({
        "type": "history",
        "data": log_handler.records[-100:]
    }))

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                pass
            elif msg.type == WSMsgType.ERROR:
                log.warning(f"WebSocket error: {ws.exception()}")
    finally:
        log_handler.ws_clients.discard(ws)
        log.info(f"WebSocket client disconnected: {caller}")

    return ws


# ── Static File / Web App Setup ───────────────────────────────────────────────

def create_app() -> web.Application:
    app = web.Application()
    web_dir = Path(__file__).parent / "web"

    # Authentication routes
    app.router.add_post("/api/auth/login", api_auth_login)
    app.router.add_get("/api/auth/me", api_auth_me)
    app.router.add_post("/api/auth/logout", api_auth_logout)

    # Admin Panel routes (restricted to owner & manually added admins)
    app.router.add_get("/api/admin/users", api_admin_users)
    app.router.add_post("/api/admin/users/add", api_admin_users_add)
    app.router.add_post("/api/admin/users/toggle", api_admin_users_toggle)
    app.router.add_post("/api/admin/users/delete", api_admin_users_delete)
    app.router.add_post("/api/admin/users/reset-passcode", api_admin_users_reset_passcode)
    app.router.add_get("/api/admin/sessions", api_admin_sessions)
    app.router.add_post("/api/admin/sessions/terminate", api_admin_sessions_terminate)
    app.router.add_get("/api/admin/audit_logs", api_admin_audit_logs)

    # Bot Control & Telemetry API routes
    app.router.add_get("/api/status", api_status)
    app.router.add_post("/api/bot/presence", api_set_presence)
    app.router.add_get("/api/guilds", api_guilds)
    app.router.add_get("/api/guild/{guild_id}/config", api_guild_config)
    app.router.add_post("/api/guild/{guild_id}/config", api_guild_config)
    app.router.add_post("/api/guild/{guild_id}/setup", api_guild_setup)

    # Moderation routes
    app.router.add_post("/api/moderation/kick", api_moderation_kick)
    app.router.add_post("/api/moderation/ban", api_moderation_ban)
    app.router.add_post("/api/moderation/unban", api_moderation_unban)
    app.router.add_post("/api/moderation/mute", api_moderation_mute)
    app.router.add_post("/api/moderation/unmute", api_moderation_unmute)
    app.router.add_post("/api/moderation/warn", api_moderation_warn)
    app.router.add_post("/api/moderation/clearwarns", api_moderation_clearwarns)
    app.router.add_get("/api/moderation/{guild_id}/warns", api_moderation_getwarns)
    app.router.add_post("/api/moderation/purge", api_moderation_purge)
    app.router.add_post("/api/moderation/lock", api_moderation_lock)
    app.router.add_post("/api/moderation/slowmode", api_moderation_slowmode)

    # Announcements & DM
    app.router.add_post("/api/announce", api_announce)
    app.router.add_post("/api/dm", api_dm)

    # Giveaways
    app.router.add_get("/api/giveaways", api_giveaways_list)
    app.router.add_post("/api/giveaways/create", api_giveaways_create)
    app.router.add_post("/api/giveaways/end", api_giveaways_end)

    # Tickets
    app.router.add_get("/api/tickets", api_tickets_list)
    app.router.add_post("/api/tickets/close", api_tickets_close)
    app.router.add_post("/api/tickets/setup", api_tickets_setup)

    # Polls
    app.router.add_post("/api/polls/create", api_polls_create)

    # Non-prefix
    app.router.add_get("/api/non_prefix", api_non_prefix)
    app.router.add_post("/api/non_prefix", api_non_prefix)

    # Logs & WebSocket
    app.router.add_get("/api/logs", api_logs)
    app.router.add_get("/ws", ws_handler)

    # Health check compatibility for Render/Cloud ports
    async def health_check(req):
        return web.Response(text="Nexus Discord Bot is running! ⚡\nStatus: OK", content_type="text/plain")
    app.router.add_get("/health", health_check)

    # Serve index.html directly on root
    async def index(req):
        index_file = web_dir / "index.html"
        if index_file.exists():
            return web.FileResponse(index_file)
        return web.Response(text="Nexus Control Webpage (web/index.html missing)", content_type="text/html")

    app.router.add_get("/", index)

    # Serve commands.html on /commands
    async def commands_view(req):
        cmd_file = web_dir / "commands.html"
        if cmd_file.exists():
            return web.FileResponse(cmd_file)
        return web.Response(text="Nexus Command Directory (web/commands.html missing)", content_type="text/html")

    app.router.add_get("/commands", commands_view)

    # Static assets
    if web_dir.exists():
        app.router.add_static("/static", web_dir, show_index=True)

    # Initialize DB on app startup
    async def on_startup(application):
        await init_dashboard_db()
    app.on_startup.append(on_startup)

    return app



def free_port_if_in_use(port: int):
    """If port is occupied by another local process, free it so the bot dashboard can bind cleanly."""
    try:
        import subprocess
        if sys.platform == "win32":
            out = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True, stderr=subprocess.DEVNULL).decode()
            for line in out.strip().split("\n"):
                parts = line.strip().split()
                if len(parts) >= 5 and "LISTENING" in line:
                    pid = int(parts[-1])
                    if pid != os.getpid():
                        subprocess.run(f"taskkill /PID {pid} /F", shell=True, capture_output=True)
                        time.sleep(0.4)
    except Exception:
        pass


async def start_dashboard(bot: Any, port: int = 5000) -> web.AppRunner:
    set_bot(bot)
    free_port_if_in_use(port)
    await init_dashboard_db()

    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    try:
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        log.info(f"⚡ Nexus Control Dashboard live at http://localhost:{port}")
    except OSError as e:
        log.warning(f"Port {port} in use, clearing conflict and retrying: {e}")
        free_port_if_in_use(port)
        await asyncio.sleep(0.5)
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        log.info(f"⚡ Nexus Control Dashboard live at http://localhost:{port}")

    return runner


def start_dashboard_thread(bot: Any, port: int = 5000) -> threading.Thread:
    """Runs the aiohttp web dashboard in a dedicated background thread with its own isolated event loop."""
    set_bot(bot)
    free_port_if_in_use(port)

    def _thread_target():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(init_dashboard_db())

        app = create_app()
        runner = web.AppRunner(app)
        loop.run_until_complete(runner.setup())
        try:
            site = web.TCPSite(runner, "0.0.0.0", port)
            loop.run_until_complete(site.start())
            log.info(f"⚡ Nexus Control Dashboard live at http://localhost:{port}")
        except OSError as e:
            log.warning(f"Port {port} in use, clearing conflict and retrying: {e}")
            free_port_if_in_use(port)
            time.sleep(0.5)
            site = web.TCPSite(runner, "0.0.0.0", port)
            loop.run_until_complete(site.start())
            log.info(f"⚡ Nexus Control Dashboard live at http://localhost:{port}")

        loop.run_forever()

    t = threading.Thread(target=_thread_target, daemon=True, name="NexusDashboardThread")
    t.start()
    return t


if __name__ == "__main__":
    # Standalone execution
    port = int(os.getenv("PORT") or os.getenv("DASHBOARD_PORT") or 5000)
    print(f"Starting standalone Nexus Control Dashboard on port {port}...")
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=port)
