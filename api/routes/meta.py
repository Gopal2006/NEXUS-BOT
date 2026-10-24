"""
Meta and Health Check API Routes.
Serves cloud container health probes and bot telemetry.
"""

import time
import os
try:
    import psutil
except ImportError:
    psutil = None
from fastapi import APIRouter, Depends
from core.bot import bot
from core.config import BRAND_NAME
from api.auth import verify_bot_owner

router = APIRouter()
_START_TIME = time.time()


@router.get("/")
@router.get("/health")
async def health_check():
    """Cloud host health check probe. Used by Render and container orchestrators."""
    is_ready = bot.is_ready()
    return {
        "status": "healthy" if is_ready else "starting",
        "bot": bot.user.name if bot.user else BRAND_NAME,
        "bot_id": bot.user.id if bot.user else None,
        "guilds": len(bot.guilds),
        "ping_ms": round(bot.latency * 1000, 1) if is_ready else None,
        "uptime_seconds": int(time.time() - _START_TIME),
    }


@router.get("/api/v1/stats")
async def bot_stats():
    """Returns runtime statistics and performance telemetry for the dashboard."""
    is_ready = bot.is_ready()
    total_users = sum(g.member_count or 0 for g in bot.guilds) if is_ready else 0

    # System memory
    ram_mb = 0.0
    if psutil is not None:
        try:
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            ram_mb = round(mem_info.rss / (1024 * 1024), 1)
        except Exception:
            pass

    return {
        "status": "online" if is_ready else "initializing",
        "brand_name": BRAND_NAME,
        "guilds_count": len(bot.guilds),
        "users_count": total_users,
        "ping_ms": round(bot.latency * 1000, 1) if is_ready else 0,
        "uptime_seconds": int(time.time() - _START_TIME),
        "ram_usage_mb": ram_mb,
        "total_cogs": len(bot.cogs),
        "loaded_cogs": list(bot.cogs.keys()),
    }


# ── Global Owner Administration Routes ───────────────────────────────────────

@router.get("/api/v1/admin/guilds")
async def admin_guilds(admin_id: int = Depends(verify_bot_owner)):
    """Lists all guilds where the bot is currently a member."""
    return [
        {
            "id": str(g.id),
            "name": g.name,
            "icon": g.icon.url if g.icon else None,
            "member_count": g.member_count or 0,
            "owner_id": str(g.owner_id),
        }
        for g in bot.guilds
    ]


@router.get("/api/v1/admin/nonprefix")
async def list_non_prefix(admin_id: int = Depends(verify_bot_owner)):
    """Fetches non-prefix users with database metadata."""
    from db.database import get_db
    db = await get_db()
    async with db.execute("SELECT * FROM non_prefix_users ORDER BY added_at DESC") as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


@router.post("/api/v1/admin/nonprefix")
async def add_non_prefix(
    body: dict,
    admin_id: int = Depends(verify_bot_owner),
):
    """Adds a user to non-prefix allowlist."""
    from db.database import add_non_prefix_user
    user_id = int(body.get("user_id"))
    await add_non_prefix_user(user_id, admin_id)
    return {"status": "success", "user_id": user_id}


@router.delete("/api/v1/admin/nonprefix/{user_id}")
async def remove_non_prefix(
    user_id: int,
    admin_id: int = Depends(verify_bot_owner),
):
    """Removes a user from non-prefix allowlist."""
    from db.database import remove_non_prefix_user
    await remove_non_prefix_user(user_id)
    return {"status": "success", "user_id": user_id}

