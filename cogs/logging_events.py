"""
Audit Logging Events Cog
Extends Nexus logging to capture message edits/deletions, member joins/leaves,
role & channel lifecycle changes, member profile updates, and voice activity
into the configured log channels (mod_log_ch, server_log_ch, activity_log_ch).
"""

import time
import logging
import discord
from discord.ext import commands

from db.database import get_config
from core.ui import ui_embed

log = logging.getLogger("Nexus.LoggingEvents")


class LoggingEventsCog(commands.Cog, name="LoggingEvents"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _get_channel(self, guild: discord.Guild, key: str) -> discord.TextChannel | None:
        cfg = await get_config(guild.id)
        ch_id = cfg.get(key) or cfg.get("log_ch")
        if ch_id:
            return guild.get_channel(ch_id)
        return None

    # ── Message Logs ──────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        log_ch = await self._get_channel(message.guild, "server_log_ch")
        if not log_ch:
            return

        content = message.content or "*No text content (embed or attachment)*"
        embed = ui_embed(
            title="🗑️ Message Deleted",
            description=(
                f"**Author:** {message.author.mention} (`{message.author.id}`)\n"
                f"**Channel:** {message.channel.mention}\n"
                f"**Content:**\n```\n{content[:1000]}\n```"
            ),
            color=0xED4245,
        )
        if message.attachments:
            embed.add_field(name="Attachments", value=str(len(message.attachments)), inline=True)
        embed.set_footer(text=f"Message ID: {message.id}")
        try:
            await log_ch.send(embed=embed)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild or before.author.bot:
            return
        if before.content == after.content:
            return

        log_ch = await self._get_channel(before.guild, "server_log_ch")
        if not log_ch:
            return

        before_txt = before.content or "*Empty*"
        after_txt = after.content or "*Empty*"
        embed = ui_embed(
            title="✏️ Message Edited",
            description=(
                f"**Author:** {before.author.mention} (`{before.author.id}`)\n"
                f"**Channel:** {before.channel.mention}\n"
                f"[Jump to Message]({after.jump_url})\n\n"
                f"**Before:**\n```\n{before_txt[:450]}\n```\n"
                f"**After:**\n```\n{after_txt[:450]}\n```"
            ),
            color=0xFEE75C,
        )
        embed.set_footer(text=f"Message ID: {before.id}")
        try:
            await log_ch.send(embed=embed)
        except Exception:
            pass

    # ── Channel Logs ──────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        log_ch = await self._get_channel(channel.guild, "server_log_ch")
        if not log_ch:
            return

        embed = ui_embed(
            title="📁 Channel Created",
            description=f"**Name:** #{channel.name} (`{channel.id}`)\n**Type:** {channel.type}",
            color=0x57F287,
        )
        try:
            await log_ch.send(embed=embed)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        log_ch = await self._get_channel(channel.guild, "server_log_ch")
        if not log_ch:
            return

        embed = ui_embed(
            title="🗑️ Channel Deleted",
            description=f"**Name:** #{channel.name} (`{channel.id}`)\n**Type:** {channel.type}",
            color=0xED4245,
        )
        try:
            await log_ch.send(embed=embed)
        except Exception:
            pass

    # ── Role Logs ─────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        log_ch = await self._get_channel(role.guild, "server_log_ch")
        if not log_ch:
            return

        embed = ui_embed(
            title="🛡️ Role Created",
            description=f"**Role:** {role.mention} (`{role.name}` / `{role.id}`)",
            color=0x57F287,
        )
        try:
            await log_ch.send(embed=embed)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        log_ch = await self._get_channel(role.guild, "server_log_ch")
        if not log_ch:
            return

        embed = ui_embed(
            title="🗑️ Role Deleted",
            description=f"**Name:** `{role.name}` (`{role.id}`)",
            color=0xED4245,
        )
        try:
            await log_ch.send(embed=embed)
        except Exception:
            pass

    # ── Voice Activity Logs ───────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.bot:
            return

        log_ch = await self._get_channel(member.guild, "activity_log_ch")
        if not log_ch:
            return

        # Voice Join
        if before.channel is None and after.channel is not None:
            embed = ui_embed(
                title="🔊 Voice Channel Joined",
                description=f"**Member:** {member.mention} (`{member.id}`)\n**Channel:** {after.channel.name}",
                color=0x57F287,
            )
            try:
                await log_ch.send(embed=embed)
            except Exception:
                pass

        # Voice Leave
        elif before.channel is not None and after.channel is None:
            embed = ui_embed(
                title="🔇 Voice Channel Left",
                description=f"**Member:** {member.mention} (`{member.id}`)\n**Channel:** {before.channel.name}",
                color=0xED4245,
            )
            try:
                await log_ch.send(embed=embed)
            except Exception:
                pass

        # Voice Move
        elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
            embed = ui_embed(
                title="🔄 Voice Channel Moved",
                description=(
                    f"**Member:** {member.mention} (`{member.id}`)\n"
                    f"**From:** {before.channel.name}\n"
                    f"**To:** {after.channel.name}"
                ),
                color=0x3498DB,
            )
            try:
                await log_ch.send(embed=embed)
            except Exception:
                pass

    # ── Member Update Logs ────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.bot:
            return

        log_ch = await self._get_channel(before.guild, "server_log_ch")
        if not log_ch:
            return

        # Nickname change
        if before.display_name != after.display_name:
            embed = ui_embed(
                title="🏷️ Nickname Changed",
                description=(
                    f"**Member:** {after.mention} (`{after.id}`)\n"
                    f"**Before:** `{before.display_name}`\n"
                    f"**After:** `{after.display_name}`"
                ),
                color=0x3498DB,
            )
            try:
                await log_ch.send(embed=embed)
            except Exception:
                pass

        # Roles change
        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]

            if added:
                added_str = ", ".join(r.mention for r in added)
                embed = ui_embed(
                    title="➕ Role(s) Added",
                    description=f"**Member:** {after.mention}\n**Roles Added:** {added_str}",
                    color=0x57F287,
                )
                try:
                    await log_ch.send(embed=embed)
                except Exception:
                    pass

            if removed:
                removed_str = ", ".join(r.mention for r in removed)
                embed = ui_embed(
                    title="➖ Role(s) Removed",
                    description=f"**Member:** {after.mention}\n**Roles Removed:** {removed_str}",
                    color=0xED4245,
                )
                try:
                    await log_ch.send(embed=embed)
                except Exception:
                    pass


def setup(bot: commands.Bot):
    bot.add_cog(LoggingEventsCog(bot))
