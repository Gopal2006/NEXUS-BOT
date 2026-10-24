"""
Utility Cog — Technical telemetry, profile inspection, and detailed server info.
Commands:
  - /serverinfo, /userinfo (Public / Server Members)
  - /ping, /stats, /uptime (Bot Owner Only)
"""

import time
import platform
import discord
from discord.ext import commands
from discord import option

from core.config import BRAND_NAME, SUPPORT_SERVER, is_bot_owner
from core.permissions import requires_tier
from core.ui import COLOR_BLURPLE, COLOR_GREEN
from utils.durations import format_duration

_BOT_START_TIME = time.time()


class Utility(commands.Cog):
    """💡 Utility, System Telemetry, and Server Insights."""

    def __init__(self, bot):
        self.bot = bot

    # ── Ping (Bot Owner Only) ─────────────────────────────────────────────────
    @discord.slash_command(name="ping", description="[Owner] Check bot gateway WebSocket latency and API response")
    @requires_tier("bot_owner")
    async def slash_ping(self, ctx: discord.ApplicationContext):
        start = time.perf_counter()
        await ctx.defer(ephemeral=False)
        end = time.perf_counter()
        api_latency = round((end - start) * 1000)
        gateway_latency = round(self.bot.latency * 1000)

        embed = discord.Embed(
            title="🏓 Pong!",
            color=COLOR_GREEN,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="🌐 Gateway Latency", value=f"`{gateway_latency}ms`", inline=True)
        embed.add_field(name="⚡ REST API Latency", value=f"`{api_latency}ms`", inline=True)
        embed.set_footer(text=f"{BRAND_NAME} System Diagnostics")
        await ctx.followup.send(embed=embed)

    @commands.command(name="ping")
    @requires_tier("bot_owner")
    async def prefix_ping(self, ctx: commands.Context):
        """n!ping — [Owner] Check bot latency"""
        start = time.perf_counter()
        msg = await ctx.reply("🏓 Pinging...")
        end = time.perf_counter()
        api_latency = round((end - start) * 1000)
        gateway_latency = round(self.bot.latency * 1000)

        embed = discord.Embed(
            title="🏓 Pong!",
            color=COLOR_GREEN,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="🌐 Gateway Latency", value=f"`{gateway_latency}ms`", inline=True)
        embed.add_field(name="⚡ REST API Latency", value=f"`{api_latency}ms`", inline=True)
        embed.set_footer(text=f"{BRAND_NAME} System Diagnostics")
        await msg.edit(content=None, embed=embed)

    # ── Uptime (Bot Owner Only) ───────────────────────────────────────────────
    @discord.slash_command(name="uptime", description="[Owner] Exact uptime since bot process started")
    @requires_tier("bot_owner")
    async def slash_uptime(self, ctx: discord.ApplicationContext):
        elapsed = time.time() - _BOT_START_TIME
        embed = discord.Embed(
            title="⏱️ Process Uptime",
            description=f"**{BRAND_NAME}** running continuously for:\n`{format_duration(elapsed)}`",
            color=COLOR_BLURPLE,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="🚀 Started At", value=f"<t:{int(_BOT_START_TIME)}:F> (<t:{int(_BOT_START_TIME)}:R>)", inline=False)
        await ctx.respond(embed=embed)

    @commands.command(name="uptime")
    @requires_tier("bot_owner")
    async def prefix_uptime(self, ctx: commands.Context):
        """n!uptime — [Owner] Check uptime"""
        elapsed = time.time() - _BOT_START_TIME
        embed = discord.Embed(
            title="⏱️ Process Uptime",
            description=f"**{BRAND_NAME}** running continuously for:\n`{format_duration(elapsed)}`",
            color=COLOR_BLURPLE,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="🚀 Started At", value=f"<t:{int(_BOT_START_TIME)}:F> (<t:{int(_BOT_START_TIME)}:R>)", inline=False)
        await ctx.reply(embed=embed)

    # ── Stats (Bot Owner Only) ────────────────────────────────────────────────
    @discord.slash_command(name="stats", description="[Owner] View cluster metrics and resource usage")
    @requires_tier("bot_owner")
    async def slash_stats(self, ctx: discord.ApplicationContext):
        await self._send_stats(ctx)

    @commands.command(name="stats", aliases=["botinfo", "about"])
    @requires_tier("bot_owner")
    async def prefix_stats(self, ctx: commands.Context):
        """n!stats — [Owner] Global cluster telemetry"""
        await self._send_stats(ctx)

    async def _send_stats(self, ctx):
        bot = self.bot
        total_guilds = len(bot.guilds)
        total_users = sum(g.member_count or 0 for g in bot.guilds)
        total_channels = sum(len(g.channels) for g in bot.guilds)
        uptime_str = format_duration(time.time() - _BOT_START_TIME)

        embed = discord.Embed(
            title=f"📊 {BRAND_NAME} — Global Telemetry",
            color=COLOR_BLURPLE,
            timestamp=discord.utils.utcnow(),
        )
        if bot.user.display_avatar:
            embed.set_thumbnail(url=bot.user.display_avatar.url)

        embed.add_field(
            name="🤖 Identity & Reach",
            value=(
                f"**Name:** {bot.user.name}\n"
                f"**ID:** `{bot.user.id}`\n"
                f"**Guilds:** `{total_guilds:,}`\n"
                f"**Total Users:** `{total_users:,}`\n"
                f"**Channels:** `{total_channels:,}`"
            ),
            inline=True,
        )
        embed.add_field(
            name="⚙️ Environment",
            value=(
                f"**Python:** `v{platform.python_version()}`\n"
                f"**Py-cord:** `v{discord.__version__}`\n"
                f"**OS:** `{platform.system()} {platform.release()}`\n"
                f"**WebSocket:** `{round(bot.latency * 1000)}ms`\n"
                f"**Uptime:** `{uptime_str}`"
            ),
            inline=True,
        )
        embed.set_footer(text=f"{BRAND_NAME} Global Infrastructure")

        if hasattr(ctx, "respond"):
            await ctx.respond(embed=embed)
        else:
            await ctx.reply(embed=embed)

    # ── Userinfo (Public) ─────────────────────────────────────────────────────
    @discord.slash_command(name="userinfo", description="Display deep profile inspection for a member")
    @option("member", discord.Member, description="Member to look up (defaults to yourself)", required=False, default=None)
    async def slash_userinfo(self, ctx: discord.ApplicationContext, member: discord.Member = None):
        target = member or ctx.author
        await self._send_userinfo(ctx, target)

    @commands.command(name="userinfo", aliases=["whois", "ui"])
    async def prefix_userinfo(self, ctx: commands.Context, member: discord.Member = None):
        """n!userinfo [@member] — Profile inspection"""
        target = member or ctx.author
        await self._send_userinfo(ctx, target)

    async def _send_userinfo(self, ctx, member: discord.Member):
        roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"]
        roles_str = ", ".join(roles) if roles else "*None*"
        if len(roles_str) > 1024:
            roles_str = roles_str[:1020] + "..."

        embed = discord.Embed(
            title=f"👤 Member Profile — {member.display_name}",
            color=member.color if member.color.value != 0 else COLOR_BLURPLE,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="📛 Username", value=f"`{member.name}`", inline=True)
        embed.add_field(name="🆔 User ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="🤖 Account Type", value="`Bot`" if member.bot else "`Human User`", inline=True)

        embed.add_field(
            name="📅 Created On",
            value=f"<t:{int(member.created_at.timestamp())}:D>\n(<t:{int(member.created_at.timestamp())}:R>)",
            inline=True,
        )
        if member.joined_at:
            embed.add_field(
                name="📥 Joined Server",
                value=f"<t:{int(member.joined_at.timestamp())}:D>\n(<t:{int(member.joined_at.timestamp())}:R>)",
                inline=True,
            )
        embed.add_field(name="🏷️ Top Role", value=member.top_role.mention, inline=True)
        embed.add_field(name=f"🎭 Assigned Roles [{len(roles)}]", value=roles_str, inline=False)

        # Key Permissions
        key_perms = []
        perms = member.guild_permissions
        if perms.administrator:
            key_perms.append("Administrator")
        if perms.manage_guild:
            key_perms.append("Manage Server")
        if perms.manage_roles:
            key_perms.append("Manage Roles")
        if perms.manage_channels:
            key_perms.append("Manage Channels")
        if perms.kick_members:
            key_perms.append("Kick Members")
        if perms.ban_members:
            key_perms.append("Ban Members")
        if perms.moderate_members:
            key_perms.append("Timeout Members")

        if key_perms:
            embed.add_field(name="🛡️ Key Permissions", value=" • ".join(key_perms), inline=False)

        embed.set_footer(text=f"Nexus Profile Audit • Requested by {ctx.author.name}")

        if hasattr(ctx, "respond"):
            await ctx.respond(embed=embed)
        else:
            await ctx.reply(embed=embed)

    # ── Serverinfo (Public) ───────────────────────────────────────────────────
    @discord.slash_command(name="serverinfo", description="Display full server overview and telemetry")
    async def slash_serverinfo(self, ctx: discord.ApplicationContext):
        await self._send_serverinfo(ctx)

    @commands.command(name="serverinfo", aliases=["server", "si"])
    async def prefix_serverinfo(self, ctx: commands.Context):
        """n!serverinfo — Detailed server statistics"""
        await self._send_serverinfo(ctx)

    async def _send_serverinfo(self, ctx):
        g = ctx.guild
        if not g:
            return

        total_members = g.member_count or len(g.members)
        humans = sum(1 for m in g.members if not m.bot)
        bots = total_members - humans
        online = sum(1 for m in g.members if m.status != discord.Status.offline and not m.bot)

        text_ch = len(g.text_channels)
        voice_ch = len(g.voice_channels)
        stage_ch = len(g.stage_channels)
        categories = len(g.categories)
        threads = len(g.threads)
        role_count = len(g.roles) - 1

        embed = discord.Embed(
            title=f"🏛️ {g.name}",
            description=g.description or "No server description set.",
            color=0x2B2D31,
            timestamp=discord.utils.utcnow(),
        )
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        if g.banner:
            embed.set_image(url=g.banner.url)

        embed.add_field(
            name="👑 Server Owner",
            value=f"{g.owner.mention if g.owner else '*Unknown*'} (`{g.owner_id}`)",
            inline=True,
        )
        embed.add_field(name="🆔 Guild ID", value=f"`{g.id}`", inline=True)
        embed.add_field(
            name="📅 Created On",
            value=f"<t:{int(g.created_at.timestamp())}:D> (<t:{int(g.created_at.timestamp())}:R>)",
            inline=True,
        )

        embed.add_field(
            name="👥 Member Demographics",
            value=(
                f"• **Total:** `{total_members:,}`\n"
                f"• **Humans:** `{humans:,}`\n"
                f"• **Bots:** `{bots:,}`\n"
                f"• **Online:** `{online:,}`"
            ),
            inline=True,
        )
        embed.add_field(
            name="💬 Channel Architecture",
            value=(
                f"• **Text:** `{text_ch}` | **Voice:** `{voice_ch}`\n"
                f"• **Stage:** `{stage_ch}` | **Threads:** `{threads}`\n"
                f"• **Categories:** `{categories}`"
            ),
            inline=True,
        )
        embed.add_field(
            name="💎 Nitro Boost Status",
            value=(
                f"• **Level:** `Tier {g.premium_tier}`\n"
                f"• **Boosts:** `{g.premium_subscription_count}` boosts\n"
                f"• **Vanity URL:** `{g.vanity_url_code or 'None'}`"
            ),
            inline=True,
        )

        embed.add_field(
            name="🛡️ Security & Roles",
            value=(
                f"• **Verification:** `{str(g.verification_level).title()}`\n"
                f"• **Explicit Filter:** `{str(g.explicit_content_filter).title()}`\n"
                f"• **Total Roles:** `{role_count}` roles"
            ),
            inline=False,
        )

        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)

        if hasattr(ctx, "respond"):
            await ctx.respond(embed=embed)
        else:
            await ctx.reply(embed=embed)


def setup(bot):
    bot.add_cog(Utility(bot))
