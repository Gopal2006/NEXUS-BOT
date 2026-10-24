"""
General Guild Configuration API Routes.
Manages welcome/leave channels, audit logs, and bot-role permissions.
"""

import time
import json
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
import discord

from core.config import is_bot_owner
from db.database import get_config, set_config, get_db
from db.repos.management import get_welcome_extras, update_welcome_extras
from db.repos.mod_cases import record_mod_case
from api.auth import verify_guild_access, get_current_user_id
from api.models import (
    GuildConfigUpdate,
    BotRoleUpdateRequest,
    TicketRoleUpdateRequest,
    WelcomeSettingsUpdate,
    LockdownRequest,
)

router = APIRouter(prefix="/api/v1/guilds/{guild_id}/settings", tags=["Settings"])


async def record_audit(guild_id: int, user_id: int, action: str, details: str = ""):
    db = await get_db()
    await db.execute(
        "INSERT INTO dashboard_audit (guild_id, user_id, action, details, timestamp) VALUES (?, ?, ?, ?, ?)",
        (guild_id, user_id, action, details, time.time()),
    )
    await db.commit()


@router.get("")
async def get_settings(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Returns current server config, bot-role, ticket-role, and server ownership metadata."""
    cfg = await get_config(guild_id)
    bot_role_id = cfg.get("bot_role_id")
    bot_role = guild.get_role(bot_role_id) if bot_role_id else None

    ticket_role_id = cfg.get("ticket_role_id")
    ticket_role = guild.get_role(ticket_role_id) if ticket_role_id else None

    is_owner = (user_id == guild.owner_id) or is_bot_owner(user_id)

    return {
        "bot_role_id": str(bot_role_id) if bot_role_id else None,
        "bot_role_name": bot_role.name if bot_role else None,
        "bot_role_color": f"#{bot_role.color.value:06x}" if bot_role and bot_role.color.value != 0 else "#5865F2",
        "bot_role_members_count": len(bot_role.members) if bot_role else 0,
        "is_server_owner": is_owner,
        "can_configure_bot_role": is_owner,
        "owner_id": str(guild.owner_id),
        "owner_name": str(guild.owner.name if guild.owner else "Server Owner"),
        "ticket_role_id": str(ticket_role_id) if ticket_role_id else None,
        "ticket_role_name": ticket_role.name if ticket_role else None,
        "ticket_role_color": f"#{ticket_role.color.value:06x}" if ticket_role and ticket_role.color.value != 0 else "#5865F2",
        "ticket_role_members_count": len(ticket_role.members) if ticket_role else 0,
        "can_configure_ticket_role": is_owner,
        "welcome_ch": str(cfg.get("welcome_ch")) if cfg.get("welcome_ch") else None,
        "leave_ch": str(cfg.get("leave_ch")) if cfg.get("leave_ch") else None,
        "welcome_msg": cfg.get("welcome_msg"),
        "leave_msg": cfg.get("leave_msg"),
        "log_ch": str(cfg.get("log_ch")) if cfg.get("log_ch") else None,
        "mod_log_ch": str(cfg.get("mod_log_ch")) if cfg.get("mod_log_ch") else None,
        "server_log_ch": str(cfg.get("server_log_ch")) if cfg.get("server_log_ch") else None,
        "activity_log_ch": str(cfg.get("activity_log_ch")) if cfg.get("activity_log_ch") else None,
        "cmd_log_ch": str(cfg.get("cmd_log_ch")) if cfg.get("cmd_log_ch") else None,
    }


@router.post("/bot-role")
async def set_server_bot_role(
    guild_id: int,
    body: BotRoleUpdateRequest,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Exclusively allows Server Owner (or Bot Owner) to set the Bot-Role."""
    if user_id != guild.owner_id and not is_bot_owner(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Server Owner can configure or assign the Bot-Role.",
        )

    if not body.role_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No role_id provided")

    role = guild.get_role(body.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role {body.role_id} not found in this server")

    await set_config(guild_id, bot_role_id=role.id)
    await record_audit(
        guild_id=guild_id,
        user_id=user_id,
        action="set_bot_role",
        details=json.dumps({"role_id": role.id, "role_name": role.name}),
    )

    return {
        "status": "success",
        "bot_role_id": str(role.id),
        "bot_role_name": role.name,
        "bot_role_color": f"#{role.color.value:06x}" if role.color.value != 0 else "#5865F2",
        "bot_role_members_count": len(role.members),
    }


@router.post("/remove-bot-role")
async def remove_server_bot_role(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Exclusively allows Server Owner (or Bot Owner) to remove the Bot-Role restriction."""
    if user_id != guild.owner_id and not is_bot_owner(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Server Owner can remove the Bot-Role.",
        )

    await set_config(guild_id, bot_role_id=None)
    await record_audit(
        guild_id=guild_id,
        user_id=user_id,
        action="remove_bot_role",
        details="Bot-Role restriction lifted",
    )

    return {"status": "success", "message": "Bot-Role restriction has been removed successfully."}


@router.post("/ticket-role")
async def set_server_ticket_role(
    guild_id: int,
    body: TicketRoleUpdateRequest,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Exclusively allows Server Owner (or Bot Owner) to configure the Support Ticket Staff Role."""
    if user_id != guild.owner_id and not is_bot_owner(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Server Owner can configure or assign the Ticket Support Staff Role.",
        )

    if not body.role_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No role_id provided")

    role = guild.get_role(body.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role {body.role_id} not found in this server")

    await set_config(guild_id, ticket_role_id=role.id)
    await record_audit(
        guild_id=guild_id,
        user_id=user_id,
        action="set_ticket_role",
        details=json.dumps({"role_id": role.id, "role_name": role.name}),
    )

    return {
        "status": "success",
        "ticket_role_id": str(role.id),
        "ticket_role_name": role.name,
        "ticket_role_color": f"#{role.color.value:06x}" if role.color.value != 0 else "#5865F2",
        "ticket_role_members_count": len(role.members),
    }


@router.post("/remove-ticket-role")
async def remove_server_ticket_role(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Exclusively allows Server Owner (or Bot Owner) to remove the Ticket Support Staff Role."""
    if user_id != guild.owner_id and not is_bot_owner(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Server Owner can remove the Ticket Support Staff Role.",
        )

    await set_config(guild_id, ticket_role_id=None)
    await record_audit(
        guild_id=guild_id,
        user_id=user_id,
        action="remove_ticket_role",
        details="Ticket Support Staff Role cleared",
    )

    return {"status": "success", "message": "Ticket Support Staff Role has been removed successfully."}


@router.post("/lockdown")
async def server_lockdown(
    guild_id: int,
    body: LockdownRequest,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Server Owner & Bot-Role Staff command: Triggers emergency lockdown by disabling send_messages on @everyone."""
    cfg = await get_config(guild_id)
    bot_role_id = cfg.get("bot_role_id")
    member = guild.get_member(user_id)
    has_bot_role = bool(bot_role_id and member and any(r.id == bot_role_id for r in member.roles))

    if user_id != guild.owner_id and not is_bot_owner(user_id) and not has_bot_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Server Owner or members with the Bot-Role can trigger an emergency server lockdown.",
        )

    everyone = guild.default_role
    locked_count = 0
    for ch in guild.text_channels:
        try:
            overwrites = ch.overwrites_for(everyone)
            if overwrites.send_messages is not False:
                overwrites.send_messages = False
                await ch.set_permissions(everyone, overwrite=overwrites, reason=f"Dashboard Lockdown: {body.reason}")
                locked_count += 1
        except Exception:
            pass

    case_id = await record_mod_case(
        guild_id=guild_id,
        action="Lockdown",
        user_id=guild.owner_id,
        user_name="Server-Wide",
        mod_id=user_id,
        mod_name=member.display_name if member else str(user_id),
        reason=f"Dashboard Lockdown | Channels: {locked_count} | {body.reason}",
    )

    await record_audit(
        guild_id=guild_id,
        user_id=user_id,
        action="lockdown",
        details=json.dumps({"channels_locked": locked_count, "reason": body.reason, "case_id": case_id}),
    )

    # Dispatch Discord audit embed to configured log channel
    log_ch_id = cfg.get("server_log_ch") or cfg.get("mod_log_ch") or cfg.get("log_ch")
    if log_ch_id:
        try:
            cid = int(log_ch_id)
            ch = guild.get_channel(cid)
            if not ch:
                ch = await guild.fetch_channel(cid)
            if ch and hasattr(ch, "send"):
                embed = discord.Embed(
                    title=f"🚨 Emergency Lockdown Activated | Case #{case_id}",
                    description=(
                        f"**Case ID:** `#{case_id}`\n"
                        f"**Scope:** Server-Wide (All Channels)\n"
                        f"**Channels Locked:** `{locked_count}`\n"
                        f"**Initiator:** <@{user_id}> (Web Dashboard)\n"
                        f"**Reason:** {body.reason}"
                    ),
                    color=0xED4245,
                    timestamp=discord.utils.utcnow(),
                )
                embed.set_footer(text="Nexus  •  Audit Log")
                await ch.send(embed=embed)
        except Exception:
            pass

    return {
        "status": "success",
        "case_id": case_id,
        "channels_locked": locked_count,
        "message": f"Emergency lockdown activated: Locked down {locked_count} text channel(s).",
    }


@router.post("/unlockdown")
async def server_unlockdown(
    guild_id: int,
    body: LockdownRequest,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Server Owner & Bot-Role Staff command: Lifts emergency lockdown across text channels."""
    cfg = await get_config(guild_id)
    bot_role_id = cfg.get("bot_role_id")
    member = guild.get_member(user_id)
    has_bot_role = bool(bot_role_id and member and any(r.id == bot_role_id for r in member.roles))

    if user_id != guild.owner_id and not is_bot_owner(user_id) and not has_bot_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Server Owner or members with the Bot-Role can lift an emergency server lockdown.",
        )

    everyone = guild.default_role
    unlocked_count = 0
    for ch in guild.text_channels:
        try:
            overwrites = ch.overwrites_for(everyone)
            if overwrites.send_messages is False:
                overwrites.send_messages = None
                await ch.set_permissions(everyone, overwrite=overwrites, reason="Dashboard Unlockdown")
                unlocked_count += 1
        except Exception:
            pass

    case_id = await record_mod_case(
        guild_id=guild_id,
        action="Unlockdown",
        user_id=guild.owner_id,
        user_name="Server-Wide",
        mod_id=user_id,
        mod_name=member.display_name if member else str(user_id),
        reason=f"Dashboard Unlockdown | Channels: {unlocked_count}",
    )

    await record_audit(
        guild_id=guild_id,
        user_id=user_id,
        action="unlockdown",
        details=json.dumps({"channels_unlocked": unlocked_count, "case_id": case_id}),
    )

    # Dispatch Discord audit embed to configured log channel
    log_ch_id = cfg.get("server_log_ch") or cfg.get("mod_log_ch") or cfg.get("log_ch")
    if log_ch_id:
        try:
            cid = int(log_ch_id)
            ch = guild.get_channel(cid)
            if not ch:
                ch = await guild.fetch_channel(cid)
            if ch and hasattr(ch, "send"):
                embed = discord.Embed(
                    title=f"🔓 Emergency Lockdown Lifted | Case #{case_id}",
                    description=(
                        f"**Case ID:** `#{case_id}`\n"
                        f"**Scope:** Server-Wide (All Channels)\n"
                        f"**Channels Unlocked:** `{unlocked_count}`\n"
                        f"**Initiator:** <@{user_id}> (Web Dashboard)\n"
                        f"Standard messaging permissions restored."
                    ),
                    color=0x57F287,
                    timestamp=discord.utils.utcnow(),
                )
                embed.set_footer(text="Nexus  •  Audit Log")
                await ch.send(embed=embed)
        except Exception:
            pass

    return {
        "status": "success",
        "case_id": case_id,
        "channels_unlocked": unlocked_count,
        "message": f"Lockdown lifted: Restored permissions across {unlocked_count} text channel(s).",
    }


@router.post("/setupbot")
async def setup_bot_channels(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Auto-provisions the 📁 NEXUS LOGS category and 4 audit channels (matching /setupbot command)."""
    me = guild.me
    if not me or not me.guild_permissions.manage_channels:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bot lacks 'Manage Channels' permission in this server to auto-provision logging channels.",
        )

    cfg = await get_config(guild.id)
    bot_role_id = cfg.get("bot_role_id")
    bot_role = guild.get_role(bot_role_id) if bot_role_id else None
    ticket_role_id = cfg.get("ticket_role_id")
    ticket_role = guild.get_role(ticket_role_id) if ticket_role_id else None

    base_overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False, read_messages=False, send_messages=False,
        ),
        me: discord.PermissionOverwrite(
            view_channel=True, read_messages=True, send_messages=True,
            embed_links=True, attach_files=True, read_message_history=True,
            manage_channels=True,
        ),
    }
    if bot_role:
        base_overwrites[bot_role] = discord.PermissionOverwrite(
            view_channel=True, read_messages=True, read_message_history=True, send_messages=False,
        )

    try:
        category = discord.utils.get(guild.categories, name="📁 NEXUS LOGS")
        if not category:
            category = await guild.create_category(
                "📁 NEXUS LOGS",
                overwrites=base_overwrites,
                reason="Nexus /setupbot via Dashboard",
            )

        async def get_or_make_channel(name, topic, extra_role=None):
            existing = discord.utils.get(category.text_channels, name=name) or discord.utils.get(guild.text_channels, name=name)
            if existing:
                return existing
            ow = dict(base_overwrites)
            if extra_role:
                ow[extra_role] = discord.PermissionOverwrite(
                    view_channel=True, read_messages=True, read_message_history=True, send_messages=False,
                )
            return await guild.create_text_channel(
                name=name, category=category, overwrites=ow, topic=topic,
                reason="Nexus /setupbot via Dashboard",
            )

        mod_ch = await get_or_make_channel("🔒・mod-logs", "Moderation audit — Kicks, Bans, Timeouts, Warnings")
        server_ch = await get_or_make_channel("🔒・server-logs", "Server audit — Locks, Unlocks, Slowmode, Purges")
        activity_ch = await get_or_make_channel("🔒・activity-logs", "Staff DMs, Ticket events, Giveaways", extra_role=ticket_role)
        cmd_ch = await get_or_make_channel("🔒・cmd-logs", "Dedicated execution log channel for prefix and slash commands")

        await set_config(
            guild.id,
            log_ch=mod_ch.id,
            mod_log_ch=mod_ch.id,
            server_log_ch=server_ch.id,
            activity_log_ch=activity_ch.id,
            cmd_log_ch=cmd_ch.id,
        )

        await record_audit(
            guild_id=guild_id,
            user_id=user_id,
            action="setupbot",
            details="Auto-provisioned 📁 NEXUS LOGS category and audit channels",
        )

        return {
            "status": "success",
            "category_name": category.name,
            "mod_log_ch": str(mod_ch.id),
            "server_log_ch": str(server_ch.id),
            "activity_log_ch": str(activity_ch.id),
            "cmd_log_ch": str(cmd_ch.id),
            "channels": [
                {"id": str(mod_ch.id), "name": mod_ch.name},
                {"id": str(server_ch.id), "name": server_ch.name},
                {"id": str(activity_ch.id), "name": activity_ch.name},
                {"id": str(cmd_ch.id), "name": cmd_ch.name},
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to auto-provision channels: {str(e)}")


@router.put("")
async def update_settings(
    guild_id: int,
    body: GuildConfigUpdate,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Updates server configuration, validates channels/roles belong to this guild, and audits changes."""
    updates = body.model_dump(exclude_unset=True)

    # Bot-role protection: Only server owner or global bot owner can touch bot_role_id
    if "bot_role_id" in updates:
        if user_id != guild.owner_id and not is_bot_owner(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the Server Owner can configure or change the Bot-Role.",
            )

    # Ticket-role protection: Only server owner or global bot owner can touch ticket_role_id
    if "ticket_role_id" in updates:
        if user_id != guild.owner_id and not is_bot_owner(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the Server Owner can configure or change the Ticket Support Staff Role.",
            )

    # Validate channels belong to guild if provided
    ch_keys = ["welcome_ch", "leave_ch", "log_ch", "mod_log_ch", "server_log_ch", "activity_log_ch", "cmd_log_ch"]
    for k in ch_keys:
        if k in updates and updates[k] is not None:
            ch_id = updates[k]
            if not guild.get_channel(ch_id):
                updates[k] = None  # Silently clear broken/deleted channels instead of crashing

    # Validate roles belong to guild
    role_keys = ["bot_role_id", "ticket_role_id"]
    for r in role_keys:
        if r in updates and updates[r] is not None:
            r_id = updates[r]
            if not guild.get_role(r_id):
                updates[r] = None  # Clear broken/deleted roles

    if updates:
        await set_config(guild_id, **updates)
        await record_audit(
            guild_id=guild_id,
            user_id=user_id,
            action="update_settings",
            details=json.dumps(updates),
        )

    return {"status": "success", "updated_fields": list(updates.keys())}


@router.get("/welcome")
async def get_welcome_config(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
) -> dict[str, Any]:
    """Returns dedicated welcome and farewell configuration including DM and autorole extras."""
    cfg = await get_config(guild_id)
    extras = await get_welcome_extras(guild_id)

    welcome_ch = guild.get_channel(cfg.get("welcome_ch")) if cfg.get("welcome_ch") else None
    leave_ch = guild.get_channel(cfg.get("leave_ch")) if cfg.get("leave_ch") else None
    role = guild.get_role(extras.get("role_id")) if extras.get("role_id") else None

    return {
        "welcome_ch": str(cfg.get("welcome_ch")) if cfg.get("welcome_ch") else None,
        "welcome_ch_name": welcome_ch.name if welcome_ch else None,
        "leave_ch": str(cfg.get("leave_ch")) if cfg.get("leave_ch") else None,
        "leave_ch_name": leave_ch.name if leave_ch else None,
        "welcome_msg": cfg.get("welcome_msg") or "Welcome {mention} to **{guild}**! 🎉",
        "leave_msg": cfg.get("leave_msg") or "**{name}** has left the server. Goodbye! 👋",
        "dm_enabled": bool(extras.get("dm_enabled", 0)),
        "dm_message": extras.get("dm_message") or "Welcome to **{guild}**! Please check our rules and enjoy your stay. ✨",
        "role_id": str(extras.get("role_id")) if extras.get("role_id") else None,
        "role_name": role.name if role else None,
        "welcome_image_url": extras.get("welcome_image_url"),
        "leave_image_url": extras.get("leave_image_url"),
        "welcome_color": extras.get("welcome_color") or "#5865F2",
        "welcome_format": extras.get("welcome_format") or "embed",
        "leave_format": extras.get("leave_format") or "embed",
    }


@router.put("/welcome")
async def update_welcome_config(
    guild_id: int,
    body: WelcomeSettingsUpdate,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Updates welcome, leave, and direct-message onboarding settings."""
    data = body.model_dump(exclude_unset=True)

    cfg_updates = {}
    extra_updates = {}

    for k in ["welcome_ch", "leave_ch", "welcome_msg", "leave_msg"]:
        if k in data:
            if k in ("welcome_ch", "leave_ch") and data[k] is not None:
                if not guild.get_channel(data[k]):
                    data[k] = None
            cfg_updates[k] = data[k]

    for k in [
        "dm_enabled",
        "dm_message",
        "role_id",
        "welcome_image_url",
        "leave_image_url",
        "welcome_color",
        "welcome_format",
        "leave_format",
    ]:
        if k in data:
            if k == "role_id" and data[k] is not None:
                if not guild.get_role(data[k]):
                    data[k] = None
            extra_updates[k] = data[k]

    if cfg_updates:
        await set_config(guild_id, **cfg_updates)
    if extra_updates:
        await update_welcome_extras(guild_id, **extra_updates)

    await record_audit(
        guild_id=guild_id,
        user_id=user_id,
        action="update_welcome_settings",
        details=json.dumps(data),
    )

    return {"status": "success", "updated": list(data.keys())}
