"""
Moderation Cog
Commands:
  /kick, /ban, /unban, /mute, /unmute, /warn, /warnings, /clearwarns
  /purge, /slowmode, /lock, /unlock
  n!kick, n!ban, n!purge (prefix shortcuts)
"""

import discord
from discord.ext import commands, tasks
from discord import option
import aiosqlite
import datetime
import logging
import time
from pathlib import Path

log = logging.getLogger("Nexus.Moderation")

DB_PATH = Path("nexus.db")
GLOBAL_OWNER_ID = 1201050377911554061


async def get_config(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM guild_config WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
        if row is None:
            await db.execute("INSERT INTO guild_config (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
            async with db.execute("SELECT * FROM guild_config WHERE guild_id=?", (guild_id,)) as cur:
                row = await cur.fetchone()
        return dict(row)


async def is_bot_admin(ctx) -> bool:
    """Server owner, global owner, non-prefix user, or member with the bot-role.
    Administrators without the bot-role are NOT granted access."""
    if ctx.author.id == GLOBAL_OWNER_ID:
        return True
    if hasattr(ctx, "bot") and ctx.author.id in getattr(ctx.bot, "non_prefix_users", set()):
        return True
    if ctx.guild is None:
        return False
    if ctx.author.id == ctx.guild.owner_id:
        return True
    cfg = await get_config(ctx.guild.id)
    role_id = cfg.get("bot_role_id")
    if role_id:
        member = ctx.guild.get_member(ctx.author.id) or ctx.author
        if hasattr(member, "roles"):
            return any(r.id == role_id for r in member.roles)
    return False


async def no_perm(ctx):
    """Ephemeral 'ask server owner for bot role' response."""
    if ctx.guild is None:
        embed = discord.Embed(
            title="🔒 Access Denied",
            description="Commands can only be used inside a server.",
            color=0xED4245,
        )
        if hasattr(ctx, "respond"):
            return await ctx.respond(embed=embed, ephemeral=True)
        return await ctx.reply(embed=embed)

    cfg = await get_config(ctx.guild.id)
    role_id  = cfg.get("bot_role_id")
    bot_role = ctx.guild.get_role(role_id) if role_id else None
    tip = (
        f"You need the **{bot_role.name}** role to use bot commands.\n"
        "Please ask the **server owner** to grant you this role."
        if bot_role else
        "You don't have permission to use bot commands.\n"
        "Please ask the **server owner** to assign a bot-role using `/set-botrole`."
    )
    if hasattr(ctx, "respond"):
        await ctx.respond(
            embed=discord.Embed(title="🔒 Access Denied", description=tip, color=0xED4245),
            ephemeral=True,
        )
    else:
        await ctx.reply(
            embed=discord.Embed(title="🔒 Access Denied", description=tip, color=0xED4245),
            delete_after=15,
        )



async def log_action(bot, guild, action: str, mod: discord.Member, target, reason: str = None, mode: str = None):
    cfg = await get_config(guild.id)
    server_actions = {"Lock", "Unlock", "Slowmode", "Purge"}
    if action in server_actions:
        ch_id = cfg.get("server_log_ch") or cfg.get("log_ch")
    else:
        ch_id = cfg.get("mod_log_ch") or cfg.get("log_ch")

    if not ch_id:
        return
    ch = guild.get_channel(ch_id)
    if not ch:
        try:
            ch = await guild.fetch_channel(ch_id)
        except Exception:
            try:
                ch = await bot.fetch_channel(ch_id)
            except Exception:
                return

    colors = {
        "Kick": 0xFEE75C,
        "Ban": 0xED4245,
        "Unban": 0x57F287,
        "Mute": 0xF47FFF,
        "Unmute": 0x57F287,
        "Warn": 0xFFA500,
        "Lock": 0xED4245,
        "Unlock": 0x57F287,
        "Slowmode": 0x5865F2,
        "Purge": 0x57F287,
    }
    embed = discord.Embed(
        title=f"🛡️ Action: {action}",
        color=colors.get(action, 0x5865F2),
        timestamp=discord.utils.utcnow(),
    )
    if isinstance(target, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread)):
        embed.add_field(name="📁 Channel", value=f"{target.mention} (`{target.id}`)", inline=True)
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


def parse_duration(s: str) -> int:
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
    return total


class Moderation(commands.Cog):
    """🔨 Moderation tools."""

    def __init__(self, bot):
        self.bot = bot
        self.unmute_loop.start()

    def cog_unload(self):
        self.unmute_loop.cancel()

    # ── Auto-unmute loop ──────────────────────────────────────────────────────
    @tasks.loop(seconds=30)
    async def unmute_loop(self):
        now = time.time()
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
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
                    await member.timeout(None)
                except Exception:
                    pass
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "DELETE FROM mutes WHERE guild_id=? AND user_id=?",
                    (row["guild_id"], row["user_id"]),
                )
                await db.commit()

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

        # Reason check: Bot owner bypasses; all others must provide a reason
        if ctx.author.id != GLOBAL_OWNER_ID:
            if not reason or not reason.strip() or reason.strip() == "No reason provided":
                return await ctx.respond(
                    embed=discord.Embed(
                        description="❌ You must provide a **reason** to kick a member.",
                        color=0xED4245,
                    ),
                    ephemeral=True,
                )
        if not reason:
            reason = "No reason provided"

        await ctx.defer(ephemeral=False)
        if member.id == ctx.guild.owner_id:
            return await ctx.followup.send(
                embed=discord.Embed(description="❌ You cannot kick the **server owner**.", color=0xED4245),
                ephemeral=True,
            )
        if member.id == self.bot.user.id:
            return await ctx.followup.send(
                embed=discord.Embed(description="❌ I cannot kick myself.", color=0xED4245),
                ephemeral=True,
            )
        if member.id == ctx.author.id:
            return await ctx.followup.send(
                embed=discord.Embed(description="❌ You cannot kick yourself.", color=0xED4245),
                ephemeral=True,
            )
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id and ctx.author.id != GLOBAL_OWNER_ID:
            return await ctx.followup.send(
                embed=discord.Embed(
                    description=f"❌ You cannot kick {member.mention} because their highest role ({member.top_role.mention}) is equal to or higher than yours.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.followup.send(
                embed=discord.Embed(
                    title="❌ Role Hierarchy Error",
                    description=f"I cannot kick {member.mention} because their highest role ({member.top_role.mention}) is equal to or higher than my bot role ({ctx.guild.me.top_role.mention}).\n\n**To fix this:** Go to **Server Settings → Roles** and drag my bot role above their role!",
                    color=0xED4245,
                ),
                ephemeral=True,
            )
        if not ctx.guild.me.guild_permissions.kick_members:
            return await ctx.followup.send(
                embed=discord.Embed(description="❌ I do not have the **Kick Members** permission in this server.", color=0xED4245),
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
            dm_embed.set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon.url if ctx.guild.icon else None,
            )
            await member.send(embed=dm_embed)
            dm_sent = True
        except Exception:
            dm_sent = False

        try:
            await member.kick(reason=f"{reason} | Moderator: {ctx.author}")
        except discord.Forbidden:
            return await ctx.followup.send(
                embed=discord.Embed(
                    title="❌ Permission Denied",
                    description=f"Discord denied permission to kick {member.mention}. Ensure Nexus has the **Kick Members** permission and its highest role is placed above this member's role.",
                    color=0xED4245,
                )
            )
        except Exception as e:
            return await ctx.followup.send(
                embed=discord.Embed(title="❌ Kick Failed", description=f"An unexpected error occurred: `{e}`", color=0xED4245)
            )

        dm_status = "📨 Notified via DM." if dm_sent else "⚠️ Could not DM (user has DMs closed)."
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=f"**{member.mention}** (`{member}`) has been kicked from the server.\n\n**🛡️ Moderator:** {ctx.author.mention}\n**📝 Reason:** {reason}\n**📬 DM Status:** {dm_status}",
            color=0x57F287,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.followup.send(embed=embed)
        await log_action(self.bot, ctx.guild, "Kick", ctx.author, member, f"{reason} | {dm_status}")

    # ── /ban ──────────────────────────────────────────────────────────────────
    @discord.slash_command(name="ban", description="Ban a member from the server")
    @option("member", discord.Member, description="Member to ban")
    @option("reason", str, description="Reason for ban", required=False, default=None)
    @option("delete_days", int, description="Days of messages to delete (0-7)", required=False, default=0)
    async def ban(self, ctx: discord.ApplicationContext, member: discord.Member, reason: str = None, delete_days: int = 0):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)

        # Reason check: Bot owner bypasses; all others must provide a reason
        if ctx.author.id != GLOBAL_OWNER_ID:
            if not reason or not reason.strip() or reason.strip() == "No reason provided":
                return await ctx.respond(
                    embed=discord.Embed(
                        description="❌ You must provide a **reason** to ban a member.",
                        color=0xED4245,
                    ),
                    ephemeral=True,
                )
        if not reason:
            reason = "No reason provided"

        await ctx.defer(ephemeral=False)
        if member.id == ctx.guild.owner_id:
            return await ctx.followup.send(
                embed=discord.Embed(description="❌ You cannot ban the **server owner**.", color=0xED4245),
                ephemeral=True,
            )
        if member.id == self.bot.user.id:
            return await ctx.followup.send(
                embed=discord.Embed(description="❌ I cannot ban myself.", color=0xED4245),
                ephemeral=True,
            )
        if member.id == ctx.author.id:
            return await ctx.followup.send(
                embed=discord.Embed(description="❌ You cannot ban yourself.", color=0xED4245),
                ephemeral=True,
            )
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id and ctx.author.id != GLOBAL_OWNER_ID:
            return await ctx.followup.send(
                embed=discord.Embed(
                    description=f"❌ You cannot ban {member.mention} because their highest role ({member.top_role.mention}) is equal to or higher than yours.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.followup.send(
                embed=discord.Embed(
                    title="❌ Role Hierarchy Error",
                    description=f"I cannot ban {member.mention} because their highest role ({member.top_role.mention}) is equal to or higher than my bot role ({ctx.guild.me.top_role.mention}).\n\n**To fix this:** Go to **Server Settings → Roles** and drag my bot role above their role!",
                    color=0xED4245,
                ),
                ephemeral=True,
            )
        if not ctx.guild.me.guild_permissions.ban_members:
            return await ctx.followup.send(
                embed=discord.Embed(description="❌ I do not have the **Ban Members** permission in this server.", color=0xED4245),
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
            dm_embed.set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon.url if ctx.guild.icon else None,
            )
            await member.send(embed=dm_embed)
            dm_sent = True
        except Exception:
            dm_sent = False

        try:
            delete_secs = max(0, min(7, delete_days)) * 86400
            await member.ban(reason=f"{reason} | Moderator: {ctx.author}", delete_message_seconds=delete_secs)
        except discord.Forbidden:
            return await ctx.followup.send(
                embed=discord.Embed(
                    title="❌ Permission Denied",
                    description=f"Discord denied permission to ban {member.mention}. Ensure Nexus has the **Ban Members** permission and its highest role is placed above this member's role.",
                    color=0xED4245,
                )
            )
        except Exception as e:
            return await ctx.followup.send(
                embed=discord.Embed(title="❌ Ban Failed", description=f"An unexpected error occurred: `{e}`", color=0xED4245)
            )

        dm_status = "📨 Notified via DM." if dm_sent else "⚠️ Could not DM (user has DMs closed)."
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"**{member.mention}** (`{member}`) has been banned from the server.\n\n**🛡️ Moderator:** {ctx.author.mention}\n**📝 Reason:** {reason}\n**🗑️ Message History Pruned:** `{delete_days} day(s)`\n**📬 DM Status:** {dm_status}",
            color=0x57F287,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.followup.send(embed=embed)
        await log_action(self.bot, ctx.guild, "Ban", ctx.author, member, f"{reason} | {dm_status}")

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
            embed = discord.Embed(
                title="✅ Member Unbanned",
                description=f"**{user.mention}** (`{user}`) has been unbanned.\n\n**🛡️ Moderator:** {ctx.author.mention}\n**📝 Reason:** {reason}",
                color=0x57F287,
                timestamp=discord.utils.utcnow(),
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            await ctx.followup.send(embed=embed)
            await log_action(self.bot, ctx.guild, "Unban", ctx.author, user, reason)
        except discord.NotFound:
            await ctx.followup.send(embed=discord.Embed(description="❌ User not found or not currently banned.", color=0xED4245), ephemeral=True)
        except discord.Forbidden:
            await ctx.followup.send(embed=discord.Embed(description="❌ I do not have permission to unban members.", color=0xED4245), ephemeral=True)
        except ValueError:
            await ctx.followup.send(embed=discord.Embed(description="❌ Invalid user ID. Please provide a numeric Discord User ID.", color=0xED4245), ephemeral=True)
        except Exception as e:
            await ctx.followup.send(embed=discord.Embed(description=f"❌ Unban failed: `{e}`", color=0xED4245), ephemeral=True)

    # ── /mute (timeout) ───────────────────────────────────────────────────────
    @discord.slash_command(name="mute", description="Timeout a member")
    @option("member", discord.Member, description="Member to mute")
    @option("duration", str, description="Duration e.g. 10m, 1h, 1d")
    @option("reason", str, description="Reason", required=False, default="No reason provided")
    async def mute(self, ctx: discord.ApplicationContext, member: discord.Member, duration: str, reason: str = "No reason provided"):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        await ctx.defer(ephemeral=False)
        if member.id == ctx.guild.owner_id:
            return await ctx.followup.send(embed=discord.Embed(description="❌ You cannot mute the server owner.", color=0xED4245), ephemeral=True)
        if member.id == self.bot.user.id or member.id == ctx.author.id:
            return await ctx.followup.send(embed=discord.Embed(description="❌ Invalid target.", color=0xED4245), ephemeral=True)
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id and ctx.author.id != GLOBAL_OWNER_ID:
            return await ctx.followup.send(embed=discord.Embed(description="❌ You cannot mute someone with an equal or higher role than yours.", color=0xED4245), ephemeral=True)
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.followup.send(
                embed=discord.Embed(
                    title="❌ Role Hierarchy Error",
                    description=f"I cannot mute {member.mention} because their highest role is equal to or higher than my bot role.\n\n**To fix this:** Drag my bot role above their role in **Server Settings → Roles**.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )

        secs = parse_duration(duration)
        if secs < 1:
            return await ctx.followup.send(
                embed=discord.Embed(description="❌ Invalid duration format. Examples: `10m`, `1h`, `1d`, `7d`.", color=0xED4245), ephemeral=True
            )

        dm_sent = False
        try:
            dm_embed = discord.Embed(
                title="🔇 You were timed out",
                description=f"You have been timed out in **{ctx.guild.name}**.\n\n**Duration:** `{duration}`\n**Reason:** {reason}",
                color=0xF47FFF,
                timestamp=discord.utils.utcnow(),
            )
            dm_embed.set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon.url if ctx.guild.icon else None,
            )
            await member.send(embed=dm_embed)
            dm_sent = True
        except Exception:
            dm_sent = False

        from datetime import timedelta
        until = discord.utils.utcnow() + timedelta(seconds=secs)
        try:
            await member.timeout(until, reason=f"{reason} | Moderator: {ctx.author}")
        except discord.Forbidden:
            return await ctx.followup.send(embed=discord.Embed(title="❌ Permission Denied", description="Discord prevented applying timeout. Ensure Nexus has **Moderate Members** permission.", color=0xED4245))

        ends_at = time.time() + secs
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO mutes (guild_id, user_id, ends_at) VALUES (?,?,?)",
                (ctx.guild.id, member.id, ends_at),
            )
            await db.commit()

        dm_status = "📨 Notified via DM." if dm_sent else "⚠️ Could not DM (user has DMs closed)."
        await ctx.followup.send(embed=discord.Embed(
            title="🔇 Member Muted",
            description=f"**{member.mention}** (`{member}`) has been timed out for `{duration}`.\n\n**🛡️ Moderator:** {ctx.author.mention}\n**📝 Reason:** {reason}\n**📬 Status:** {dm_status}",
            color=0x57F287,
            timestamp=discord.utils.utcnow(),
        ))
        await log_action(self.bot, ctx.guild, "Mute", ctx.author, member, f"{reason} | Duration: {duration} | {dm_status}")

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
        except discord.Forbidden:
            return await ctx.followup.send(embed=discord.Embed(description="❌ I do not have permission to remove timeouts.", color=0xED4245), ephemeral=True)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM mutes WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
            await db.commit()
        await ctx.followup.send(embed=discord.Embed(
            title="🔊 Unmuted",
            description=f"**{member.mention}** (`{member}`) has been unmuted.\n\n**🛡️ Moderator:** {ctx.author.mention}\n**📝 Reason:** {reason}",
            color=0x57F287,
            timestamp=discord.utils.utcnow(),
        ))
        await log_action(self.bot, ctx.guild, "Unmute", ctx.author, member, reason)

    # ── /warn ─────────────────────────────────────────────────────────────────
    @discord.slash_command(name="warn", description="Warn a member")
    @option("member", discord.Member, description="Member to warn")
    @option("reason", str, description="Reason for warning", required=False, default=None)
    async def warn(self, ctx: discord.ApplicationContext, member: discord.Member, reason: str = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)

        # Reason check: Bot owner bypasses; all others must provide a reason
        if ctx.author.id != GLOBAL_OWNER_ID:
            if not reason or not reason.strip():
                return await ctx.respond(
                    embed=discord.Embed(
                        description="❌ You must provide a **reason** to warn a member.",
                        color=0xED4245,
                    ),
                    ephemeral=True,
                )
        if not reason:
            reason = "No reason provided"

        await ctx.defer(ephemeral=False)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO warns (guild_id, user_id, mod_id, reason, timestamp) VALUES (?,?,?,?,?)",
                (ctx.guild.id, member.id, ctx.author.id, reason, time.time()),
            )
            await db.commit()
            async with db.execute(
                "SELECT COUNT(*) FROM warns WHERE guild_id=? AND user_id=?",
                (ctx.guild.id, member.id),
            ) as cur:
                total = (await cur.fetchone())[0]

        dm_sent = False
        try:
            dm_embed = discord.Embed(
                title="⚠️ Warning Received",
                description=f"You received a warning in **{ctx.guild.name}**.\n\n**Reason:** {reason}\n**Total Warnings:** {total}",
                color=0xFEE75C,
                timestamp=discord.utils.utcnow(),
            )
            dm_embed.set_author(
                name=ctx.guild.name,
                icon_url=ctx.guild.icon.url if ctx.guild.icon else None,
            )
            await member.send(embed=dm_embed)
            dm_sent = True
        except Exception:
            dm_sent = False

        dm_status = "📨 Notified via DM." if dm_sent else "⚠️ Could not DM (user has DMs closed)."
        await ctx.followup.send(embed=discord.Embed(
            title="⚠️ Warning Issued",
            description=f"**{member.mention}** (`{member}`) has been warned.\n\n**🛡️ Moderator:** {ctx.author.mention}\n**📝 Reason:** {reason}\n**📊 Total Warnings:** `{total}`\n**📬 DM Status:** {dm_status}",
            color=0xFEE75C,
            timestamp=discord.utils.utcnow(),
        ))
        await log_action(self.bot, ctx.guild, "Warn", ctx.author, member, f"{reason} | Warning #{total} | {dm_status}")

    # ── /warnings ─────────────────────────────────────────────────────────────
    @discord.slash_command(name="warnings", description="View warnings for a member")
    @option("member", discord.Member, description="Member to check")
    async def warnings(self, ctx: discord.ApplicationContext, member: discord.Member):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM warns WHERE guild_id=? AND user_id=? ORDER BY timestamp DESC",
                (ctx.guild.id, member.id),
            ) as cur:
                rows = await cur.fetchall()

        embed = discord.Embed(
            title=f"⚠️ Warnings — {member.display_name}",
            description=f"**Total: {len(rows)}**",
            color=0xFEE75C,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        for i, r in enumerate(rows[:10], 1):
            mod = ctx.guild.get_member(r["mod_id"])
            ts = int(r["timestamp"])
            embed.add_field(
                name=f"#{i} — <t:{ts}:d>",
                value=f"**Reason:** {r['reason']}\n**By:** {mod.mention if mod else 'Unknown'}",
                inline=False,
            )
        await ctx.respond(embed=embed, ephemeral=True)

    # ── /clearwarns ───────────────────────────────────────────────────────────
    @discord.slash_command(name="clearwarns", description="Clear all warnings for a member")
    @option("member", discord.Member, description="Member to clear warns for")
    async def clearwarns(self, ctx: discord.ApplicationContext, member: discord.Member):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM warns WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id)
            )
            await db.commit()
        await ctx.respond(embed=discord.Embed(
            title="🗑️ Warnings Cleared",
            description=f"All warnings for **{member}** have been cleared.",
            color=0x57F287,
        ))

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
        await ctx.followup.send(
            embed=discord.Embed(
                description=f"🗑️ Deleted **{deleted_count}** message(s).",
                color=0x57F287,
            ),
            ephemeral=True,
        )

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
    @discord.slash_command(name="lock", description="Lock a channel")
    @option("channel", discord.TextChannel, description="Channel to lock (defaults to current)", required=False, default=None)
    @option("reason", str, description="Reason for lock", required=False, default="No reason provided")
    async def lock(self, ctx: discord.ApplicationContext, channel: discord.TextChannel = None, reason: str = "No reason provided"):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        await ctx.defer(ephemeral=False)
        ch = channel or ctx.channel
        me = ctx.guild.me
        perms = ch.permissions_for(me)
        if not perms.manage_roles and not perms.manage_channels:
            return await ctx.followup.send(
                embed=discord.Embed(
                    title="❌ Missing Bot Permission",
                    description=f"I need **Manage Roles** or **Manage Channels** permission in {ch.mention} to update its permissions.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )

        overwrite = ch.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        overwrite.send_messages_in_threads = False
        overwrite.create_public_threads = False
        overwrite.create_private_threads = False
        overwrite.add_reactions = False

        try:
            await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=f"Locked by {ctx.author}: {reason}")
        except discord.Forbidden:
            return await ctx.followup.send(
                embed=discord.Embed(
                    title="❌ Permission Denied",
                    description=f"Discord prevented locking {ch.mention}. Ensure Nexus has **Manage Channels** / **Manage Roles** and its role is high in the hierarchy.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )
        except Exception as e:
            return await ctx.followup.send(
                embed=discord.Embed(title="❌ Lock Failed", description=f"An error occurred: `{e}`", color=0xED4245),
                ephemeral=True,
            )

        cfg = await get_config(ctx.guild.id)
        bot_role_id = cfg.get("bot_role_id")
        if bot_role_id:
            bot_role = ctx.guild.get_role(bot_role_id)
            if bot_role:
                try:
                    staff_ow = ch.overwrites_for(bot_role)
                    staff_ow.send_messages = True
                    staff_ow.send_messages_in_threads = True
                    await ch.set_permissions(bot_role, overwrite=staff_ow)
                except Exception:
                    pass

        lock_notice = discord.Embed(
            title="🔒 Channel Locked",
            description=f"This channel has been locked by {ctx.author.mention}.\n\n**Reason:** {reason}",
            color=0xED4245,
            timestamp=discord.utils.utcnow(),
        )
        lock_notice.set_footer(text="Nexus Security")
        try:
            await ch.send(embed=lock_notice)
        except Exception:
            pass

        await ctx.followup.send(
            embed=discord.Embed(
                title="🔒 Channel Locked Successfully",
                description=f"{ch.mention} has been locked for `@everyone`.\n**Reason:** {reason}",
                color=0x57F287,
            )
        )
        await log_action(self.bot, ctx.guild, "Lock", ctx.author, ch, reason)

    @discord.slash_command(name="unlock", description="Unlock a channel")
    @option("channel", discord.TextChannel, description="Channel to unlock (defaults to current)", required=False, default=None)
    async def unlock(self, ctx: discord.ApplicationContext, channel: discord.TextChannel = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        await ctx.defer(ephemeral=False)
        ch = channel or ctx.channel
        me = ctx.guild.me
        perms = ch.permissions_for(me)
        if not perms.manage_roles and not perms.manage_channels:
            return await ctx.followup.send(
                embed=discord.Embed(
                    title="❌ Missing Bot Permission",
                    description=f"I need **Manage Roles** or **Manage Channels** permission in {ch.mention} to update its permissions.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )

        overwrite = ch.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        overwrite.send_messages_in_threads = None
        overwrite.create_public_threads = None
        overwrite.create_private_threads = None
        overwrite.add_reactions = None

        try:
            await ch.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=f"Unlocked by {ctx.author}")
        except discord.Forbidden:
            return await ctx.followup.send(
                embed=discord.Embed(
                    title="❌ Permission Denied",
                    description=f"Discord prevented unlocking {ch.mention}. Ensure Nexus has **Manage Channels** / **Manage Roles**.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )
        except Exception as e:
            return await ctx.followup.send(
                embed=discord.Embed(title="❌ Unlock Failed", description=f"An error occurred: `{e}`", color=0xED4245),
                ephemeral=True,
            )

        unlock_notice = discord.Embed(
            title="🔓 Channel Unlocked",
            description=f"This channel has been unlocked by {ctx.author.mention}. Normal chatting has resumed.",
            color=0x57F287,
            timestamp=discord.utils.utcnow(),
        )
        unlock_notice.set_footer(text="Nexus Security")
        try:
            await ch.send(embed=unlock_notice)
        except Exception:
            pass

        await ctx.followup.send(
            embed=discord.Embed(
                title="🔓 Channel Unlocked Successfully",
                description=f"{ch.mention} has been restored to default permissions.",
                color=0x57F287,
            )
        )
        await log_action(self.bot, ctx.guild, "Unlock", ctx.author, ch)

    # ── Prefix shortcuts ──────────────────────────────────────────────────────
    @commands.command(name="kick")
    async def prefix_kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        if ctx.author.id != GLOBAL_OWNER_ID:
            if not reason or not reason.strip() or reason.strip() == "No reason provided":
                return await ctx.reply("❌ You must provide a **reason** to kick a member.")
        if not reason:
            reason = "No reason provided"
        try:
            await member.kick(reason=f"{reason} | Mod: {ctx.author}")
            mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
            await log_action(self.bot, ctx.guild, "Kick", ctx.author, member, reason, mode=mode)
            await ctx.reply(f"✅ Kicked **{member}**.")
        except Exception as e:
            await ctx.reply(f"❌ Failed to kick {member}: `{e}`")

    @commands.command(name="ban")
    async def prefix_ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        if ctx.author.id != GLOBAL_OWNER_ID:
            if not reason or not reason.strip() or reason.strip() == "No reason provided":
                return await ctx.reply("❌ You must provide a **reason** to ban a member.")
        if not reason:
            reason = "No reason provided"
        try:
            await member.ban(reason=f"{reason} | Mod: {ctx.author}")
            mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
            await log_action(self.bot, ctx.guild, "Ban", ctx.author, member, reason, mode=mode)
            await ctx.reply(f"✅ Banned **{member}**.")
        except Exception as e:
            await ctx.reply(f"❌ Failed to ban {member}: `{e}`")

    @commands.command(name="purge")
    async def prefix_purge(self, ctx: commands.Context, amount: int = 10):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        deleted = await ctx.channel.purge(limit=min(amount, 100) + 1)
        deleted_count = max(0, len(deleted) - 1)
        reason = f"Purged {deleted_count} message(s) in {ctx.channel.mention}"
        mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
        await log_action(self.bot, ctx.guild, "Purge", ctx.author, ctx.channel, reason, mode=mode)
        await ctx.send(f"🗑️ Deleted {deleted_count} messages.", delete_after=5)

    @commands.command(name="mute", aliases=["timeout"])
    async def prefix_mute(self, ctx: commands.Context, member: discord.Member, duration: str = "10m", *, reason: str = None):
        """n!mute @member [duration] [reason]"""
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        secs = parse_duration(duration)
        if secs < 10:
            return await ctx.reply("❌ Invalid duration (minimum 10s, e.g. `10m`, `1h`, `1d`).")
        if not reason:
            reason = "No reason provided"
        until = discord.utils.utcnow() + datetime.timedelta(seconds=secs)
        try:
            await member.timeout(until, reason=reason)
            mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
            await log_action(self.bot, ctx.guild, "Mute", ctx.author, member, f"{reason} ({duration})", mode=mode)
            await ctx.reply(f"🔇 Timed out **{member}** for `{duration}`.")
        except Exception as e:
            await ctx.reply(f"❌ Failed to mute: `{e}`")

    @commands.command(name="unmute", aliases=["untimeout"])
    async def prefix_unmute(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        """n!unmute @member [reason]"""
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        reason = reason or "No reason provided"
        try:
            await member.remove_timeout(reason=reason)
            mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
            await log_action(self.bot, ctx.guild, "Unmute", ctx.author, member, reason, mode=mode)
            await ctx.reply(f"🔊 Removed timeout from **{member}**.")
        except Exception as e:
            await ctx.reply(f"❌ Failed to unmute: `{e}`")

    @commands.command(name="warn")
    async def prefix_warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        """n!warn @member <reason>"""
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        if ctx.author.id != GLOBAL_OWNER_ID:
            if not reason or not reason.strip() or reason.strip() == "No reason provided":
                return await ctx.reply("❌ You must provide a **reason** to warn a member.")
        reason = reason or "No reason provided"
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO warns (guild_id, user_id, mod_id, reason, timestamp) VALUES (?,?,?,?,?)",
                (ctx.guild.id, member.id, ctx.author.id, reason, time.time()),
            )
            await db.commit()
        mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
        await log_action(self.bot, ctx.guild, "Warn", ctx.author, member, reason, mode=mode)
        await ctx.reply(f"⚠️ Warned **{member}** for: `{reason}`")

    @commands.command(name="warnings", aliases=["warns"])
    async def prefix_warnings(self, ctx: commands.Context, member: discord.Member):
        """n!warnings @member"""
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM warns WHERE guild_id=? AND user_id=? ORDER BY id DESC",
                (ctx.guild.id, member.id),
            ) as cur:
                rows = await cur.fetchall()
        if not rows:
            return await ctx.reply(f"ℹ️ **{member}** has no warnings.")
        embed = discord.Embed(title=f"⚠️ Warnings for {member}", color=0xFEE75C)
        for r in rows[:10]:
            embed.add_field(
                name=f"Case #{r['id']} — <t:{int(r['timestamp'])}:R>",
                value=f"Mod: <@{r['mod_id']}>\nReason: {r['reason']}",
                inline=False,
            )
        embed.set_footer(text=f"Total: {len(rows)} warnings")
        await ctx.reply(embed=embed)

    @commands.command(name="lock")
    async def prefix_lock(self, ctx: commands.Context, channel: discord.TextChannel = None, *, reason: str = "No reason provided"):
        """n!lock [#channel] [reason]"""
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        ch = channel or ctx.channel
        default_role = ctx.guild.default_role
        perms = ch.overwrites_for(default_role)
        perms.send_messages = False
        await ch.set_permissions(default_role, overwrite=perms, reason=f"Locked by {ctx.author}: {reason}")
        mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
        await log_action(self.bot, ctx.guild, "Lock", ctx.author, ch, reason, mode=mode)
        await ctx.reply(f"🔒 Locked {ch.mention}.")

    @commands.command(name="unlock")
    async def prefix_unlock(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """n!unlock [#channel]"""
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        ch = channel or ctx.channel
        default_role = ctx.guild.default_role
        perms = ch.overwrites_for(default_role)
        perms.send_messages = None
        await ch.set_permissions(default_role, overwrite=perms, reason=f"Unlocked by {ctx.author}")
        mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
        await log_action(self.bot, ctx.guild, "Unlock", ctx.author, ch, mode=mode)
        await ctx.reply(f"🔓 Unlocked {ch.mention}.")

    @commands.command(name="slowmode")
    async def prefix_slowmode(self, ctx: commands.Context, seconds: int = 0, channel: discord.TextChannel = None):
        """n!slowmode <seconds> [#channel]"""
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        ch = channel or ctx.channel
        seconds = max(0, min(21600, seconds))
        await ch.edit(slowmode_delay=seconds)
        mode = f"🏷️ Prefix (`{ctx.prefix}`)" if (ctx.prefix and ctx.prefix.strip()) else "⚡ No Prefix"
        await log_action(self.bot, ctx.guild, "Slowmode", ctx.author, ch, f"Set to {seconds}s", mode=mode)
        await ctx.reply(f"⏱️ Slowmode in {ch.mention} set to `{seconds}s`." if seconds else f"⏱️ Slowmode in {ch.mention} disabled.")


def setup(bot):
    bot.add_cog(Moderation(bot))
