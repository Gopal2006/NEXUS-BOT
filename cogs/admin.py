"""
Admin Cog — bot-role management, server configuration, welcome/leave setup.
Commands: /set-botrole, /remove-botrole, /set-welcome, /set-leave,
          /set-log, /config, /setupbot, /set-status, /serverstats
"""

import discord
from discord.ext import commands
from discord import option
import aiosqlite
from pathlib import Path
import time

DB_PATH = Path("nexus.db")
GLOBAL_OWNER_ID = 1201050377911554061
SUPPORT_SERVER  = "https://discord.gg/PLACEHOLDER"  # Update when ready

_BOT_START_TIME = time.time()  # approximate uptime reference

async def get_config(guild_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            await db.execute("INSERT INTO guild_config (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
            async with db.execute("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)) as cur:
                row = await cur.fetchone()
        return dict(row)

async def set_config(guild_id: int, **kwargs):
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [guild_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE guild_config SET {sets} WHERE guild_id = ?", vals)
        await db.commit()


# ── Shared permission helper ──────────────────────────────────────────────────
async def _is_bot_admin(ctx_or_author, guild) -> bool:
    """True only for global owner, server owner, or member with the bot-role.
    Administrators without the bot-role are NOT granted access."""
    if guild is None:
        return False
    author = ctx_or_author if isinstance(ctx_or_author, discord.Member) else getattr(ctx_or_author, "author", ctx_or_author)
    if author.id == GLOBAL_OWNER_ID:
        return True
    if author.id == guild.owner_id:
        return True
    cfg = await get_config(guild.id)
    role_id = cfg.get("bot_role_id")
    if role_id:
        member = guild.get_member(author.id) or author
        if hasattr(member, "roles"):
            return any(r.id == role_id for r in member.roles)
    return False


# ── Shared: ephemeral "no permission" response ────────────────────────────────
async def _no_perm(ctx: discord.ApplicationContext):
    if ctx.guild is None:
        return await ctx.respond(
            embed=discord.Embed(
                title="🔒 Access Denied",
                description="Commands can only be used inside a server.",
                color=0xED4245,
            ),
            ephemeral=True,
        )

    cfg = await get_config(ctx.guild.id)
    role_id = cfg.get("bot_role_id")
    bot_role = ctx.guild.get_role(role_id) if role_id else None

    if bot_role:
        tip = (
            f"You need the {bot_role.mention} role to use bot commands.\n"
            "Please ask the **server owner** to grant you this role."
        )
    else:
        tip = (
            "You don't have access to bot commands.\n"
            "Please ask the **server owner** to assign you the bot-role using `/set-botrole`."
        )

    await ctx.respond(
        embed=discord.Embed(
            title="🔒 Access Denied",
            description=tip,
            color=0xED4245,
        ),
        ephemeral=True,
    )


class Admin(commands.Cog):
    """⚙️ Server configuration and bot-role management."""

    def __init__(self, bot):
        self.bot = bot

    # ── /set-botrole ──────────────────────────────────────────────────────────
    @discord.slash_command(name="set-botrole", description="Set which role can control the bot")
    @option("role", discord.Role, description="Role that will have full bot access")
    async def set_botrole(self, ctx: discord.ApplicationContext, role: discord.Role):
        # Only server owner (or global bot owner) can configure the bot-role
        if ctx.author.id not in (ctx.guild.owner_id, GLOBAL_OWNER_ID):
            return await ctx.respond(
                embed=discord.Embed(
                    title="🔒 Server Owner Only",
                    description="Only the **server owner** can assign the bot-role.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )
        await set_config(ctx.guild.id, bot_role_id=role.id)
        embed = discord.Embed(
            title="✅ Bot-Role Configured",
            description=(
                f"Members with {role.mention} now have full bot management access.\n\n"
                "They can use all bot commands except `/set-botrole` and `/remove-botrole`, "
                "which remain exclusive to the server owner."
            ),
            color=0x57F287,
        )
        embed.set_footer(text=f"Set by {ctx.author}")
        await ctx.respond(embed=embed)

    # ── /remove-botrole ───────────────────────────────────────────────────────
    @discord.slash_command(name="remove-botrole", description="Remove the bot role restriction")
    async def remove_botrole(self, ctx: discord.ApplicationContext):
        if ctx.author.id not in (ctx.guild.owner_id, GLOBAL_OWNER_ID):
            return await ctx.respond(
                embed=discord.Embed(
                    title="🔒 Server Owner Only",
                    description="Only the **server owner** can remove the bot-role.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )
        await set_config(ctx.guild.id, bot_role_id=None)
        await ctx.respond(
            embed=discord.Embed(
                title="✅ Bot-Role Removed",
                description=(
                    "The bot-role restriction has been lifted.\n"
                    "Only you (the server owner) can now use bot commands until a new bot-role is set."
                ),
                color=0x57F287,
            )
        )

    # ── /set-welcome ──────────────────────────────────────────────────────────
    @discord.slash_command(name="set-welcome", description="Set the welcome channel and message")
    @option("channel", discord.TextChannel, description="Channel to send welcome messages in")
    @option("message", str, description="Welcome message — use {mention} {name} {guild}", required=False, default=None)
    async def set_welcome(self, ctx: discord.ApplicationContext, channel: discord.TextChannel, message: str = None):
        if not await _is_bot_admin(ctx, ctx.guild):
            return await _no_perm(ctx)
        kwargs = dict(welcome_ch=channel.id)
        if message:
            kwargs["welcome_msg"] = message
        await set_config(ctx.guild.id, **kwargs)
        await ctx.respond(embed=discord.Embed(
            title="✅ Welcome Channel Set",
            description=(
                f"Welcome messages will appear in {channel.mention}.\n\n"
                "**Available placeholders:**\n"
                "`{mention}` — member mention\n"
                "`{name}` — username\n"
                "`{guild}` — server name"
            ),
            color=0x57F287,
        ))

    # ── /set-leave ────────────────────────────────────────────────────────────
    @discord.slash_command(name="set-leave", description="Set the leave channel and message")
    @option("channel", discord.TextChannel, description="Channel to send leave messages in")
    @option("message", str, description="Leave message — use {mention} {name} {guild}", required=False, default=None)
    async def set_leave(self, ctx: discord.ApplicationContext, channel: discord.TextChannel, message: str = None):
        if not await _is_bot_admin(ctx, ctx.guild):
            return await _no_perm(ctx)
        kwargs = dict(leave_ch=channel.id)
        if message:
            kwargs["leave_msg"] = message
        await set_config(ctx.guild.id, **kwargs)
        await ctx.respond(embed=discord.Embed(
            title="✅ Leave Channel Set",
            description=(
                f"Leave messages will appear in {channel.mention}.\n\n"
                "**Available placeholders:**\n"
                "`{mention}` — member mention\n"
                "`{name}` — username\n"
                "`{guild}` — server name"
            ),
            color=0x57F287,
        ))

    # ── /set-log ──────────────────────────────────────────────────────────────
    @discord.slash_command(name="set-log", description="Set the moderation log channel")
    @option("channel", discord.TextChannel, description="Channel to send mod logs")
    async def set_log(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        if not await _is_bot_admin(ctx, ctx.guild):
            return await _no_perm(ctx)
        await set_config(ctx.guild.id, log_ch=channel.id, mod_log_ch=channel.id)
        await ctx.respond(embed=discord.Embed(
            title="✅ Log Channel Set",
            description=f"Moderation logs will appear in {channel.mention}.",
            color=0x57F287,
        ))

    # ── /set-cmdlog ───────────────────────────────────────────────────────────
    @discord.slash_command(name="set-cmdlog", description="Set the channel for prefix and no-prefix command audit logs")
    @option("channel", discord.TextChannel, description="Channel to send command execution logs")
    async def set_cmdlog(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        if not await _is_bot_admin(ctx, ctx.guild):
            return await _no_perm(ctx)
        await set_config(ctx.guild.id, cmd_log_ch=channel.id)
        await ctx.respond(embed=discord.Embed(
            title="✅ Command Log Channel Set",
            description=f"Prefix and non-prefix command audit logs will appear in {channel.mention}.",
            color=0x57F287,
        ))

    # ── /config ───────────────────────────────────────────────────────────────
    @discord.slash_command(name="config", description="View the server configuration")
    async def config(self, ctx: discord.ApplicationContext):
        if not await _is_bot_admin(ctx, ctx.guild):
            return await _no_perm(ctx)
        cfg = await get_config(ctx.guild.id)
        g   = ctx.guild

        def ch(id_):
            c = g.get_channel(id_) if id_ else None
            return c.mention if c else "*not set*"

        def role(id_):
            r = g.get_role(id_) if id_ else None
            return r.mention if r else "*not set*"

        embed = discord.Embed(
            title=f"⚙️ {g.name} — Configuration",
            color=0x5865F2,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="🔧 Bot-Role",            value=role(cfg.get("bot_role_id")),                      inline=True)
        embed.add_field(name="🎫 Ticket Role",          value=role(cfg.get("ticket_role_id")),                   inline=True)
        embed.add_field(name="\u200b",                   value="\u200b",                                          inline=True)
        embed.add_field(name="👋 Welcome Channel",      value=ch(cfg.get("welcome_ch")),                          inline=True)
        embed.add_field(name="🚪 Leave Channel",         value=ch(cfg.get("leave_ch")),                            inline=True)
        embed.add_field(name="🔨 Mod Log",              value=ch(cfg.get("mod_log_ch") or cfg.get("log_ch")),     inline=True)
        embed.add_field(name="📋 Server Log",           value=ch(cfg.get("server_log_ch")),                      inline=True)
        embed.add_field(name="📨 Activity Log",         value=ch(cfg.get("activity_log_ch")),                    inline=True)
        embed.add_field(name="⌨️ Command Log",          value=ch(cfg.get("cmd_log_ch") or cfg.get("activity_log_ch")), inline=True)
        embed.add_field(name="💬 Welcome Message",      value=f"`{cfg['welcome_msg']}`",                          inline=False)
        embed.add_field(name="💬 Leave Message",        value=f"`{cfg['leave_msg']}`",                            inline=False)
        embed.set_thumbnail(url=g.icon.url if g.icon else None)
        embed.set_footer(text=f"Server ID: {g.id}")
        await ctx.respond(embed=embed, ephemeral=True)

    # ── /serverstats ──────────────────────────────────────────────────────────
    @discord.slash_command(name="serverstats", description="View server statistics and bot status")
    async def serverstats(self, ctx: discord.ApplicationContext):
        if not await _is_bot_admin(ctx, ctx.guild):
            return await _no_perm(ctx)
        g   = ctx.guild
        cfg = await get_config(g.id)
        bot = self.bot

        def ch(id_):
            c = g.get_channel(id_) if id_ else None
            return c.mention if c else "*not set*"

        def role(id_):
            r = g.get_role(id_) if id_ else None
            return r.mention if r else "*not set*"

        # Member counts
        total_members = g.member_count
        humans        = sum(1 for m in g.members if not m.bot)
        bots          = total_members - humans
        online        = sum(
            1 for m in g.members
            if m.status != discord.Status.offline and not m.bot
        )

        # Channel counts
        text_ch    = len(g.text_channels)
        voice_ch   = len(g.voice_channels)
        categories = len(g.categories)
        threads    = len(g.threads)

        # Roles
        role_count = len(g.roles) - 1  # exclude @everyone


        embed = discord.Embed(
            title=f"📊 {g.name} — Server Statistics",
            color=0x5865F2,
            timestamp=discord.utils.utcnow(),
        )
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)

        # ── Server overview ────────────────────────────────────────────────────
        embed.add_field(
            name="🌐 Server Info",
            value=(
                f"**Owner:** {g.owner.mention if g.owner else '*unknown*'}\n"
                f"**Created:** <t:{int(g.created_at.timestamp())}:D>\n"
                f"**Server ID:** `{g.id}`\n"
                f"**Verification:** `{str(g.verification_level).title()}`\n"
                f"**Boost Level:** `Tier {g.premium_tier}` ({g.premium_subscription_count} boosts)"
            ),
            inline=False,
        )

        # ── Members ────────────────────────────────────────────────────────────
        embed.add_field(
            name="👥 Members",
            value=(
                f"**Total:** `{total_members}`\n"
                f"**Humans:** `{humans}`\n"
                f"**Bots:** `{bots}`\n"
                f"**Online:** `{online}`"
            ),
            inline=True,
        )

        # ── Channels ───────────────────────────────────────────────────────────
        embed.add_field(
            name="💬 Channels",
            value=(
                f"**Text:** `{text_ch}`\n"
                f"**Voice:** `{voice_ch}`\n"
                f"**Categories:** `{categories}`\n"
                f"**Threads:** `{threads}`"
            ),
            inline=True,
        )

        # ── Roles ──────────────────────────────────────────────────────────────
        embed.add_field(
            name="🏷️ Roles",
            value=f"**Total:** `{role_count}`",
            inline=True,
        )

        # ── Bot config ─────────────────────────────────────────────────────────
        embed.add_field(
            name="🤖 Bot Configuration",
            value=(
                f"**Bot-Role:** {role(cfg.get('bot_role_id'))}\n"
                f"**Ticket-Role:** {role(cfg.get('ticket_role_id'))}\n"
                f"**Mod Log:** {ch(cfg.get('mod_log_ch') or cfg.get('log_ch'))}\n"
                f"**Server Log:** {ch(cfg.get('server_log_ch'))}\n"
                f"**Activity Log:** {ch(cfg.get('activity_log_ch'))}\n"
                f"**Command Log:** {ch(cfg.get('cmd_log_ch') or cfg.get('activity_log_ch'))}\n"
                f"**Welcome Ch:** {ch(cfg.get('welcome_ch'))}\n"
                f"**Leave Ch:** {ch(cfg.get('leave_ch'))}"
            ),
            inline=False,
        )

        embed.set_footer(text=f"Nexus  •  Requested by {ctx.author.display_name}")
        await ctx.respond(embed=embed, ephemeral=True)

    # ── /setupbot ─────────────────────────────────────────────────────────────
    @discord.slash_command(name="setupbot", description="Create log channels and set up the bot")
    async def setupbot(self, ctx: discord.ApplicationContext):
        if not await _is_bot_admin(ctx, ctx.guild):
            return await _no_perm(ctx)

        await ctx.defer(ephemeral=False)
        guild = ctx.guild
        me    = guild.me

        if not me.guild_permissions.manage_channels:
            return await ctx.followup.send(
                embed=discord.Embed(
                    title="❌ Missing Permission",
                    description=(
                        "I need the **Manage Channels** permission to create log channels.\n"
                        "Please grant it in **Server Settings → Roles** and try again."
                    ),
                    color=0xED4245,
                )
            )

        cfg           = await get_config(guild.id)
        bot_role_id   = cfg.get("bot_role_id")
        bot_role      = guild.get_role(bot_role_id) if bot_role_id else None
        ticket_role_id = cfg.get("ticket_role_id")
        ticket_role   = guild.get_role(ticket_role_id) if ticket_role_id else None

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
                    reason=f"Nexus /setupbot by {ctx.author}",
                )

            async def get_or_make_channel(name, topic, extra_role=None):
                existing = discord.utils.get(category.text_channels, name=name) or \
                           discord.utils.get(guild.text_channels, name=name)
                if existing:
                    return existing
                ow = dict(base_overwrites)
                if extra_role:
                    ow[extra_role] = discord.PermissionOverwrite(
                        view_channel=True, read_messages=True, read_message_history=True, send_messages=False,
                    )
                return await guild.create_text_channel(
                    name=name, category=category, overwrites=ow, topic=topic,
                    reason=f"Nexus /setupbot by {ctx.author}",
                )

            mod_ch      = await get_or_make_channel("🔒・mod-logs",      "Moderation audit — Kicks, Bans, Timeouts, Warnings")
            server_ch   = await get_or_make_channel("🔒・server-logs",   "Server audit — Locks, Unlocks, Slowmode, Purges")
            activity_ch = await get_or_make_channel("🔒・activity-logs", "Staff DMs, Ticket events, Giveaways", extra_role=ticket_role)

        except discord.Forbidden:
            return await ctx.followup.send(
                embed=discord.Embed(
                    title="❌ Permission Error",
                    description="Discord blocked channel creation. Make sure Nexus's role is above others in the role hierarchy.",
                    color=0xED4245,
                )
            )

        await set_config(
            guild.id,
            log_ch=mod_ch.id, mod_log_ch=mod_ch.id,
            server_log_ch=server_ch.id, activity_log_ch=activity_ch.id,
            cmd_log_ch=activity_ch.id,
        )

        # Welcome messages in each log channel
        await mod_ch.send(embed=discord.Embed(
            title="🛡️ Moderation Log Channel — Active",
            description="Records: Kicks · Bans · Unbans · Timeouts · Warnings",
            color=0xED4245, timestamp=discord.utils.utcnow(),
        ).set_footer(text="Nexus  •  Mod Audit"))

        await server_ch.send(embed=discord.Embed(
            title="📋 Server Log Channel — Active",
            description="Records: Channel Locks/Unlocks · Slowmode · Message Purges",
            color=0x5865F2, timestamp=discord.utils.utcnow(),
        ).set_footer(text="Nexus  •  Server Audit"))

        await activity_ch.send(embed=discord.Embed(
            title="📨 Activity Log Channel — Active",
            description="Records: Staff DMs · Support Tickets · Giveaways",
            color=0x57F287, timestamp=discord.utils.utcnow(),
        ).set_footer(text="Nexus  •  Activity Audit"))

        reply = discord.Embed(
            title="🚀 Nexus Setup Complete",
            description=(
                f"Three private audit log channels have been created:\n\n"
                f"🔨 **Mod Logs:** {mod_ch.mention}\n"
                f"📋 **Server Logs:** {server_ch.mention}\n"
                f"📨 **Activity Logs:** {activity_ch.mention}\n\n"
                f"🔧 **Bot-Role:** {bot_role.mention if bot_role else '*Not set — use `/set-botrole`*'}\n"
                f"🎫 **Ticket-Role:** {ticket_role.mention if ticket_role else '*Not set — use `/ticket set-role`*'}\n\n"
                "All channels are private (`@everyone` cannot view them)."
            ),
            color=0x57F287,
            timestamp=discord.utils.utcnow(),
        )
        if guild.icon:
            reply.set_thumbnail(url=guild.icon.url)
        reply.set_footer(text="Nexus System", icon_url=me.display_avatar.url)
        await ctx.followup.send(embed=reply)

    # ── /set-status ───────────────────────────────────────────────────────────
    @discord.slash_command(name="set-status", description="Set the bot presence status")
    @option("status",        str, description="Presence state",   choices=["dnd", "online", "idle", "invisible"], required=False, default="dnd")
    @option("activity_type", str, description="Activity type",    choices=["watching", "playing", "listening", "competing"], required=False, default="watching")
    @option("activity_text", str, description="Status text",      required=False, default="over the server")
    async def set_status(
        self,
        ctx: discord.ApplicationContext,
        status: str = "dnd",
        activity_type: str = "watching",
        activity_text: str = "over the server",
    ):
        # Bot-owner exclusive
        if ctx.author.id != GLOBAL_OWNER_ID and not await self.bot.is_owner(ctx.author):
            return await ctx.respond(
                embed=discord.Embed(
                    title="🔒 Access Denied",
                    description="You do not have permission to use this command.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )

        status_map = {
            "dnd": discord.Status.dnd, "online": discord.Status.online,
            "idle": discord.Status.idle, "invisible": discord.Status.invisible,
        }
        act_map = {
            "watching": discord.ActivityType.watching, "playing": discord.ActivityType.playing,
            "listening": discord.ActivityType.listening, "competing": discord.ActivityType.competing,
        }

        await self.bot.change_presence(
            status=status_map.get(status.lower(), discord.Status.dnd),
            activity=discord.Activity(
                type=act_map.get(activity_type.lower(), discord.ActivityType.watching),
                name=activity_text,
            ),
        )

        status_labels = {
            "dnd": "🔴 Do Not Disturb", "online": "🟢 Online",
            "idle": "🟡 Idle", "invisible": "⚪ Invisible",
        }
        await ctx.respond(
            embed=discord.Embed(
                title="✅ Bot Presence Updated",
                description=(
                    f"**Status:** {status_labels.get(status.lower(), status)}\n"
                    f"**Activity:** {activity_type.capitalize()} `{activity_text}`"
                ),
                color=0xED4245 if status == "dnd" else 0x57F287,
            )
        )


def setup(bot):
    bot.add_cog(Admin(bot))
