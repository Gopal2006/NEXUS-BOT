"""
Security API Routes: Antinuke, Whitelist, Emergency Lockdown, and Automod.
"""

import time
import json
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
import discord

from api.auth import verify_guild_access, get_current_user_id
from api.models import (
    AntinukeUpdate,
    LockdownRequest,
    WhitelistCreateRequest,
    AutomodUpdate,
)
from db.database import get_db
from db.repos.security import (
    get_antinuke_settings,
    update_antinuke_settings,
    get_guild_whitelist,
    add_whitelist_entry,
    remove_whitelist_entry,
    get_automod_settings,
    update_automod_settings,
)

router = APIRouter(prefix="/api/v1/guilds/{guild_id}", tags=["Security"])


async def record_audit(guild_id: int, user_id: int, action: str, details: str = ""):
    db = await get_db()
    await db.execute(
        "INSERT INTO dashboard_audit (guild_id, user_id, action, details, timestamp) VALUES (?, ?, ?, ?, ?)",
        (guild_id, user_id, action, details, time.time()),
    )
    await db.commit()


# ── Antinuke ──────────────────────────────────────────────────────────────────

@router.get("/antinuke")
async def get_antinuke(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
) -> dict[str, Any]:
    return await get_antinuke_settings(guild_id)


@router.put("/antinuke")
async def update_antinuke(
    guild_id: int,
    body: AntinukeUpdate,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    updates = body.model_dump(exclude_unset=True)
    if updates:
        await update_antinuke_settings(guild_id, **updates)
        await record_audit(guild_id, user_id, "update_antinuke", json.dumps(updates))
    return {"status": "success", "settings": await get_antinuke_settings(guild_id)}


@router.post("/lockdown")
async def trigger_lockdown(
    guild_id: int,
    body: LockdownRequest,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Locks all text channels against @everyone send_messages."""
    everyone = guild.default_role
    locked = 0
    for ch in guild.text_channels:
        try:
            overwrites = ch.overwrites_for(everyone)
            if overwrites.send_messages is not False:
                overwrites.send_messages = False
                await ch.set_permissions(everyone, overwrite=overwrites, reason=f"Dashboard Lockdown: {body.reason}")
                locked += 1
        except Exception:
            pass

    await record_audit(guild_id, user_id, "emergency_lockdown", f"Locked {locked} channels. Reason: {body.reason}")
    return {"status": "success", "channels_locked": locked}


@router.post("/unlockdown")
async def release_lockdown(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Releases lockdown on all text channels."""
    everyone = guild.default_role
    unlocked = 0
    for ch in guild.text_channels:
        try:
            overwrites = ch.overwrites_for(everyone)
            if overwrites.send_messages is False:
                overwrites.send_messages = None
                await ch.set_permissions(everyone, overwrite=overwrites, reason="Dashboard Unlockdown")
                unlocked += 1
        except Exception:
            pass

    await record_audit(guild_id, user_id, "release_lockdown", f"Unlocked {unlocked} channels")
    return {"status": "success", "channels_unlocked": unlocked}


# ── Whitelist ─────────────────────────────────────────────────────────────────

@router.get("/whitelist")
async def get_whitelist(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
) -> list[dict[str, Any]]:
    entries = await get_guild_whitelist(guild_id)
    # Enrich names
    results = []
    for e in entries:
        t_id = e["target_id"]
        t_type = e["target_type"]
        name = "Unknown"
        if t_type == "user":
            u = guild.get_member(t_id)
            name = u.name if u else str(t_id)
        elif t_type == "role":
            r = guild.get_role(t_id)
            name = r.name if r else str(t_id)

        results.append({**e, "name": name})
    return results


@router.post("/whitelist")
async def add_whitelist(
    guild_id: int,
    body: WhitelistCreateRequest,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    success = await add_whitelist_entry(
        guild_id=guild_id,
        target_id=body.target_id,
        target_type=body.target_type,
        module=body.module,
        added_by=user_id,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add whitelist entry")

    await record_audit(guild_id, user_id, "add_whitelist", f"Added {body.target_type} {body.target_id} ({body.module})")
    return {"status": "success"}


@router.delete("/whitelist/{target_id}")
async def remove_whitelist(
    guild_id: int,
    target_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    await remove_whitelist_entry(guild_id, target_id)
    await record_audit(guild_id, user_id, "remove_whitelist", f"Removed {target_id}")
    return {"status": "success"}


# ── Automod ───────────────────────────────────────────────────────────────────

@router.get("/automod")
async def get_automod(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
) -> dict[str, Any]:
    return await get_automod_settings(guild_id)


@router.put("/automod")
async def update_automod(
    guild_id: int,
    body: AutomodUpdate,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    updates = body.model_dump(exclude_unset=True)
    if updates:
        await update_automod_settings(guild_id, **updates)
        await record_audit(guild_id, user_id, "update_automod", json.dumps(updates))
    return {"status": "success", "settings": await get_automod_settings(guild_id)}
