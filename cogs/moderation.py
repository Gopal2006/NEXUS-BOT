"""
Moderation Cog — Comprehensive Moderation Suite with Case Tracking
Commands:
  /kick, /ban, /softban, /unban, /mute, /unmute, /warn, /warnings, /clearwarns
  /jail, /unjail, /purge, /slowmode, /lock, /unlock, /hide, /unhide, /nick, /modlogs
  /role add, /role remove
  Prefix & non-prefix aliases for all staff moderation actions.
"""

import discord
from discord.ext import commands, tasks
from discord import option
import datetime
import logging
import time

from core.config import is_bot_owner
from core.permissions import has_tier_permission, send_no_permission, requires_tier
from db.database import get_config, get_db
from db.repos.mod_cases import (
    record_mod_case,
    get_user_mod_cases,
    count_user_cases,
)
from utils.durations import parse_duration, format_duration

log = logging.getLogger("Nexus.Moderation")


async def is_bot_admin(ctx) -> bool:
    return await has_tier_permission(ctx, tier="staff")


async def no_perm(ctx):
    return await send_no_permission(ctx)


async def log_action(
    bot,
    guild: discord.Guild,
    action: str,
    mod: discord.Member,
    target,
    reason: str = None,
    mode: str = None,
    case_id: int = None,
):
    """Sends a formatted audit log entry to the designated channel."""
    cfg = await get_config(guild.id)
    server_actions = {"Lock", "Unlock", "Lockdown", "Unlockdown", "Slowmode", "Purge", "Hide", "Unhide"}
    if action in server_actions:
        ch_id = cfg.get("server_log_ch") or cfg.get("mod_log_ch") or cfg.get("log_ch")
    else:
        ch_id = cfg.get("mod_log_ch") or cfg.get("server_log_ch") or cfg.get("log_ch")

    if not ch_id:
        return
    try:
        cid = int(ch_id)
    except (TypeError, ValueError):
        return

    ch = guild.get_channel(cid)
    if not ch:
        try:
            ch = await guild.fetch_channel(cid)
        except Exception:
            try:
                ch = await bot.fetch_channel(cid)
            except Exception:
                return

    colors = {
        "Kick": 0xFEE75C,
        "Ban": 0xED4245,
        "Softban": 0xE67E22,
        "Unban": 0x57F287,
        "Mute": 0xF47FFF,
        "Unmute": 0x57F287,
        "Warn": 0xFFA500,
        "Jail": 0x9B59B6,
        "Unjail": 0x57F287,
        "Lock": 0xED4245,
        "Unlock": 0x57F287,
        "Lockdown": 0xED4245,
        "Unlockdown": 0x57F287,
        "Hide": 0xED4245,
        "Unhide": 0x57F287,
        "Slowmode": 0x5865F2,
        "Purge": 0x57F287,
        "Nick": 0x3498DB,
        "RoleAdd": 0x57F287,
        "RoleRemove": 0xED4245,
    }

    title_str = f"🛡️ Action: {action}"
    if case_id:
        title_str += f" | Case #{case_id}"

    embed = discord.Embed(
        title=title_str,
        color=colors.get(action, 0x5865F2),
        timestamp=discord.utils.utcnow(),
    )
    if isinstance(target, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread)):
        embed.add_field(name="📁 Channel", value=f"{target.mention} (`{target.id}`)", inline=True)
    elif str(target).lower() in ("all", "server-wide", "server wide"):
        embed.add_field(name="🌐 Scope", value="Server-Wide (All Channels)", inline=True)
    else:
        target_str = target.mention if hasattr(target, "mention") else str(target)
        target_id = getattr(target, "id", "N/A")
        embed.add_field(name="Target", value=f"{target_str} (`{target_id}`)", inline=True)

    embed.add_field(name="Moderator", value=f"{mod.mention} (`{mod.id}`)", inline=True)
    if mode:
        embed.add_field(name="⚙️ Execution", value=mode, inline=True)
    if reason:
        embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text="Nexus  •  Audit Log")
    try:
        await ch.send(embed=embed)
    except Exception as e:
        log.error(f"Failed to send mod log to channel {ch_id}: {e}")


def check_hierarchy(mod: discord.Member, target: discord.Member, me: discord.Member) -> tuple[bool, str]:
    """Validates role hierarchy between moderator, target, and the bot."""
    if target.id == mod.guild.owner_id:
        return False, "❌ You cannot perform moderation actions on the **Server Owner**."
    if target.id == me.id:
        return False, "❌ I cannot perform moderation actions on myself."
    if target.id == mod.id:
        return False, "❌ You cannot perform moderation actions on yourself."

    if not is_bot_owner(mod.id) and mod.id != mod.guild.owner_id:
        if target.top_role >= mod.top_role:
            return False, f"❌ You cannot act on {target.mention} because their highest role ({target.top_role.mention}) is equal to or higher than yours."

    if target.top_role >= me.top_role:
        return False, f"❌ I cannot act on {target.mention} because their highest role ({target.top_role.mention}) is equal to or higher than my bot role ({me.top_role.mention}). Drag my role higher in Server Settings."

    return True, ""


class Moderation(commands.Cog):
    """🔨 Comprehensive Moderation Suite."""

    def __init__(self, bot):
        self.bot = bot
        self.unmute_loop.start()

    def cog_unload(self):
        self.unmute_loop.cancel()

    # ── Background Auto-Unmute Loop ───────────────────────────────────────────
    @tasks.loop(seconds=30)
    async def unmute_loop(self):
        now = time.time()
        try:
            db = await get_db()
            async with db.execute(
                "SELECT * FROM mutes WHERE ends_at IS NOT NULL AND ends_at <= ?", (now,)
            ) as cur:
                rows = await cur.fetchall()

            for row in rows:
                guild = self.bot.get_guild(row["guild_id"])
                if not guild:
                    continue
                member = guild.get_member(row["user_id"])
                if member:
                    try:
                        await member.timeout(None, reason="Nexus: Scheduled timeout expired.")
                    except Exception:
                        pass
                await db.execute(
                    "DELETE FROM mutes WHERE guild_id=? AND user_id=?",
                    (row["guild_id"], row["user_id"]),
                )
                await db.commit()
        except Exception as e:
            log.error(f"Error in unmute background loop: {e}")

    @unmute_loop.before_loop
    async def before_unmute(self):
        await self.bot.wait_until_ready()

    # ── /kick ─────────────────────────────────────────────────────────────────
    @discord.slash_command(name="kick", description="Kick a member from the server")
    @option("member", discord.Member, description="Member to kick")
    @option("reason", str, description="Reason for kick", required=False, default=None)
    async def kick(self, ctx: discord.ApplicationContext, member: discord.Member, reason: str = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)

        if not is_bot_owner(ctx.author.id):
            if not reason or not reason.strip() or reason.strip() == "No reason provided":
                return await ctx.respond(
                    embed=discord.Embed(description="❌ You must provide a **reason** to kick a member.", color=0xED4245),
                    ephemeral=True,
                )
        reason = reason or "No reason provided"

        await ctx.defer(ephemeral=False)
        allowed, msg = check_hierarchy(ctx.author, member, ctx.guild.me)
        if not allowed:
            return await ctx.followup.send(embed=discord.Embed(description=msg, color=0xED4245), ephemeral=True)

        if not ctx.guild.me.guild_permissions.kick_members:
            return await ctx.followup.send(
                embed=discord.Embed(description="❌ I do not have the **Kick Members** permission.", color=0xED4245),
                ephemeral=True,
            )

        dm_sent = False
        try:
            dm_embed = discord.Embed(
                title="👢 You were kicked",
                description=f"You have been kicked from **{ctx.guild.name}**.\n\n**Reason:** {reason}",
                color=0xFEE75C,
                timestamp=discord.utils.utcnow(),
            )
            dm_embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
            await member.send(embed=dm_embed)
            dm_sent = True
        except Exception:
            dm_sent = False

        try:
            await member.kick(reason=f"{reason} | Moderator: {ctx.author}")
        except Exception as e:
            return await ctx.followup.send(embed=discord.Embed(title="❌ Kick Failed", description=f"`{e}`", color=0xED4245))

        case_id = await record_mod_case(
            guild_id=ctx.guild.id,
            action="Kick",
            user_id=member.id,
            user_name=str(member),
            mod_id=ctx.author.id,
            mod_name=str(ctx.author),
            reason=reason,
        )

        dm_status = "📨 Notified via DM." if dm_sent else "⚠️ Could not DM."
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=(
                f"**{member.mention}** (`{member}`) was kicked.\n\n"
                f"**🛡️ Case ID:** `#{case_id}`\n"
                f"**👤 Moderator:** {ctx.author.mention}\n"
                f"**📝 Reason:** {reason}\n"
                f"**📬 Status:** {dm_status}"
            ),
            color=0x57F287,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.followup.send(embed=embed)
        await log_action(self.bot, ctx.guild, "Kick", ctx.author, member, f"{reason} | {dm_status}", case_id=case_id)

    # ── /ban ──────────────────────────────────────────────────────────────────
    @discord.slash_command(name="ban", description="Ban a member from the server")
    @option("member", discord.Member, description="Member to ban")
    @option("reason", str, description="Reason for ban", required=False, default=None)
    @option("delete_days", int, description="Days of messages to delete (0-7)", required=False, default=0)
    async def ban(self, ctx: discord.ApplicationContext, member: discord.Member, reason: str = None, delete_days: int = 0):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)

        if not is_bot_owner(ctx.author.id):
            if not reason or not reason.strip() or reason.strip() == "No reason provided":
                return await ctx.respond(
                    embed=discord.Embed(description="❌ You must provide a **reason** to ban a member.", color=0xED4245),
                    ephemeral=True,
                )
        reason = reason or "No reason provided"

        await ctx.defer(ephemeral=False)
        allowed, msg = check_hierarchy(ctx.author, member, ctx.guild.me)
        if not allowed:
            return await ctx.followup.send(embed=discord.Embed(description=msg, color=0xED4245), ephemeral=True)

        if not ctx.guild.me.guild_permissions.ban_members:
            return await ctx.followup.send(
                embed=discord.Embed(description="❌ I do not have the **Ban Members** permission.", color=0xED4245),
                ephemeral=True,
            )

        dm_sent = False
        try:
            dm_embed = discord.Embed(
                title="🔨 You were banned",
                description=f"You have been banned from **{ctx.guild.name}**.\n\n**Reason:** {reason}",
                color=0xED4245,
                timestamp=discord.utils.utcnow(),
            )
            dm_embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
            await member.send(embed=dm_embed)
            dm_sent = True
        except Exception:
            dm_sent = False

        try:
            delete_secs = max(0, min(7, delete_days)) * 86400
            await member.ban(reason=f"{reason} | Moderator: {ctx.author}", delete_message_seconds=delete_secs)
        except Exception as e:
            return await ctx.followup.send(embed=discord.Embed(title="❌ Ban Failed", description=f"`{e}`", color=0xED4245))

        case_id = await record_mod_case(
            guild_id=ctx.guild.id,
            action="Ban",
            user_id=member.id,
            user_name=str(member),
            mod_id=ctx.author.id,
            mod_name=str(ctx.author),
            reason=reason,
        )

        dm_status = "📨 Notified via DM." if dm_sent else "⚠️ Could not DM."
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=(
                f"**{member.mention}** (`{member}`) has been banned.\n\n"
                f"**🛡️ Case ID:** `#{case_id}`\n"
                f"**👤 Moderator:** {ctx.author.mention}\n"
                f"**📝 Reason:** {reason}\n"
                f"**🗑️ Pruned:** `{delete_days} day(s)`\n"
                f"**📬 Status:** {dm_status}"
            ),
            color=0x57F287,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.followup.send(embed=embed)
        await log_action(self.bot, ctx.guild, "Ban", ctx.author, member, f"{reason} | {dm_status}", case_id=case_id)

    # ── /softban ──────────────────────────────────────────────────────────────
    @discord.slash_command(name="softban", description="Ban and immediately unban to delete user messages")
    @option("member", discord.Member, description="Member to softban")
    @option("reason", str, description="Reason for softban (required)", required=True)
    async def softban(self, ctx: discord.ApplicationContext, member: discord.Member, reason: str):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)

        if not reason or not reason.strip():
            return await ctx.respond(
                embed=discord.Embed(description="❌ You must provide a **reason** to softban a member.", color=0xED4245),
                ephemeral=True,
            )

        await ctx.defer(ephemeral=False)
        allowed, msg = check_hierarchy(ctx.author, member, ctx.guild.me)
        if not allowed:
            return await ctx.followup.send(embed=discord.Embed(description=msg, color=0xED4245), ephemeral=True)

        try:
            await member.ban(reason=f"Softban: {reason} | Mod: {ctx.author}", delete_message_seconds=86400)
            await ctx.guild.unban(member, reason=f"Softban unban: {reason}")
        except Exception as e:
            return await ctx.followup.send(embed=discord.Embed(title="❌ Softban Failed", description=f"`{e}`", color=0xED4245))

        case_id = await record_mod_case(
            guild_id=ctx.guild.id,
            action="Softban",
            user_id=member.id,
            user_name=str(member),
            mod_id=ctx.author.id,
            mod_name=str(ctx.author),
            reason=reason,
        )

        embed = discord.Embed(
            title="🧹 Member Softbanned",
            description=f"**{member.mention}** (`{member}`) has been softbanned and messages cleared.\n**Case ID:** `#{case_id}`\n**Reason:** {reason}",
            color=0x57F287,
        )
        await ctx.followup.send(embed=embed)
        await log_action(self.bot, ctx.guild, "Softban", ctx.author, member, reason, case_id=case_id)

    # ── /unban ────────────────────────────────────────────────────────────────
    @discord.slash_command(name="unban", description="Unban a user by ID")
    @option("user_id", str, description="User ID to unban")
    @option("reason", str, description="Reason", required=False, default="No reason provided")
    async def unban(self, ctx: discord.ApplicationContext, user_id: str, reason: str = "No reason provided"):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        await ctx.defer(ephemeral=False)
        try:
            uid = int(user_id.strip())
            user = await self.bot.fetch_user(uid)
            await ctx.guild.unban(user, reason=f"{reason} | Moderator: {ctx.author}")
            case_id = await record_mod_case(
                guild_id=ctx.guild.id,
                action="Unban",
                user_id=user.id,
                user_name=str(user),
                mod_id=ctx.author.id,
                mod_name=str(ctx.author),
                reason=reason,
            )
            embed = discord.Embed(
                title="✅ Member Unbanned",
                description=f"**{user.mention}** (`{user}`) has been unbanned.\n**Case ID:** `#{case_id}`\n**Reason:** {reason}",
                color=0x57F287,
            )
            await ctx.followup.send(embed=embed)
            await log_action(self.bot, ctx.guild, "Unban", ctx.author, user, reason, case_id=case_id)
        except Exception as e:
            await ctx.followup.send(embed=discord.Embed(description=f"❌ Unban failed: `{e}`", color=0xED4245), ephemeral=True)

    # ── /mute ─────────────────────────────────────────────────────────────────
    @discord.slash_command(name="mute", description="Timeout a member")
    @option("member", discord.Member, description="Member to mute")
    @option("duration", str, description="Duration e.g. 10m, 1h, 1d")
    @option("reason", str, description="Reason for mute (required)", required=True)
    async def mute(self, ctx: discord.ApplicationContext, member: discord.Member, duration: str, reason: str):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)

        if not reason or not reason.strip():
            return await ctx.respond(
                embed=discord.Embed(description="❌ You must provide a **reason** to mute a member.", color=0xED4245),
                ephemeral=True,
            )

        await ctx.defer(ephemeral=False)

        allowed, msg = check_hierarchy(ctx.author, member, ctx.guild.me)
        if not allowed:
            return await ctx.followup.send(embed=discord.Embed(description=msg, color=0xED4245), ephemeral=True)

        secs = parse_duration(duration)
        if secs < 1:
            return await ctx.followup.send(embed=discord.Embed(description="❌ Invalid duration format. Example: `10m`, `1h`, `1d`.", color=0xED4245), ephemeral=True)

        dm_sent = False
        try:
            dm_embed = discord.Embed(
                title="🔇 You were timed out",
                description=f"You have been timed out in **{ctx.guild.name}**.\n\n**Duration:** `{duration}`\n**Reason:** {reason}",
                color=0xF47FFF,
                timestamp=discord.utils.utcnow(),
            )
            await member.send(embed=dm_embed)
            dm_sent = True
        except Exception:
            dm_sent = False

        from datetime import timedelta
        until = discord.utils.utcnow() + timedelta(seconds=secs)
        try:
            await member.timeout(until, reason=f"{reason} | Moderator: {ctx.author}")
        except Exception as e:
            return await ctx.followup.send(embed=discord.Embed(title="❌ Timeout Failed", description=f"`{e}`", color=0xED4245))

        ends_at = time.time() + secs
        db = await get_db()
        await db.execute(
            "INSERT OR REPLACE INTO mutes (guild_id, user_id, ends_at) VALUES (?,?,?)",
            (ctx.guild.id, member.id, ends_at),
        )
        await db.commit()

        case_id = await record_mod_case(
            guild_id=ctx.guild.id,
            action="Mute",
            user_id=member.id,
            user_name=str(member),
            mod_id=ctx.author.id,
            mod_name=str(ctx.author),
            reason=reason,
            duration_seconds=secs,
        )

        dm_status = "📨 Notified via DM." if dm_sent else "⚠️ Could not DM."
        await ctx.followup.send(embed=discord.Embed(
            title="🔇 Member Muted",
            description=f"**{member.mention}** (`{member}`) timed out for `{duration}`.\n**Case ID:** `#{case_id}`\n**Reason:** {reason}\n**Status:** {dm_status}",
            color=0x57F287,
        ))
        await log_action(self.bot, ctx.guild, "Mute", ctx.author, member, f"{reason} | Duration: {duration} | {dm_status}", case_id=case_id)

    # ── /unmute ───────────────────────────────────────────────────────────────
    @discord.slash_command(name="unmute", description="Remove a timeout from a member")
    @option("member", discord.Member, description="Member to unmute")
    @option("reason", str, description="Reason", required=False, default="No reason provided")
    async def unmute(self, ctx: discord.ApplicationContext, member: discord.Member, reason: str = "No reason provided"):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        await ctx.defer(ephemeral=False)
        try:
            await member.timeout(None, reason=f"{reason} | Moderator: {ctx.author}")
        except Exception as e:
            return await ctx.followup.send(embed=discord.Embed(description=f"❌ Failed to remove timeout: `{e}`", color=0xED4245))

        db = await get_db()
        await db.execute("DELETE FROM mutes WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
        await db.commit()

        case_id = await record_mod_case(
            guild_id=ctx.guild.id,
            action="Unmute",
            user_id=member.id,
            user_name=str(member),
            mod_id=ctx.author.id,
            mod_name=str(ctx.author),
            reason=reason,
        )

        await ctx.followup.send(embed=discord.Embed(
            title="🔊 Unmuted",
            description=f"**{member.mention}** (`{member}`) timeout removed.\n**Case ID:** `#{case_id}`\n**Reason:** {reason}",
            color=0x57F287,
        ))
        await log_action(self.bot, ctx.guild, "Unmute", ctx.author, member, reason, case_id=case_id)

    # ── /warn ─────────────────────────────────────────────────────────────────
    @discord.slash_command(name="warn", description="Warn a member")
    @option("member", discord.Member, description="Member to warn")
    @option("reason", str, description="Reason for warning", required=False, default=None)
    async def warn(self, ctx: discord.ApplicationContext, member: discord.Member, reason: str = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)

        if not is_bot_owner(ctx.author.id):
            if not reason or not reason.strip():
                return await ctx.respond(
                    embed=discord.Embed(description="❌ You must provide a **reason** to warn a member.", color=0xED4245),
                    ephemeral=True,
                )
        reason = reason or "No reason provided"

        await ctx.defer(ephemeral=False)
        db = await get_db()
        await db.execute(
            "INSERT INTO warns (guild_id, user_id, mod_id, reason, timestamp) VALUES (?,?,?,?,?)",
            (ctx.guild.id, member.id, ctx.author.id, reason, time.time()),
        )
        await db.commit()

        total = await count_user_cases(ctx.guild.id, member.id)

        case_id = await record_mod_case(
            guild_id=ctx.guild.id,
            action="Warn",
            user_id=member.id,
            user_name=str(member),
            mod_id=ctx.author.id,
            mod_name=str(ctx.author),
            reason=reason,
        )

        dm_sent = False
        try:
            dm_embed = discord.Embed(
                title="⚠️ Warning Received",
                description=f"You received a warning in **{ctx.guild.name}**.\n\n**Reason:** {reason}\n**Total Disciplinary Cases:** {total}",
                color=0xFEE75C,
            )
            await member.send(embed=dm_embed)
            dm_sent = True
        except Exception:
            dm_sent = False

        dm_status = "📨 Notified via DM." if dm_sent else "⚠️ Could not DM."
        await ctx.followup.send(embed=discord.Embed(
            title="⚠️ Warning Issued",
            description=f"**{member.mention}** (`{member}`) has been warned.\n**Case ID:** `#{case_id}`\n**Reason:** {reason}\n**Total Cases:** `{total}`\n**Status:** {dm_status}",
            color=0xFEE75C,
        ))
        await log_action(self.bot, ctx.guild, "Warn", ctx.author, member, f"{reason} | {dm_status}", case_id=case_id)

    # ── /warnings ─────────────────────────────────────────────────────────────
    @discord.slash_command(name="warnings", description="View warning cases for a member")
    @option("member", discord.Member, description="Member to check")
    async def warnings(self, ctx: discord.ApplicationContext, member: discord.Member):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)

        cases = await get_user_mod_cases(ctx.guild.id, member.id, limit=10)
        warn_cases = [c for c in cases if c["action"] == "Warn"]

        embed = discord.Embed(
            title=f"⚠️ Warnings — {member.display_name}",
            description=f"**Total Warnings Logged: {len(warn_cases)}**",
            color=0xFEE75C,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        for c in warn_cases[:10]:
            embed.add_field(
                name=f"Case #{c['case_id']} — <t:{int(c['timestamp'])}:R>",
                value=f"**Mod:** <@{c['mod_id']}>\n**Reason:** {c['reason']}",
                inline=False,
            )
        await ctx.respond(embed=embed, ephemeral=True)

    # ── /clearwarns ───────────────────────────────────────────────────────────
    @discord.slash_command(name="clearwarns", description="Clear all warnings for a member")
    @option("member", discord.Member, description="Member to clear warns for")
    async def clearwarns(self, ctx: discord.ApplicationContext, member: discord.Member):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        db = await get_db()
        await db.execute("DELETE FROM warns WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
        await db.commit()
        await ctx.respond(embed=discord.Embed(
            title="🗑️ Warnings Cleared",
            description=f"All warning records for **{member}** have been cleared.",
            color=0x57F287,
        ))

    # ── /modlogs ──────────────────────────────────────────────────────────────
    @discord.slash_command(name="modlogs", description="Browse all disciplinary mod cases for a user")
    @option("member", discord.Member, description="Member to view history for")
    async def modlogs(self, ctx: discord.ApplicationContext, member: discord.Member):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)

        cases = await get_user_mod_cases(ctx.guild.id, member.id, limit=15)
        if not cases:
            return await ctx.respond(
                embed=discord.Embed(description=f"ℹ️ {member.mention} has a completely clean disciplinary record.", color=0x57F287),
                ephemeral=True,
            )

        embed = discord.Embed(
            title=f"📋 Moderation History — {member.display_name}",
            description=f"**Total Cases:** `{len(cases)}`",
            color=0x5865F2,
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        for c in cases:
            dur_str = f" ({format_duration(c['duration_seconds'])})" if c.get("duration_seconds") else ""
            embed.add_field(
                name=f"Case #{c['case_id']} — {c['action']}{dur_str} (<t:{int(c['timestamp'])}:R>)",
                value=f"**Mod:** <@{c['mod_id']}>\n**Reason:** {c['reason']}",
                inline=False,
            )
        await ctx.respond(embed=embed, ephemeral=True)

    # ── /lockdown ─────────────────────────────────────────────────────────────
    @discord.slash_command(name="lockdown", description="Emergency server lockdown: prevent @everyone from sending messages")
    @requires_tier("staff")
    @option("scope", str, description="Scope of lockdown", choices=["all", "current"], default="all")
    @option("reason", str, description="Reason for lockdown", required=False, default="Emergency lockdown")
    async def lockdown(self, ctx: discord.ApplicationContext, scope: str = "all", reason: str = "Emergency lockdown"):
        await ctx.defer(ephemeral=False)
        guild = ctx.guild
        everyone = guild.default_role
        locked_count = 0

        target_channels = [ctx.channel] if scope == "current" else guild.text_channels
        for ch in target_channels:
            try:
                overwrites = ch.overwrites_for(everyone)
                if overwrites.send_messages is not False:
                    overwrites.send_messages = False
                    await ch.set_permissions(everyone, overwrite=overwrites, reason=f"Lockdown by {ctx.author}: {reason}")
                    locked_count += 1
            except Exception:
                pass

        case_id = await record_mod_case(
            guild_id=ctx.guild.id,
            action="Lockdown",
            user_id=ctx.guild.owner_id,
            user_name="Server-Wide",
            mod_id=ctx.author.id,
            mod_name=str(ctx.author),
            reason=f"Scope: {scope} | Locked: {locked_count} ch | {reason}",
        )
        embed = discord.Embed(
            title="🔒 Server Lockdown Activated",
            description=(
                f"**Case ID:** `#{case_id}`\n"
                f"**Scope:** {scope.upper()}\n"
                f"**Channels Locked:** `{locked_count}`\n"
                f"**Reason:** {reason}\n"
                f"**Initiator:** {ctx.author.mention}"
            ),
            color=0xED4245,
            timestamp=discord.utils.utcnow(),
        )
        await ctx.followup.send(embed=embed)
        await log_action(self.bot, ctx.guild, "Lockdown", ctx.author, "Server-Wide" if scope == "all" else ctx.channel, f"Channels Locked: {locked_count} | {reason}", case_id=case_id)

    # ── /unlockdown ───────────────────────────────────────────────────────────
    @discord.slash_command(name="unlockdown", description="Lift emergency lockdown across channels")
    @requires_tier("staff")
    @option("scope", str, description="Scope to unlock", choices=["all", "current"], default="all")
    async def unlockdown(self, ctx: discord.ApplicationContext, scope: str = "all"):
        await ctx.defer(ephemeral=False)
        guild = ctx.guild
        everyone = guild.default_role
        unlocked_count = 0

        target_channels = [ctx.channel] if scope == "current" else guild.text_channels
        for ch in target_channels:
            try:
                overwrites = ch.overwrites_for(everyone)
                if overwrites.send_messages is False:
                    overwrites.send_messages = None
                    await ch.set_permissions(everyone, overwrite=overwrites, reason=f"Unlockdown by {ctx.author}")
                    unlocked_count += 1
            except Exception:
                pass

        case_id = await record_mod_case(
            guild_id=ctx.guild.id,
            action="Unlockdown",
            user_id=ctx.guild.owner_id,
            user_name="Server-Wide",
            mod_id=ctx.author.id,
            mod_name=str(ctx.author),
            reason=f"Scope: {scope} | Unlocked: {unlocked_count} ch",
        )
        embed = discord.Embed(
            title="🔓 Server Lockdown Lifted",
            description=(
                f"**Case ID:** `#{case_id}`\n"
                f"Unlocked **{unlocked_count}** channel(s). Standard messaging permissions restored.\n"
                f"**Initiator:** {ctx.author.mention}"
            ),
            color=0x57F287,
            timestamp=discord.utils.utcnow(),
        )
        await ctx.followup.send(embed=embed)
        await log_action(self.bot, ctx.guild, "Unlockdown", ctx.author, "Server-Wide" if scope == "all" else ctx.channel, f"Channels Unlocked: {unlocked_count}", case_id=case_id)

    # ── /hide / /unhide ───────────────────────────────────────────────────────
    @discord.slash_command(name="hide", description="Hide a channel from @everyone")
    @option("channel", discord.TextChannel, description="Channel to hide (defaults to current)", required=False, default=None)
    async def hide(self, ctx: discord.ApplicationContext, channel: discord.TextChannel = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        ch = channel or ctx.channel
        await ch.set_permissions(ctx.guild.default_role, view_channel=False, reason=f"Hidden by {ctx.author}")
        embed = discord.Embed(description=f"🔒 {ch.mention} is now hidden from `@everyone`.", color=0x57F287)
        await ctx.respond(embed=embed)
        await log_action(self.bot, ctx.guild, "Hide", ctx.author, ch)

    @discord.slash_command(name="unhide", description="Unhide a channel for @everyone")
    @option("channel", discord.TextChannel, description="Channel to unhide (defaults to current)", required=False, default=None)
    async def unhide(self, ctx: discord.ApplicationContext, channel: discord.TextChannel = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        ch = channel or ctx.channel
        await ch.set_permissions(ctx.guild.default_role, view_channel=None, reason=f"Unhidden by {ctx.author}")
        embed = discord.Embed(description=f"👁️ {ch.mention} is now visible to `@everyone`.", color=0x57F287)
        await ctx.respond(embed=embed)
        await log_action(self.bot, ctx.guild, "Unhide", ctx.author, ch)

    # ── /nick ─────────────────────────────────────────────────────────────────
    @discord.slash_command(name="nick", description="Change or reset a member's server nickname")
    @option("member", discord.Member, description="Target member")
    @option("nickname", str, description="New nickname (leave blank to reset)", required=False, default=None)
    async def nick(self, ctx: discord.ApplicationContext, member: discord.Member, nickname: str = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)

        allowed, msg = check_hierarchy(ctx.author, member, ctx.guild.me)
        if not allowed:
            return await ctx.respond(embed=discord.Embed(description=msg, color=0xED4245), ephemeral=True)

        try:
            await member.edit(nick=nickname, reason=f"Changed by {ctx.author}")
            target_nick = f"`{nickname}`" if nickname else "*Reset to default*"
            await ctx.respond(embed=discord.Embed(
                description=f"✅ Updated nickname for {member.mention} to {target_nick}.",
                color=0x57F287,
            ))
            await log_action(self.bot, ctx.guild, "Nick", ctx.author, member, f"Nickname set to: {nickname or 'Default'}")
        except Exception as e:
            await ctx.respond(embed=discord.Embed(description=f"❌ Failed to update nickname: `{e}`", color=0xED4245), ephemeral=True)

    # ── /role (add / remove) ──────────────────────────────────────────────────
    role_group = discord.SlashCommandGroup("role", "Assign or remove roles from a member")

    @role_group.command(name="add", description="Add a role to a member")
    @option("member", discord.Member, description="Target member")
    @option("role", discord.Role, description="Role to grant")
    async def role_add(self, ctx: discord.ApplicationContext, member: discord.Member, role: discord.Role):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)

        if role >= ctx.guild.me.top_role:
            return await ctx.respond(embed=discord.Embed(description=f"❌ {role.mention} is higher than my bot role.", color=0xED4245), ephemeral=True)
        if not is_bot_owner(ctx.author.id) and ctx.author.id != ctx.guild.owner_id and role >= ctx.author.top_role:
            return await ctx.respond(embed=discord.Embed(description=f"❌ You cannot assign {role.mention} (equal or higher than your top role).", color=0xED4245), ephemeral=True)

        try:
            await member.add_roles(role, reason=f"Added by {ctx.author}")
            await ctx.respond(embed=discord.Embed(description=f"✅ Granted {role.mention} to {member.mention}.", color=0x57F287))
            await log_action(self.bot, ctx.guild, "RoleAdd", ctx.author, member, f"Added {role.name}")
        except Exception as e:
            await ctx.respond(embed=discord.Embed(description=f"❌ Failed: `{e}`", color=0xED4245), ephemeral=True)

    @role_group.command(name="remove", description="Remove a role from a member")
    @option("member", discord.Member, description="Target member")
    @option("role", discord.Role, description="Role to revoke")
    async def role_remove(self, ctx: discord.ApplicationContext, member: discord.Member, role: discord.Role):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)

        if role >= ctx.guild.me.top_role:
            return await ctx.respond(embed=discord.Embed(description=f"❌ {role.mention} is higher than my bot role.", color=0xED4245), ephemeral=True)
        if not is_bot_owner(ctx.author.id) and ctx.author.id != ctx.guild.owner_id and role >= ctx.author.top_role:
            return await ctx.respond(embed=discord.Embed(description=f"❌ You cannot revoke {role.mention} (equal or higher than your top role).", color=0xED4245), ephemeral=True)

        try:
            await member.remove_roles(role, reason=f"Removed by {ctx.author}")
            await ctx.respond(embed=discord.Embed(description=f"✅ Removed {role.mention} from {member.mention}.", color=0x57F287))
            await log_action(self.bot, ctx.guild, "RoleRemove", ctx.author, member, f"Removed {role.name}")
        except Exception as e:
            await ctx.respond(embed=discord.Embed(description=f"❌ Failed: `{e}`", color=0xED4245), ephemeral=True)

    # ── /purge ────────────────────────────────────────────────────────────────
    @discord.slash_command(name="purge", description="Bulk delete messages")
    @option("amount", int, description="Number of messages to delete (1–100)")
    @option("member", discord.Member, description="Only delete messages from this user", required=False, default=None)
    async def purge(self, ctx: discord.ApplicationContext, amount: int, member: discord.Member = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        amount = max(1, min(100, amount))
        await ctx.defer(ephemeral=True)
        if member:
            def check(m):
                return m.author.id == member.id
            deleted = await ctx.channel.purge(limit=amount * 3, check=check, bulk=True)
        else:
            deleted = await ctx.channel.purge(limit=amount, bulk=True)
        deleted_count = len(deleted)
        reason = f"Purged {deleted_count} message(s) in {ctx.channel.mention}"
        if member:
            reason += f" sent by {member.mention}"
        await log_action(self.bot, ctx.guild, "Purge", ctx.author, ctx.channel, reason)
        await ctx.followup.send(embed=discord.Embed(description=f"🗑️ Deleted **{deleted_count}** message(s).", color=0x57F287), ephemeral=True)

    # ── /slowmode ─────────────────────────────────────────────────────────────
    @discord.slash_command(name="slowmode", description="Set slowmode for a channel")
    @option("seconds", int, description="Slowmode in seconds (0 to disable)")
    @option("channel", discord.TextChannel, description="Channel (defaults to current)", required=False, default=None)
    async def slowmode(self, ctx: discord.ApplicationContext, seconds: int, channel: discord.TextChannel = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        ch = channel or ctx.channel
        await ch.edit(slowmode_delay=max(0, min(21600, seconds)))
        msg = f"⏱️ Slowmode in {ch.mention} set to `{seconds}s`." if seconds > 0 else f"⏱️ Slowmode in {ch.mention} disabled."
        await ctx.respond(embed=discord.Embed(description=msg, color=0x57F287))

    # ── /lock / /unlock ───────────────────────────────────────────────────────
    @discord.slash_command(name="lock", description="Lock a channel for @everyone")
    @option("channel", discord.TextChannel, description="Channel to lock (defaults to current)", required=False, default=None)
    @option("reason", str, description="Reason for lock", required=False, default="No reason provided")
    async def lock(self, ctx: discord.ApplicationContext, channel: discord.TextChannel = None, reason: str = "No reason provided"):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        await ctx.defer(ephemeral=False)
        ch = channel or ctx.channel
        overwrite = ch.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=f"Locked by {ctx.author}: {reason}")
        await ctx.followup.send(embed=discord.Embed(title="🔒 Channel Locked", description=f"{ch.mention} is locked.\n**Reason:** {reason}", color=0x57F287))
        await log_action(self.bot, ctx.guild, "Lock", ctx.author, ch, reason)

    @discord.slash_command(name="unlock", description="Unlock a channel for @everyone")
    @option("channel", discord.TextChannel, description="Channel to unlock (defaults to current)", required=False, default=None)
    async def unlock(self, ctx: discord.ApplicationContext, channel: discord.TextChannel = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        await ctx.defer(ephemeral=False)
        ch = channel or ctx.channel
        overwrite = ch.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=f"Unlocked by {ctx.author}")
        await ctx.followup.send(embed=discord.Embed(title="🔓 Channel Unlocked", description=f"{ch.mention} has been unlocked.", color=0x57F287))
        await log_action(self.bot, ctx.guild, "Unlock", ctx.author, ch)

    # ── Prefix & Non-Prefix Commands ──────────────────────────────────────────
    @commands.command(name="kick")
    async def prefix_kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        if not is_bot_owner(ctx.author.id):
            if not reason or not reason.strip():
                return await ctx.reply("❌ You must provide a **reason** to kick a member.")
        reason = reason or "No reason provided"
        try:
            await member.kick(reason=f"{reason} | Mod: {ctx.author}")
            case_id = await record_mod_case(ctx.guild.id, "Kick", member.id, str(member), ctx.author.id, str(ctx.author), reason)
            mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
            await log_action(self.bot, ctx.guild, "Kick", ctx.author, member, reason, mode=mode, case_id=case_id)
            await ctx.reply(f"✅ Kicked **{member}** (Case #{case_id}).")
        except Exception as e:
            await ctx.reply(f"❌ Failed to kick: `{e}`")

    @commands.command(name="ban")
    async def prefix_ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        if not is_bot_owner(ctx.author.id):
            if not reason or not reason.strip():
                return await ctx.reply("❌ You must provide a **reason** to ban a member.")
        reason = reason or "No reason provided"
        try:
            await member.ban(reason=f"{reason} | Mod: {ctx.author}")
            case_id = await record_mod_case(ctx.guild.id, "Ban", member.id, str(member), ctx.author.id, str(ctx.author), reason)
            mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
            await log_action(self.bot, ctx.guild, "Ban", ctx.author, member, reason, mode=mode, case_id=case_id)
            await ctx.reply(f"✅ Banned **{member}** (Case #{case_id}).")
        except Exception as e:
            await ctx.reply(f"❌ Failed to ban: `{e}`")

    @commands.command(name="softban")
    async def prefix_softban(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        if not is_bot_owner(ctx.author.id):
            if not reason or not reason.strip():
                return await ctx.reply("❌ You must provide a **reason** to softban a member.")
        try:
            await member.ban(reason=f"Softban: {reason}", delete_message_seconds=86400)
            await ctx.guild.unban(member, reason="Softban unban")
            case_id = await record_mod_case(ctx.guild.id, "Softban", member.id, str(member), ctx.author.id, str(ctx.author), reason)
            mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
            await log_action(self.bot, ctx.guild, "Softban", ctx.author, member, reason, mode=mode, case_id=case_id)
            await ctx.reply(f"🧹 Softbanned **{member}** (Case #{case_id}).")
        except Exception as e:
            await ctx.reply(f"❌ Softban failed: `{e}`")

    @commands.command(name="mute", aliases=["timeout"])
    async def prefix_mute(self, ctx: commands.Context, member: discord.Member, duration: str = "10m", *, reason: str = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        if not is_bot_owner(ctx.author.id):
            if not reason or not reason.strip():
                return await ctx.reply("❌ You must provide a **reason** to mute a member.")
        secs = parse_duration(duration)
        if secs < 10:
            return await ctx.reply("❌ Invalid duration (minimum 10s, e.g. `10m`, `1h`, `1d`).")
        until = discord.utils.utcnow() + datetime.timedelta(seconds=secs)
        try:
            await member.timeout(until, reason=reason)
            case_id = await record_mod_case(ctx.guild.id, "Mute", member.id, str(member), ctx.author.id, str(ctx.author), reason, secs)
            mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
            await log_action(self.bot, ctx.guild, "Mute", ctx.author, member, f"{reason} ({duration})", mode=mode, case_id=case_id)
            await ctx.reply(f"🔇 Timed out **{member}** for `{duration}` (Case #{case_id}).")
        except Exception as e:
            await ctx.reply(f"❌ Failed to mute: `{e}`")

    @commands.command(name="unmute", aliases=["untimeout"])
    async def prefix_unmute(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        reason = reason or "No reason provided"
        try:
            await member.remove_timeout(reason=reason)
            case_id = await record_mod_case(ctx.guild.id, "Unmute", member.id, str(member), ctx.author.id, str(ctx.author), reason)
            mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
            await log_action(self.bot, ctx.guild, "Unmute", ctx.author, member, reason, mode=mode, case_id=case_id)
            await ctx.reply(f"🔊 Removed timeout from **{member}** (Case #{case_id}).")
        except Exception as e:
            await ctx.reply(f"❌ Failed to unmute: `{e}`")

    @commands.command(name="warn")
    async def prefix_warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        if not is_bot_owner(ctx.author.id):
            if not reason or not reason.strip():
                return await ctx.reply("❌ You must provide a **reason** to warn a member.")
        reason = reason or "No reason provided"
        case_id = await record_mod_case(ctx.guild.id, "Warn", member.id, str(member), ctx.author.id, str(ctx.author), reason)
        mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
        await log_action(self.bot, ctx.guild, "Warn", ctx.author, member, reason, mode=mode, case_id=case_id)
        await ctx.reply(f"⚠️ Warned **{member}** for: `{reason}` (Case #{case_id})")

    @commands.command(name="warnings", aliases=["warns", "modlogs"])
    async def prefix_warnings(self, ctx: commands.Context, member: discord.Member):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        cases = await get_user_mod_cases(ctx.guild.id, member.id, limit=10)
        if not cases:
            return await ctx.reply(f"ℹ️ **{member}** has a clean record.")
        embed = discord.Embed(title=f"📋 Cases for {member}", color=0xFEE75C)
        for r in cases:
            embed.add_field(
                name=f"Case #{r['case_id']} — {r['action']} (<t:{int(r['timestamp'])}:R>)",
                value=f"Mod: <@{r['mod_id']}>\nReason: {r['reason']}",
                inline=False,
            )
        embed.set_footer(text=f"Total: {len(cases)} cases")
        await ctx.reply(embed=embed)

    @commands.command(name="purge")
    async def prefix_purge(self, ctx: commands.Context, amount: int = 10):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        deleted = await ctx.channel.purge(limit=min(amount, 100) + 1)
        deleted_count = max(0, len(deleted) - 1)
        mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
        await log_action(self.bot, ctx.guild, "Purge", ctx.author, ctx.channel, f"Purged {deleted_count} messages", mode=mode)
        await ctx.send(f"🗑️ Deleted {deleted_count} messages.", delete_after=5)

    @commands.command(name="lock")
    async def prefix_lock(self, ctx: commands.Context, channel: discord.TextChannel = None, *, reason: str = "No reason provided"):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        ch = channel or ctx.channel
        perms = ch.overwrites_for(ctx.guild.default_role)
        perms.send_messages = False
        await ch.set_permissions(ctx.guild.default_role, overwrite=perms, reason=f"Locked by {ctx.author}: {reason}")
        mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
        await log_action(self.bot, ctx.guild, "Lock", ctx.author, ch, reason, mode=mode)
        await ctx.reply(f"🔒 Locked {ch.mention}.")

    @commands.command(name="unlock")
    async def prefix_unlock(self, ctx: commands.Context, channel: discord.TextChannel = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        ch = channel or ctx.channel
        perms = ch.overwrites_for(ctx.guild.default_role)
        perms.send_messages = None
        await ch.set_permissions(ctx.guild.default_role, overwrite=perms, reason=f"Unlocked by {ctx.author}")
        mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
        await log_action(self.bot, ctx.guild, "Unlock", ctx.author, ch, mode=mode)
        await ctx.reply(f"🔓 Unlocked {ch.mention}.")

    @commands.command(name="hide")
    async def prefix_hide(self, ctx: commands.Context, channel: discord.TextChannel = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        ch = channel or ctx.channel
        await ch.set_permissions(ctx.guild.default_role, view_channel=False)
        await ctx.reply(f"🔒 {ch.mention} is now hidden.")

    @commands.command(name="unhide")
    async def prefix_unhide(self, ctx: commands.Context, channel: discord.TextChannel = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        ch = channel or ctx.channel
        await ch.set_permissions(ctx.guild.default_role, view_channel=None)
        await ctx.reply(f"👁️ {ch.mention} is now visible.")

    @commands.command(name="slowmode")
    async def prefix_slowmode(self, ctx: commands.Context, seconds: int = 0, channel: discord.TextChannel = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        ch = channel or ctx.channel
        seconds = max(0, min(21600, seconds))
        await ch.edit(slowmode_delay=seconds)
        mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
        await log_action(self.bot, ctx.guild, "Slowmode", ctx.author, ch, f"Set to {seconds}s", mode=mode)
        await ctx.reply(f"⏱️ Slowmode in {ch.mention} set to `{seconds}s`." if seconds else f"⏱️ Slowmode in {ch.mention} disabled.")

    @commands.command(name="nick", aliases=["nickname"])
    async def prefix_nick(self, ctx: commands.Context, member: discord.Member, *, nickname: str = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        allowed, msg = check_hierarchy(ctx.author, member, ctx.guild.me)
        if not allowed:
            return await ctx.reply(msg)
        try:
            await member.edit(nick=nickname, reason=f"Changed by {ctx.author}")
            target_nick = f"`{nickname}`" if nickname else "*Reset to default*"
            mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
            await log_action(self.bot, ctx.guild, "Nick", ctx.author, member, f"Nickname set to: {nickname or 'Default'}", mode=mode)
            await ctx.reply(f"✅ Updated nickname for {member.mention} to {target_nick}.")
        except Exception as e:
            await ctx.reply(f"❌ Failed to update nickname: `{e}`")

    @commands.group(name="role", invoke_without_command=True)
    async def prefix_role(self, ctx: commands.Context):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        await ctx.reply("ℹ️ Usage: `n!role add <@member> <@role>` or `n!role remove <@member> <@role>`")

    @prefix_role.command(name="add")
    async def prefix_role_add(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        if role >= ctx.guild.me.top_role:
            return await ctx.reply(f"❌ {role.mention} is higher than my bot role.")
        if not is_bot_owner(ctx.author.id) and ctx.author.id != ctx.guild.owner_id and role >= ctx.author.top_role:
            return await ctx.reply(f"❌ You cannot assign {role.mention} (equal or higher than your top role).")
        try:
            await member.add_roles(role, reason=f"Added by {ctx.author}")
            mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
            await log_action(self.bot, ctx.guild, "RoleAdd", ctx.author, member, f"Added {role.name}", mode=mode)
            await ctx.reply(f"✅ Granted {role.mention} to {member.mention}.")
        except Exception as e:
            await ctx.reply(f"❌ Failed to add role: `{e}`")

    @prefix_role.command(name="remove")
    async def prefix_role_remove(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        if role >= ctx.guild.me.top_role:
            return await ctx.reply(f"❌ {role.mention} is higher than my bot role.")
        if not is_bot_owner(ctx.author.id) and ctx.author.id != ctx.guild.owner_id and role >= ctx.author.top_role:
            return await ctx.reply(f"❌ You cannot revoke {role.mention} (equal or higher than your top role).")
        try:
            await member.remove_roles(role, reason=f"Removed by {ctx.author}")
            mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
            await log_action(self.bot, ctx.guild, "RoleRemove", ctx.author, member, f"Removed {role.name}", mode=mode)
            await ctx.reply(f"✅ Removed {role.mention} from {member.mention}.")
        except Exception as e:
            await ctx.reply(f"❌ Failed to remove role: `{e}`")

    @commands.command(name="lockdown")
    @requires_tier("staff")
    async def prefix_lockdown(self, ctx: commands.Context, scope: str = "all", *, reason: str = "Emergency lockdown"):
        guild = ctx.guild
        everyone = guild.default_role
        target_channels = [ctx.channel] if scope.lower() == "current" else guild.text_channels
        locked_count = 0
        for ch in target_channels:
            try:
                overwrites = ch.overwrites_for(everyone)
                if overwrites.send_messages is not False:
                    overwrites.send_messages = False
                    await ch.set_permissions(everyone, overwrite=overwrites, reason=f"Lockdown by {ctx.author}: {reason}")
                    locked_count += 1
            except Exception:
                pass
        mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
        case_id = await record_mod_case(
            guild_id=ctx.guild.id,
            action="Lockdown",
            user_id=ctx.guild.owner_id,
            user_name="Server-Wide",
            mod_id=ctx.author.id,
            mod_name=str(ctx.author),
            reason=f"Scope: {scope} | Locked: {locked_count} ch | {reason}",
        )
        await log_action(self.bot, ctx.guild, "Lockdown", ctx.author, "Server-Wide" if scope.lower() == "all" else ctx.channel, f"Channels Locked: {locked_count} | {reason}", mode=mode, case_id=case_id)
        await ctx.reply(f"🔒 Server Lockdown Activated (`Case #{case_id}`). Locked **{locked_count}** channel(s).\n**Reason:** {reason}")

    @commands.command(name="unlockdown")
    @requires_tier("staff")
    async def prefix_unlockdown(self, ctx: commands.Context, scope: str = "all"):
        guild = ctx.guild
        everyone = guild.default_role
        target_channels = [ctx.channel] if scope.lower() == "current" else guild.text_channels
        unlocked_count = 0
        for ch in target_channels:
            try:
                overwrites = ch.overwrites_for(everyone)
                if overwrites.send_messages is False:
                    overwrites.send_messages = None
                    await ch.set_permissions(everyone, overwrite=overwrites, reason=f"Unlockdown by {ctx.author}")
                    unlocked_count += 1
            except Exception:
                pass
        mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
        case_id = await record_mod_case(
            guild_id=ctx.guild.id,
            action="Unlockdown",
            user_id=ctx.guild.owner_id,
            user_name="Server-Wide",
            mod_id=ctx.author.id,
            mod_name=str(ctx.author),
            reason=f"Scope: {scope} | Unlocked: {unlocked_count} ch",
        )
        await log_action(self.bot, ctx.guild, "Unlockdown", ctx.author, "Server-Wide" if scope.lower() == "all" else ctx.channel, f"Channels Unlocked: {unlocked_count}", mode=mode, case_id=case_id)
        await ctx.reply(f"🔓 Server Lockdown Lifted (`Case #{case_id}`). Restored permissions across **{unlocked_count}** channel(s).")


def setup(bot):
    bot.add_cog(Moderation(bot))
