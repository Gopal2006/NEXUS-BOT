"""
Admin Cog — bot-role management, server configuration, welcome/leave setup.
Commands: /set-botrole, /remove-botrole, /set-welcome, /set-leave,
          /set-log, /config, /setupbot, /set-status, /serverstats
"""

import discord
from discord.ext import commands
from discord import option
import time
from pathlib import Path

from core.config import is_bot_owner, SUPPORT_SERVER
from core.permissions import has_tier_permission, send_no_permission
from db.database import get_config, set_config

_BOT_START_TIME = time.time()  # approximate uptime reference

async def _is_bot_admin(ctx_or_author, guild) -> bool:
    return await has_tier_permission(ctx_or_author, tier="staff")

async def _no_perm(ctx: discord.ApplicationContext):
    return await send_no_permission(ctx)



class Admin(commands.Cog):
    """⚙️ Server configuration and bot-role management."""

    def __init__(self, bot):
        self.bot = bot

    # ── /set-botrole ──────────────────────────────────────────────────────────
    @discord.slash_command(name="set-botrole", description="Set which role can control the bot")
    @option("role", discord.Role, description="Role that will have full bot access")
    async def set_botrole(self, ctx: discord.ApplicationContext, role: discord.Role):
        # Only server owner (or global bot owner) can configure the bot-role
        if ctx.author.id != ctx.guild.owner_id and not is_bot_owner(ctx.author.id):
            return await ctx.respond(
                embed=discord.Embed(
                    title="🔒 Server Owner Only",
                    description="Only the **server owner** can assign the bot-role.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )

        # Check if a bot role is already configured
        cfg = await get_config(ctx.guild.id)
        existing_bot_role_id = cfg.get("bot_role_id")
        if existing_bot_role_id:
            existing_role = ctx.guild.get_role(existing_bot_role_id)
            existing_mention = existing_role.mention if existing_role else f"`ID: {existing_bot_role_id}`"
            return await ctx.respond(
                embed=discord.Embed(
                    title="⚠️ Bot-Role Already Configured",
                    description=(
                        f"A Bot-Role is already set to {existing_mention}.\n\n"
                        "To change it, please run `/remove-botrole` first to remove the current role before assigning a new one."
                    ),
                    color=0xFEE75C,
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
        if ctx.author.id != ctx.guild.owner_id and not is_bot_owner(ctx.author.id):
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

    # ── /set-ticketrole ───────────────────────────────────────────────────────
    @discord.slash_command(name="set-ticketrole", description="Set which role manages support tickets (Server Owner only)")
    @option("role", discord.Role, description="Staff role to assign for ticket support")
    async def set_ticketrole(self, ctx: discord.ApplicationContext, role: discord.Role):
        if ctx.author.id != ctx.guild.owner_id and not is_bot_owner(ctx.author.id):
            return await ctx.respond(
                embed=discord.Embed(
                    title="🔒 Server Owner Only",
                    description="Only the **server owner** can assign the ticket support staff role.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )
        await set_config(ctx.guild.id, ticket_role_id=role.id)
        embed = discord.Embed(
            title="✅ Ticket Support Role Assigned",
            description=(
                f"Members with {role.mention} will now be automatically added to all new "
                "support tickets and have permission to manage and close them."
            ),
            color=0x57F287,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(text=f"Assigned by {ctx.author}")
        await ctx.respond(embed=embed)

    # ── /remove-ticketrole ────────────────────────────────────────────────────
    @discord.slash_command(name="remove-ticketrole", description="Remove the ticket support role restriction (Server Owner only)")
    async def remove_ticketrole(self, ctx: discord.ApplicationContext):
        if ctx.author.id != ctx.guild.owner_id and not is_bot_owner(ctx.author.id):
            return await ctx.respond(
                embed=discord.Embed(
                    title="🔒 Server Owner Only",
                    description="Only the **server owner** can remove the ticket support staff role.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )
        await set_config(ctx.guild.id, ticket_role_id=None)
        await ctx.respond(
            embed=discord.Embed(
                title="✅ Ticket Support Role Removed",
                description="The ticket support role restriction has been cleared.",
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
            return c.mention if c else "`Not Configured`"

        def role(id_):
            r = g.get_role(id_) if id_ else None
            return r.mention if r else "`Not Configured`"

        embed = discord.Embed(
            title="Nexus • Server Configuration",
            description=f"Current settings and audit channels for **{g.name}**.",
            color=0x2B2D31,
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(
            name="🛡️ Access & Roles",
            value=(
                f"**Bot Management:** {role(cfg.get('bot_role_id'))}\n"
                f"**Support Staff:** {role(cfg.get('ticket_role_id'))}"
            ),
            inline=False,
        )

        embed.add_field(
            name="📋 Logging & Audit Pipeline",
            value=(
                f"**Mod Logs:** {ch(cfg.get('mod_log_ch') or cfg.get('log_ch'))}\n"
                f"**Server Logs:** {ch(cfg.get('server_log_ch'))}\n"
                f"**Activity Logs:** {ch(cfg.get('activity_log_ch'))}\n"
                f"**Command Logs:** {ch(cfg.get('cmd_log_ch'))}"
            ),
            inline=False,
        )

        welcome_c = ch(cfg.get("welcome_ch"))
        leave_c = ch(cfg.get("leave_ch"))
        embed.add_field(
            name="👋 Welcoming System",
            value=(
                f"**Welcome Channel:** {welcome_c}\n"
                f"**Leave Channel:** {leave_c}"
            ),
            inline=False,
        )

        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.set_footer(text=f"Server ID: {g.id} • Use /setupbot to re-initialize logs")
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
            cmd_ch      = await get_or_make_channel("🔒・cmd-logs",      "Dedicated execution log channel for prefix and slash commands")

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
            cmd_log_ch=cmd_ch.id,
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

        await cmd_ch.send(embed=discord.Embed(
            title="⌨️ Command Log Channel — Active",
            description="Records: Prefix and slash command executions",
            color=0x5865F2, timestamp=discord.utils.utcnow(),
        ).set_footer(text="Nexus  •  Command Audit"))

        reply = discord.Embed(
            title="🚀 Nexus Setup Complete",
            description=(
                f"Four private audit log channels have been configured:\n\n"
                f"🔨 **Mod Logs:** {mod_ch.mention}\n"
                f"📋 **Server Logs:** {server_ch.mention}\n"
                f"📨 **Activity Logs:** {activity_ch.mention}\n"
                f"⌨️ **Command Logs:** {cmd_ch.mention}\n\n"
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
        if not is_bot_owner(ctx.author.id) and not await self.bot.is_owner(ctx.author):
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
