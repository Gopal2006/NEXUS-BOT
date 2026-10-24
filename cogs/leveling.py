"""
Leveling and XP System Cog
Tracks message activity, awards XP with cooldowns, calculates levels via a standard quadratic curve,
and dispenses role rewards and customizable celebration alerts.
"""

import random
import time
import logging
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup, option

from core.permissions import requires_tier
from core.ui import ui_embed, ui_error, ui_success, ui_info
from db.repos.engagement import (
    get_level_settings,
    update_level_settings,
    add_xp,
    get_user_level,
    get_leaderboard,
    xp_required_for_level,
)
from utils.placeholders import safe_format

log = logging.getLogger("Nexus.Leveling")

# In-memory cooldown tracking: (guild_id, user_id) -> last_awarded_timestamp
_xp_cooldowns: dict[tuple[int, int], float] = {}


class LevelingCog(commands.Cog, name="Leveling"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    leveling_group = SlashCommandGroup("leveling", "Configure server leveling and role rewards")

    # ── Public: /rank & n!rank ────────────────────────────────────────────────
    @commands.slash_command(name="rank", description="Check your current level, XP, and server leaderboard rank")
    @option("user", description="The user to inspect (defaults to yourself)", required=False)
    async def slash_rank(self, ctx: discord.ApplicationContext, user: discord.Member = None):
        target = user or ctx.author
        data = await get_user_level(ctx.guild.id, target.id)

        lvl = data["level"]
        xp = data["xp"]
        cur_cost = xp_required_for_level(lvl)
        next_cost = xp_required_for_level(lvl + 1)
        needed = next_cost - cur_cost
        progress = max(0, xp - cur_cost)
        pct = min(100, int((progress / max(1, needed)) * 100))

        # Visual progress bar: 10 segments
        filled = int((pct / 100) * 10)
        bar = "▰" * filled + "▱" * (10 - filled)

        embed = ui_embed(
            title=f"⭐ Rank & Level: {target.display_name}",
            description=(
                f"🏆 **Server Rank:** `#{data['rank']}`\n"
                f"📊 **Current Level:** `{lvl}`\n"
                f"✨ **Total XP:** `{xp:,}`\n"
                f"💬 **Messages:** `{data['messages']:,}`\n\n"
                f"**Level Progress:** [{bar}] `{pct}%`\n"
                f"`{progress:,} / {needed:,} XP to Level {lvl + 1}`"
            ),
            color=0xFEE75C,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.respond(embed=embed)

    @commands.command(name="rank")
    async def prefix_rank(self, ctx: commands.Context, user: discord.Member = None):
        target = user or ctx.author
        data = await get_user_level(ctx.guild.id, target.id)

        lvl = data["level"]
        xp = data["xp"]
        cur_cost = xp_required_for_level(lvl)
        next_cost = xp_required_for_level(lvl + 1)
        needed = next_cost - cur_cost
        progress = max(0, xp - cur_cost)
        pct = min(100, int((progress / max(1, needed)) * 100))

        filled = int((pct / 100) * 10)
        bar = "▰" * filled + "▱" * (10 - filled)

        embed = ui_embed(
            title=f"⭐ Rank & Level: {target.display_name}",
            description=(
                f"🏆 **Server Rank:** `#{data['rank']}`\n"
                f"📊 **Current Level:** `{lvl}`\n"
                f"✨ **Total XP:** `{xp:,}`\n"
                f"💬 **Messages:** `{data['messages']:,}`\n\n"
                f"**Level Progress:** [{bar}] `{pct}%`\n"
                f"`{progress:,} / {needed:,} XP to Level {lvl + 1}`"
            ),
            color=0xFEE75C,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.reply(embed=embed)

    # ── Public: /leaderboard & n!leaderboard ──────────────────────────────────
    @commands.slash_command(name="leaderboard", description="View the server XP leaderboard")
    @option("page", description="Leaderboard page number", min_value=1, default=1)
    async def slash_leaderboard(self, ctx: discord.ApplicationContext, page: int = 1):
        offset = (page - 1) * 10
        top = await get_leaderboard(ctx.guild.id, limit=10, offset=offset)
        if not top and page > 1:
            return await ctx.respond(embed=ui_info("Leaderboard", "No more entries on this page."), ephemeral=True)
        if not top:
            return await ctx.respond(embed=ui_info("Leaderboard", "No XP recorded in this server yet! Start chatting."))

        lines = []
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for idx, entry in enumerate(top, start=offset + 1):
            icon = medals.get(idx, f"`#{idx}`")
            lines.append(
                f"{icon} <@{entry['user_id']}> — **Level {entry['level']}** (`{entry['xp']:,} XP` • `{entry['messages']:,} msgs`)"
            )

        embed = ui_embed(
            title=f"🏆 XP Leaderboard — Page {page}",
            description="\n".join(lines),
            color=0xFEE75C,
        )
        await ctx.respond(embed=embed)

    @commands.command(name="leaderboard", aliases=["lb", "top"])
    async def prefix_leaderboard(self, ctx: commands.Context, page: int = 1):
        page = max(1, page)
        offset = (page - 1) * 10
        top = await get_leaderboard(ctx.guild.id, limit=10, offset=offset)
        if not top:
            return await ctx.reply(embed=ui_info("Leaderboard", "No XP recorded in this server yet! Start chatting."))

        lines = []
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for idx, entry in enumerate(top, start=offset + 1):
            icon = medals.get(idx, f"`#{idx}`")
            lines.append(
                f"{icon} <@{entry['user_id']}> — **Level {entry['level']}** (`{entry['xp']:,} XP` • `{entry['messages']:,} msgs`)"
            )

        embed = ui_embed(
            title=f"🏆 XP Leaderboard — Page {page}",
            description="\n".join(lines),
            color=0xFEE75C,
        )
        await ctx.reply(embed=embed)

    # ── Staff: /leveling settings & rewards ───────────────────────────────────
    @leveling_group.command(name="toggle", description="Enable or disable leveling in this server")
    @requires_tier("staff")
    @option("status", description="Enable or disable XP tracking", choices=["enable", "disable"])
    async def slash_leveling_toggle(self, ctx: discord.ApplicationContext, status: str):
        val = 1 if status == "enable" else 0
        await update_level_settings(ctx.guild.id, enabled=val)
        desc = "Leveling & XP tracking is now **ENABLED**." if val else "Leveling is now **DISABLED**."
        await ctx.respond(embed=ui_success("Leveling Configuration", desc))

    @leveling_group.command(name="reward", description="Assign or remove a role reward for reaching a level")
    @requires_tier("staff")
    @option("action", description="Action to perform", choices=["add", "remove"])
    @option("level", description="The level requirement", min_value=1, max_value=200)
    @option("role", description="The role to grant (if adding)", required=False)
    async def slash_leveling_reward(
        self,
        ctx: discord.ApplicationContext,
        action: str,
        level: int,
        role: discord.Role = None,
    ):
        settings = await get_level_settings(ctx.guild.id)
        rewards = settings.get("role_rewards", {})

        if action == "add":
            if not role:
                return await ctx.respond(embed=ui_error("Missing Role", "You must specify a role to award."), ephemeral=True)
            if role >= ctx.guild.me.top_role:
                return await ctx.respond(embed=ui_error("Hierarchy Error", "I cannot award a role higher than or equal to my highest role."), ephemeral=True)
            rewards[str(level)] = role.id
            await update_level_settings(ctx.guild.id, role_rewards=rewards)
            return await ctx.respond(embed=ui_success("Role Reward Added", f"Members reaching **Level {level}** will receive {role.mention}!"))

        elif action == "remove":
            if str(level) not in rewards:
                return await ctx.respond(embed=ui_error("Not Found", f"No role reward configured for Level {level}."), ephemeral=True)
            del rewards[str(level)]
            await update_level_settings(ctx.guild.id, role_rewards=rewards)
            return await ctx.respond(embed=ui_success("Role Reward Removed", f"Removed role reward for Level {level}."))

    @leveling_group.command(name="settings", description="View current leveling configuration")
    @requires_tier("staff")
    async def slash_leveling_settings(self, ctx: discord.ApplicationContext):
        s = await get_level_settings(ctx.guild.id)
        status = "🟢 Enabled" if s["enabled"] else "🔴 Disabled"
        ch = ctx.guild.get_channel(s["channel_id"]) if s.get("channel_id") else None

        rewards = s.get("role_rewards", {})
        reward_lines = [f"• Level {lvl}: <@&{rid}>" for lvl, rid in sorted(rewards.items(), key=lambda x: int(x[0]))]

        lines = [
            f"**Status:** {status}",
            f"**XP Range:** `{s['min_xp']} - {s['max_xp']}` per message",
            f"**Cooldown:** `{s['cooldown_seconds']}s`",
            f"**Alert Channel:** {ch.mention if ch else 'Current Chat'}",
            "",
            f"**Role Rewards ({len(rewards)}):**",
            ("\n".join(reward_lines) if reward_lines else "None configured"),
        ]
        await ctx.respond(embed=ui_info("⚙️ Leveling Configuration", "\n".join(lines)))

    # ── Gateway Listener for XP Gains ─────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        settings = await get_level_settings(message.guild.id)
        if not settings.get("enabled"):
            return

        now = time.time()
        cd_key = (message.guild.id, message.author.id)
        last_t = _xp_cooldowns.get(cd_key, 0)
        cooldown = settings.get("cooldown_seconds", 60)

        if now - last_t < cooldown:
            return

        _xp_cooldowns[cd_key] = now

        min_xp = settings.get("min_xp", 15)
        max_xp = settings.get("max_xp", 25)
        earned = random.randint(min_xp, max(min_xp, max_xp))

        leveled_up, new_level, _ = await add_xp(message.guild.id, message.author.id, earned)
        if not leveled_up:
            return

        # Check for role rewards
        rewards = settings.get("role_rewards", {})
        reward_role = None
        if str(new_level) in rewards:
            role_id = rewards[str(new_level)]
            role = message.guild.get_role(role_id)
            if role and role < message.guild.me.top_role:
                try:
                    await message.author.add_roles(role, reason=f"Level {new_level} role reward")
                    reward_role = role
                except Exception:
                    pass

        # Send celebration message
        target_ch_id = settings.get("channel_id")
        target_ch = message.guild.get_channel(target_ch_id) if target_ch_id else message.channel
        if not target_ch:
            return

        template = settings.get("levelup_message") or "Congratulations {user}! You leveled up to **Level {level}**! 🎉"
        reward_txt = f"\n🎁 **Role Reward Unlocked:** {reward_role.mention}!" if reward_role else ""
        msg_text = safe_format(template, user=message.author.mention, name=message.author.name, level=new_level) + reward_txt

        embed = ui_embed(
            title="🎉 Level Up!",
            description=msg_text,
            color=0xFEE75C,
        )
        embed.set_thumbnail(url=message.author.display_avatar.url)
        try:
            await target_ch.send(embed=embed)
        except Exception:
            pass


def setup(bot: commands.Bot):
    bot.add_cog(LevelingCog(bot))
