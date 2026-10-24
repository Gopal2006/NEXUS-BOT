"""
Autoresponder Cog
Configurable automatic text responses to specific triggers or phrases.
"""

import logging
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup, option

from core.permissions import requires_tier
from core.ui import ui_embed, ui_error, ui_success, ui_info
from db.repos.engagement import (
    get_autoresponders,
    add_autoresponder,
    delete_autoresponder,
)
from utils.placeholders import safe_format

log = logging.getLogger("Nexus.Autoresponder")


class AutoresponderCog(commands.Cog, name="Autoresponder"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    ar_group = SlashCommandGroup("autoresponder", "Configure automated text triggers and responses")

    # ── Slash: /autoresponder add ─────────────────────────────────────────────
    @ar_group.command(name="add", description="Add an automated response to a trigger word/phrase")
    @requires_tier("staff")
    @option("trigger", description="Word or phrase that triggers the bot")
    @option("response", description="The response message to send (supports {user}, {server})")
    @option("match_type", description="How the trigger is matched", choices=["exact", "contains"], default="exact")
    async def slash_ar_add(
        self,
        ctx: discord.ApplicationContext,
        trigger: str,
        response: str,
        match_type: str = "exact",
    ):
        success = await add_autoresponder(ctx.guild.id, trigger, response, match_type)
        if success:
            await ctx.respond(
                embed=ui_success(
                    "Autoresponder Added",
                    f"**Trigger:** `{trigger}`\n**Match Type:** `{match_type}`\n**Response:** {response}",
                )
            )
        else:
            await ctx.respond(embed=ui_error("Database Error", "Failed to save autoresponder."), ephemeral=True)

    # ── Slash: /autoresponder remove ──────────────────────────────────────────
    @ar_group.command(name="remove", description="Remove an autoresponder by trigger word")
    @requires_tier("staff")
    @option("trigger", description="The trigger word to delete")
    async def slash_ar_remove(self, ctx: discord.ApplicationContext, trigger: str):
        success = await delete_autoresponder(ctx.guild.id, trigger)
        if success:
            await ctx.respond(embed=ui_success("Autoresponder Removed", f"Deleted trigger `{trigger}`."))
        else:
            await ctx.respond(embed=ui_error("Not Found", f"No autoresponder found for `{trigger}`."), ephemeral=True)

    # ── Slash: /autoresponder list ────────────────────────────────────────────
    @ar_group.command(name="list", description="List all configured autoresponders")
    @requires_tier("staff")
    async def slash_ar_list(self, ctx: discord.ApplicationContext):
        entries = await get_autoresponders(ctx.guild.id)
        if not entries:
            return await ctx.respond(embed=ui_info("Autoresponders", "No autoresponders configured in this server."))

        lines = [f"• `{e['trigger']}` ({e['match_type']}) ➜ {e['response'][:60]}" for e in entries[:25]]
        embed = ui_info(f"🤖 Autoresponders ({len(entries)})", "\n".join(lines))
        await ctx.respond(embed=embed)

    # ── Prefix: n!autoresponder ───────────────────────────────────────────────
    @commands.group(name="autoresponder", aliases=["ar"], invoke_without_command=True)
    @requires_tier("staff")
    async def prefix_ar(self, ctx: commands.Context):
        entries = await get_autoresponders(ctx.guild.id)
        if not entries:
            return await ctx.reply(
                embed=ui_info(
                    "Autoresponders",
                    f"No autoresponders configured. Use `{ctx.prefix}ar add <trigger> | <response>` to add one."
                )
            )
        lines = [f"• `{e['trigger']}` ({e['match_type']}) ➜ {e['response'][:60]}" for e in entries[:25]]
        await ctx.reply(embed=ui_info(f"🤖 Autoresponders ({len(entries)})", "\n".join(lines)))

    @prefix_ar.command(name="add")
    @requires_tier("staff")
    async def prefix_ar_add(self, ctx: commands.Context, *, content: str):
        if "|" not in content:
            return await ctx.reply(
                embed=ui_error("Usage", f"`{ctx.prefix}ar add <trigger> | <response>`")
            )
        trigger, response = content.split("|", 1)
        trigger = trigger.strip()
        response = response.strip()
        if not trigger or not response:
            return await ctx.reply(embed=ui_error("Error", "Trigger and response cannot be empty."))

        await add_autoresponder(ctx.guild.id, trigger, response, match_type="exact")
        await ctx.reply(embed=ui_success("Autoresponder Added", f"Added autoresponder for `{trigger}`."))

    @prefix_ar.command(name="remove", aliases=["del", "rm"])
    @requires_tier("staff")
    async def prefix_ar_remove(self, ctx: commands.Context, *, trigger: str):
        success = await delete_autoresponder(ctx.guild.id, trigger)
        if success:
            await ctx.reply(embed=ui_success("Autoresponder Removed", f"Deleted trigger `{trigger}`."))
        else:
            await ctx.reply(embed=ui_error("Not Found", f"No autoresponder found for `{trigger}`."))

    # ── Gateway Listener ──────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        content = (message.content or "").strip().lower()
        if not content:
            return

        entries = await get_autoresponders(message.guild.id)
        for e in entries:
            trig = e["trigger"]
            mtype = e.get("match_type", "exact")

            matched = False
            if mtype == "exact" and content == trig:
                matched = True
            elif mtype == "contains" and trig in content:
                matched = True

            if matched:
                reply = safe_format(
                    e["response"],
                    user=message.author.mention,
                    name=message.author.name,
                    server=message.guild.name,
                )
                try:
                    await message.channel.send(reply)
                except Exception:
                    pass
                break


def setup(bot: commands.Bot):
    bot.add_cog(AutoresponderCog(bot))
