"""
AFK (Away From Keyboard) System Cog
Allows users to set an AFK status with custom reasons.
Notifies users when an AFK member is mentioned and automatically clears AFK on return.
"""

import time
import asyncio
import logging
import discord
from discord.ext import commands
from discord.commands import option

from core.ui import ui_embed, ui_info
from db.repos.engagement import set_afk, get_afk, remove_afk
from utils.durations import format_duration

log = logging.getLogger("Nexus.AFK")


class AFKCog(commands.Cog, name="AFK"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── /afk & n!afk ──────────────────────────────────────────────────────────
    @commands.slash_command(name="afk", description="Set your status to AFK (Away From Keyboard)")
    @option("reason", description="Why you are going AFK", default="AFK")
    async def slash_afk(self, ctx: discord.ApplicationContext, reason: str = "AFK"):
        await set_afk(ctx.guild.id, ctx.author.id, reason=reason[:200])
        await ctx.respond(
            embed=ui_info(
                "💤 AFK Status Set",
                f"{ctx.author.mention} is now AFK: **{reason}**.\nI will notify anyone who mentions you and clear your status when you return.",
            )
        )

    @commands.command(name="afk")
    async def prefix_afk(self, ctx: commands.Context, *, reason: str = "AFK"):
        await set_afk(ctx.guild.id, ctx.author.id, reason=reason[:200])
        await ctx.reply(
            embed=ui_info(
                "💤 AFK Status Set",
                f"{ctx.author.mention} is now AFK: **{reason}**.\nI will notify anyone who mentions you and clear your status when you return.",
            )
        )

    # ── Gateway Listener for AFK Notifications and Clear ──────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        # 1. Check if the message author was AFK -> Remove AFK
        afk_data = await get_afk(message.guild.id, message.author.id)
        if afk_data:
            duration = format_duration(time.time() - afk_data["timestamp"])
            await remove_afk(message.guild.id, message.author.id)
            try:
                msg = await message.channel.send(
                    f"👋 Welcome back {message.author.mention}! I've removed your AFK status (You were gone for **{duration}**)."
                )
                self.bot.loop.call_later(6, lambda: asyncio.create_task(msg.delete()))
            except Exception:
                pass

        # 2. Check if any mentioned users are currently AFK
        if message.mentions:
            for user in message.mentions:
                if user.bot or user.id == message.author.id:
                    continue

                user_afk = await get_afk(message.guild.id, user.id)
                if user_afk:
                    duration = format_duration(time.time() - user_afk["timestamp"])
                    reason = user_afk["reason"]
                    try:
                        await message.channel.send(
                            f"💤 **{user.display_name}** is currently AFK: `{reason}` ({duration} ago)."
                        )
                    except Exception:
                        pass


def setup(bot: commands.Bot):
    bot.add_cog(AFKCog(bot))
