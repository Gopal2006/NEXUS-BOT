"""
API Routes for Autorole, Leveling, Autoresponder, Birthdays, Mod Logs, and Dashboard Audit.
"""

import time
import json
import asyncio
import io
import base64
import aiohttp
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
import discord

from api.auth import verify_guild_access, get_current_user_id
from api.models import (
    AutoroleUpdate,
    LevelingUpdate,
    AutoresponderCreateRequest,
    BirthdaySettingsUpdate,
    AnnouncementCreateRequest,
    DirectMessageRequest,
    PollCreateRequest,
    GiveawayCreateRequest,
    TicketSetupRequest,
    ModerationActionRequest,
)
from db.database import get_db
from db.repos.management import (
    get_autorole_settings,
    update_autorole_settings,
)
from db.repos.engagement import (
    get_level_settings,
    update_level_settings,
    get_leaderboard,
    get_autoresponders,
    add_autoresponder,
    delete_autoresponder,
    get_birthday_settings,
    update_birthday_settings,
)
from db.repos.mod_cases import get_guild_mod_cases

router = APIRouter(prefix="/api/v1/guilds/{guild_id}", tags=["Features"])


async def record_audit(guild_id: int, user_id: int, action: str, details: str = ""):
    db = await get_db()
    await db.execute(
        "INSERT INTO dashboard_audit (guild_id, user_id, action, details, timestamp) VALUES (?, ?, ?, ?, ?)",
        (guild_id, user_id, action, details, time.time()),
    )
    await db.commit()


async def _resolve_channel(guild: discord.Guild, channel_id: Any):
    """Resolves channel from in-memory cache with fallback to Discord API fetch."""
    try:
        cid = int(channel_id)
    except (TypeError, ValueError):
        return None
    ch = guild.get_channel(cid)
    if not ch:
        try:
            ch = await guild.fetch_channel(cid)
        except Exception:
            try:
                ch = await guild._state._get_client().fetch_channel(cid)
            except Exception:
                ch = None
    return ch


# ── Autorole ──────────────────────────────────────────────────────────────────

@router.get("/autorole")
async def get_autorole(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
) -> dict[str, Any]:
    return await get_autorole_settings(guild_id)


@router.put("/autorole")
async def update_autorole(
    guild_id: int,
    body: AutoroleUpdate,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    updates = body.model_dump(exclude_unset=True)
    res = await update_autorole_settings(guild_id, **updates)
    await record_audit(guild_id, user_id, "update_autorole", json.dumps(updates))
    return {"status": "success", "settings": res}


# ── Leveling ──────────────────────────────────────────────────────────────────

@router.get("/leveling")
async def get_leveling(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
) -> dict[str, Any]:
    return await get_level_settings(guild_id)


@router.put("/leveling")
async def update_leveling(
    guild_id: int,
    body: LevelingUpdate,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    updates = body.model_dump(exclude_unset=True)
    res = await update_level_settings(guild_id, **updates)
    await record_audit(guild_id, user_id, "update_leveling", json.dumps(updates))
    return {"status": "success", "settings": res}


@router.get("/leveling/leaderboard")
async def get_leaderboard_route(
    guild_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    guild: discord.Guild = Depends(verify_guild_access),
) -> list[dict[str, Any]]:
    offset = (page - 1) * limit
    return await get_leaderboard(guild_id, limit=limit, offset=offset)


# ── Autoresponder ─────────────────────────────────────────────────────────────

@router.get("/autoresponders")
async def list_autoresponders(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
) -> list[dict[str, Any]]:
    return await get_autoresponders(guild_id)


@router.post("/autoresponders")
async def create_autoresponder(
    guild_id: int,
    body: AutoresponderCreateRequest,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    success = await add_autoresponder(guild_id, body.trigger, body.response, body.match_type)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add autoresponder")
    await record_audit(guild_id, user_id, "add_autoresponder", f"Trigger: {body.trigger}")
    return {"status": "success"}


@router.delete("/autoresponders/{trigger}")
async def remove_autoresponder_route(
    guild_id: int,
    trigger: str,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    success = await delete_autoresponder(guild_id, trigger)
    if not success:
        raise HTTPException(status_code=404, detail="Autoresponder not found")
    await record_audit(guild_id, user_id, "delete_autoresponder", f"Trigger: {trigger}")
    return {"status": "success"}


# ── Birthdays ─────────────────────────────────────────────────────────────────

@router.get("/birthdays")
async def get_birthdays_config(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
) -> dict[str, Any]:
    return await get_birthday_settings(guild_id)


@router.put("/birthdays")
async def update_birthdays_config(
    guild_id: int,
    body: BirthdaySettingsUpdate,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    updates = body.model_dump(exclude_unset=True)
    res = await update_birthday_settings(guild_id, **updates)
    await record_audit(guild_id, user_id, "update_birthdays", json.dumps(updates))
    return {"status": "success", "settings": res}


# ── Moderation Logs & Cases ───────────────────────────────────────────────────

@router.get("/modlog")
async def get_mod_cases(
    guild_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1, le=50),
    guild: discord.Guild = Depends(verify_guild_access),
) -> list[dict[str, Any]]:
    offset = (page - 1) * limit
    return await get_guild_mod_cases(guild_id, limit=limit, offset=offset)


@router.get("/warnings")
async def get_warnings(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
) -> list[dict[str, Any]]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM warns WHERE guild_id = ? ORDER BY timestamp DESC LIMIT 100",
        (guild_id,),
    ) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# ── Tickets, Giveaways, Polls Lists ───────────────────────────────────────────

@router.get("/tickets")
async def get_tickets(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
) -> list[dict[str, Any]]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM tickets WHERE guild_id = ? ORDER BY id DESC LIMIT 50",
        (guild_id,),
    ) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


@router.get("/giveaways")
async def get_giveaways(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
) -> list[dict[str, Any]]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM giveaways WHERE guild_id = ? ORDER BY id DESC LIMIT 50",
        (guild_id,),
    ) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


@router.get("/polls")
async def get_polls(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
) -> list[dict[str, Any]]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM polls WHERE guild_id = ? ORDER BY created_at DESC LIMIT 50",
        (guild_id,),
    ) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# ── Dashboard Audit Log ───────────────────────────────────────────────────────

@router.get("/audit")
async def get_dashboard_audit(
    guild_id: int,
    guild: discord.Guild = Depends(verify_guild_access),
) -> list[dict[str, Any]]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM dashboard_audit WHERE guild_id = ? ORDER BY timestamp DESC LIMIT 100",
        (guild_id,),
    ) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def _resolve_image_file(image_src: str | None) -> tuple[discord.File | None, str | None]:
    """
    Takes an image source (HTTP URL or base64 data URL) and returns:
    (discord.File, None) if downloaded or decoded successfully,
    or (None, fallback_url) if it's a URL that couldn't be downloaded directly.
    """
    if not image_src or not image_src.strip():
        return None, None
    s = image_src.strip()
    if s.startswith("data:image/"):
        try:
            header, encoded = s.split(",", 1)
            ext = header.split(";")[0].split("/")[1]
            if ext == "jpeg":
                ext = "jpg"
            img_bytes = base64.b64decode(encoded)
            return discord.File(io.BytesIO(img_bytes), filename=f"announcement.{ext}"), None
        except Exception:
            return None, None
    elif s.startswith(("http://", "https://")):
        try:
            clean_url = s.split("?")[0]
            fname = clean_url.split("/")[-1]
            valid_exts = (".png", ".jpg", ".jpeg", ".gif", ".webp")
            if not any(fname.lower().endswith(ext) for ext in valid_exts):
                fname = "announcement.png"
            async with aiohttp.ClientSession() as session:
                async with session.get(s, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        if data:
                            return discord.File(io.BytesIO(data), filename=fname), None
        except Exception:
            pass
        return None, s
    return None, None


# ── Communication & Broadcast (Announcements & DM Dispatch) ────────────────────

@router.post("/announce")
async def create_announcement(
    guild_id: int,
    body: AnnouncementCreateRequest,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Sends an announcement (plain text or rich embed) with optional link button, pings, and images."""
    content_text = (body.content or "").strip()
    image_src = (body.banner_url or "").strip()
    if not content_text and not image_src:
        raise HTTPException(
            status_code=400,
            detail="Announcement must contain either message text or an image.",
        )

    channel = await _resolve_channel(guild, body.channel_id)
    if not channel or not hasattr(channel, "send"):
        raise HTTPException(status_code=400, detail="Target text channel not found in this server")

    perms = channel.permissions_for(guild.me)
    if not perms.send_messages:
        raise HTTPException(status_code=403, detail=f"Bot lacks 'Send Messages' permission in #{channel.name}")
    if body.as_embed and not perms.embed_links:
        raise HTTPException(status_code=403, detail=f"Bot lacks 'Embed Links' permission in #{channel.name}")

    # Build action button view if configured
    view = None
    if body.button_url:
        label = (body.button_label or "Visit Link").strip()[:80]
        url = body.button_url.strip()
        if url.startswith(("http://", "https://", "discord://")):
            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(label=label or "Visit Link", url=url, style=discord.ButtonStyle.link))

    # Resolve mention ping
    content_prefix = ""
    allowed_mentions = discord.AllowedMentions(everyone=False, roles=False, users=True)
    if body.ping:
        p = body.ping.strip()
        if p == "@everyone":
            content_prefix = "@everyone\n"
            allowed_mentions = discord.AllowedMentions(everyone=True)
        elif p == "@here":
            content_prefix = "@here\n"
            allowed_mentions = discord.AllowedMentions(everyone=True)
        elif p.isdigit():
            role = guild.get_role(int(p))
            if role:
                content_prefix = f"{role.mention}\n"
                allowed_mentions = discord.AllowedMentions(roles=[role])

    # Sender info for footer / author
    sender = guild.get_member(user_id)
    author_name = sender.display_name if sender else "Staff"
    author_avatar = sender.display_avatar.url if sender and sender.display_avatar else None

    try:
        img_file, fallback_img_url = await _resolve_image_file(image_src)

        if body.as_embed:
            # Color resolution
            color_int = 0x5865F2
            if body.color:
                c_str = body.color.strip().lower()
                from core.ui import COLOR_PRESETS, parse_color
                if c_str in COLOR_PRESETS:
                    color_int = COLOR_PRESETS[c_str]
                else:
                    parsed = parse_color(c_str)
                    if parsed:
                        color_int = parsed

            embed = discord.Embed(
                title=body.title if body.title else None,
                description=content_text if content_text else None,
                color=color_int,
            )
            embed.set_author(name=f"Announced by {author_name}", icon_url=author_avatar)
            if body.thumbnail_url:
                embed.set_thumbnail(url=body.thumbnail_url)
            if img_file:
                embed.set_image(url=f"attachment://{img_file.filename}")
            elif fallback_img_url:
                embed.set_image(url=fallback_img_url)

            icon_url = guild.icon.url if guild.icon else None
            embed.set_footer(text=f"{guild.name} • Nexus Announcement", icon_url=icon_url)

            msg = await channel.send(
                content=content_prefix.strip() if content_prefix else None,
                embed=embed,
                file=img_file,
                view=view,
                allowed_mentions=allowed_mentions,
            )
        else:
            full_content_parts = []
            if content_prefix.strip():
                full_content_parts.append(content_prefix.strip())
            if content_text:
                full_content_parts.append(content_text)
            if not img_file and fallback_img_url:
                full_content_parts.append(fallback_img_url)

            plain_msg = "\n".join(full_content_parts).strip() or None

            msg = await channel.send(
                content=plain_msg,
                file=img_file,
                view=view,
                allowed_mentions=allowed_mentions,
            )

        await record_audit(
            guild_id=guild_id,
            user_id=user_id,
            action="create_announcement",
            details=json.dumps({"channel": channel.name, "as_embed": body.as_embed, "has_image": bool(image_src)}),
        )

        return {
            "status": "success",
            "message_id": str(msg.id),
            "channel_id": str(channel.id),
            "channel_name": channel.name,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch announcement: {str(e)}")


@router.post("/dm")
async def send_direct_message(
    guild_id: int,
    body: DirectMessageRequest,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Dispatches a direct message to a single member or broadcasts to all human members of a role."""
    view = None
    if body.button_url:
        label = (body.button_label or "Visit Link").strip()[:80]
        url = body.button_url.strip()
        if url.startswith(("http://", "https://", "discord://")):
            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(label=label or "Visit Link", url=url, style=discord.ButtonStyle.link))

    color_int = 0x5865F2
    if body.color:
        from core.ui import COLOR_PRESETS, parse_color
        c_str = body.color.strip().lower()
        if c_str in COLOR_PRESETS:
            color_int = COLOR_PRESETS[c_str]
        else:
            parsed = parse_color(c_str)
            if parsed:
                color_int = parsed

    sender = guild.get_member(user_id)
    sender_name = sender.display_name if sender else "Staff"

    embed = discord.Embed(
        title=body.title if body.title else None,
        description=body.content,
        color=color_int,
    )
    embed.set_author(name=f"Direct Message from {guild.name}", icon_url=guild.icon.url if guild.icon else None)
    if body.banner_url:
        embed.set_image(url=body.banner_url)
    embed.set_footer(text=f"Sent by {sender_name} • {guild.name}")

    if body.target_type == "user":
        try:
            target_uid = int(body.target_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid target user ID")

        member = guild.get_member(target_uid)
        if not member:
            try:
                member = await guild.fetch_member(target_uid)
            except Exception:
                member = None
        if not member:
            try:
                client = guild._state._get_client()
                member = await client.fetch_user(target_uid)
            except Exception:
                member = None

        if not member:
            raise HTTPException(status_code=404, detail="Target member or user not found")
        if getattr(member, "bot", False):
            raise HTTPException(status_code=400, detail="Cannot send direct messages to bot accounts")

        try:
            await member.send(embed=embed, view=view)
            await record_audit(
                guild_id=guild_id,
                user_id=user_id,
                action="send_dm_user",
                details=json.dumps({"target_user_id": target_uid, "title": body.title}),
            )
            name_display = getattr(member, "display_name", getattr(member, "name", str(target_uid)))
            return {
                "status": "success",
                "sent_count": 1,
                "failed_count": 0,
                "message": f"Successfully delivered DM to @{name_display}",
            }
        except discord.Forbidden:
            name_display = getattr(member, "display_name", getattr(member, "name", str(target_uid)))
            raise HTTPException(status_code=400, detail=f"{name_display} has direct messages disabled or has blocked the bot.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to send DM: {str(e)}")

    elif body.target_type == "role":
        try:
            target_rid = int(body.target_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid target role ID")

        role = guild.get_role(target_rid)
        if not role:
            raise HTTPException(status_code=404, detail="Target role not found in this server")

        recipients = [m for m in role.members if not m.bot]
        if not recipients:
            raise HTTPException(status_code=400, detail=f"Role @{role.name} has no human members to message")

        sent = 0
        failed = 0
        for m in recipients:
            try:
                await m.send(embed=embed, view=view)
                sent += 1
                await asyncio.sleep(0.4)
            except Exception:
                failed += 1

        await record_audit(
            guild_id=guild_id,
            user_id=user_id,
            action="broadcast_dm_role",
            details=json.dumps({"role_id": body.target_id, "sent": sent, "failed": failed}),
        )
        return {
            "status": "success",
            "sent_count": sent,
            "failed_count": failed,
            "message": f"Broadcast complete: {sent} delivered, {failed} failed (DMs closed)",
        }
    else:
        raise HTTPException(status_code=400, detail="Invalid target_type. Must be 'user' or 'role'")


# ── Interactive Poll Creation ──────────────────────────────────────────────────

@router.post("/polls/create")
async def create_interactive_poll(
    guild_id: int,
    body: PollCreateRequest,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Creates and dispatches an interactive button-based poll to a text channel."""
    channel = await _resolve_channel(guild, body.channel_id)
    if not channel or not hasattr(channel, "send"):
        raise HTTPException(status_code=400, detail="Target text channel not found")

    sender = guild.get_member(user_id)
    host_name = sender.display_name if sender else "Staff"

    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    view = discord.ui.View(timeout=None)

    embed = discord.Embed(
        title=f"📊 {body.question}",
        description="Cast your vote by clicking the buttons below!\n\n" + "\n".join(
            f"{number_emojis[i]} **{opt}**" for i, opt in enumerate(body.options)
        ),
        color=0x5865F2,
    )
    embed.set_footer(text=f"Poll hosted by {host_name} • Nexus Polls")

    for idx, opt in enumerate(body.options):
        emoji = number_emojis[idx] if idx < len(number_emojis) else None
        view.add_item(
            discord.ui.Button(
                label=opt[:80],
                emoji=emoji,
                style=discord.ButtonStyle.secondary,
                custom_id=f"web_poll_{idx}",
            )
        )

    try:
        msg = await channel.send(embed=embed, view=view)

        # Store in database
        db = await get_db()
        await db.execute(
            """INSERT INTO polls (message_id, channel_id, guild_id, question, options_json, votes_json, allowed_role_id, created_at, ended)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                msg.id,
                channel.id,
                guild.id,
                body.question,
                json.dumps(body.options),
                json.dumps({}),
                body.role_id,
                time.time(),
                0,
            ),
        )
        await db.commit()

        await record_audit(
            guild_id=guild_id,
            user_id=user_id,
            action="create_poll",
            details=json.dumps({"channel": channel.name, "question": body.question}),
        )

        return {
            "status": "success",
            "message_id": str(msg.id),
            "channel_name": channel.name,
            "question": body.question,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create poll: {str(e)}")


# ── Interactive Giveaway Creation ──────────────────────────────────────────────

@router.post("/giveaways/create")
async def create_interactive_giveaway(
    guild_id: int,
    body: GiveawayCreateRequest,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Creates and starts a prize giveaway with interactive entry button."""
    channel = await _resolve_channel(guild, body.channel_id)
    if not channel or not hasattr(channel, "send"):
        raise HTTPException(status_code=400, detail="Target text channel not found")

    sender = guild.get_member(user_id)
    host_name = sender.display_name if sender else "Staff"
    ends_at = time.time() + (body.duration_minutes * 60)

    role_req_str = ""
    if body.required_role_id:
        req_role = guild.get_role(body.required_role_id)
        if req_role:
            role_req_str = f"\n**Required Role:** {req_role.mention}"

    embed = discord.Embed(
        title=f"🎉 {body.prize}",
        description=(
            f"Click the button below to enter!\n\n"
            f"**Winners:** {body.winners}\n"
            f"**Hosted by:** {host_name}{role_req_str}\n"
            f"**Ends:** <t:{int(ends_at)}:R> (<t:{int(ends_at)}:f>)"
        ),
        color=0xFEE75C,
    )
    embed.set_footer(text=f"{body.winners} Winner(s) • Nexus Giveaways")

    view = discord.ui.View(timeout=None)
    view.add_item(
        discord.ui.Button(
            label="Enter Giveaway",
            emoji="🎉",
            style=discord.ButtonStyle.primary,
            custom_id="giveaway_enter_btn",
        )
    )

    try:
        msg = await channel.send(content="🎉 **GIVEAWAY** 🎉", embed=embed, view=view)

        # Store in database
        db = await get_db()
        cur = await db.execute(
            """INSERT INTO giveaways (guild_id, channel_id, message_id, host_id, prize, winners, ends_at, ended, required_role_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                guild.id,
                channel.id,
                msg.id,
                user_id,
                body.prize,
                body.winners,
                ends_at,
                0,
                body.required_role_id,
            ),
        )
        giveaway_id = cur.lastrowid
        await db.commit()

        await record_audit(
            guild_id=guild_id,
            user_id=user_id,
            action="create_giveaway",
            details=json.dumps({"channel": channel.name, "prize": body.prize}),
        )

        return {
            "status": "success",
            "giveaway_id": giveaway_id,
            "message_id": str(msg.id),
            "channel_name": channel.name,
            "prize": body.prize,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create giveaway: {str(e)}")


# ── Interactive Ticket Panel Deployment ────────────────────────────────────────

@router.post("/tickets/setup")
async def deploy_ticket_panel(
    guild_id: int,
    body: TicketSetupRequest,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Deploys a permanent support ticket panel to a text channel."""
    channel = await _resolve_channel(guild, body.channel_id)
    if not channel or not hasattr(channel, "send"):
        raise HTTPException(status_code=400, detail="Target text channel not found")

    embed = discord.Embed(
        title=body.title or "📩 Support Tickets",
        description=body.description or "Click the button below to open a private ticket with our staff team.",
        color=0x5865F2,
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text=f"{guild.name} Support System • Nexus Tickets")

    view = discord.ui.View(timeout=None)
    view.add_item(
        discord.ui.Button(
            label=body.button_label or "Create Ticket",
            emoji="📩",
            style=discord.ButtonStyle.primary,
            custom_id="ticket_create_btn",
        )
    )

    try:
        msg = await channel.send(embed=embed, view=view)
        await record_audit(
            guild_id=guild_id,
            user_id=user_id,
            action="setup_ticket_panel",
            details=json.dumps({"channel": channel.name}),
        )
        return {
            "status": "success",
            "message_id": str(msg.id),
            "channel_name": channel.name,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to deploy ticket panel: {str(e)}")


# ── Moderation Action Dispatcher ───────────────────────────────────────────────

@router.post("/moderation/action")
async def execute_moderation_action(
    guild_id: int,
    body: ModerationActionRequest,
    guild: discord.Guild = Depends(verify_guild_access),
    user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Executes a moderation command (kick, ban, mute, warn, lock, unlock) directly from the dashboard."""
    sender = guild.get_member(user_id)
    mod_name = sender.display_name if sender else "Dashboard Moderator"
    reason = f"{body.reason} (Moderator: {mod_name})"

    try:
        if body.action in ("kick", "ban", "mute", "warn"):
            member = guild.get_member(body.target_id)
            if not member:
                try:
                    member = await guild.fetch_member(body.target_id)
                except Exception:
                    member = None
            if not member and body.action != "ban":
                raise HTTPException(status_code=404, detail="Target member not found in this server")

            if body.action == "warn":
                db = await get_db()
                await db.execute(
                    "INSERT INTO warns (guild_id, user_id, mod_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (guild.id, member.id, user_id, body.reason, time.time()),
                )
                await db.commit()
                # DM target if possible
                try:
                    await member.send(
                        f"⚠️ You have received a formal warning in **{guild.name}**:\n**Reason:** {body.reason}"
                    )
                except Exception:
                    pass
                msg = f"Warned @{member.display_name} successfully"

            elif body.action == "mute":
                duration_mins = body.duration_minutes or 60
                import datetime
                until = discord.utils.utcnow() + datetime.timedelta(minutes=duration_mins)
                await member.timeout(until=until, reason=reason)
                msg = f"Timed out @{member.display_name} for {duration_mins} minute(s)"

            elif body.action == "kick":
                await member.kick(reason=reason)
                msg = f"Kicked @{member.display_name} from the server"

            elif body.action == "ban":
                if member:
                    await member.ban(reason=reason, delete_message_seconds=86400)
                    msg = f"Banned @{member.display_name} from the server"
                else:
                    user_obj = discord.Object(id=body.target_id)
                    await guild.ban(user_obj, reason=reason)
                    msg = f"Banned user ID {body.target_id} from the server"

        elif body.action in ("lock", "unlock"):
            channel = await _resolve_channel(guild, body.target_id)
            if not channel:
                raise HTTPException(status_code=400, detail="Target text channel not found")

            if body.action == "lock":
                await channel.set_permissions(guild.default_role, send_messages=False, reason=reason)
                msg = f"Locked #{channel.name}: sending messages disabled for @everyone"
            else:
                await channel.set_permissions(guild.default_role, send_messages=None, reason=reason)
                msg = f"Unlocked #{channel.name}: normal messaging restored"

        await record_audit(
            guild_id=guild_id,
            user_id=user_id,
            action=f"mod_{body.action}",
            details=json.dumps({"target_id": body.target_id, "reason": body.reason}),
        )

        return {"status": "success", "action": body.action, "message": msg}
    except discord.Forbidden:
        raise HTTPException(
            status_code=403,
            detail="Discord Permission Error: Bot lacks sufficient hierarchy or permissions to execute this action.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute moderation action: {str(e)}")
