"""
Global error handlers for slash and prefix commands.
Preserves silent-ignore behavior for owner-exclusive commands when invoked by non-owners.
"""

import logging
import discord
from discord.ext import commands

from core.config import is_bot_owner
from core.permissions import send_no_permission

log = logging.getLogger("Nexus.Errors")

OWNER_COMMANDS = {
    "addnp", "removenp", "nplist", "np", "np add", "np remove", "np list",
    "npadd", "npremove", "checknp", "sync",
}


def setup_error_handlers(bot: commands.Bot):
    """Registers global error event listeners on the bot."""

    @bot.event
    async def on_application_command_error(
        ctx: discord.ApplicationContext, error: discord.DiscordException
    ):
        if isinstance(error, (commands.CheckFailure, discord.CheckFailure)):
            return await send_no_permission(ctx)

        log.error(f"Error in slash command '{ctx.command}': {error}")
        try:
            if not ctx.response.is_done():
                await ctx.respond(
                    embed=discord.Embed(
                        description=f"❌ An error occurred: `{error}`", color=0xED4245
                    ),
                    ephemeral=True,
                )
            else:
                await ctx.followup.send(
                    embed=discord.Embed(
                        description=f"❌ An error occurred: `{error}`", color=0xED4245
                    ),
                    ephemeral=True,
                )
        except Exception:
            pass

    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            return

        # If a member other than the bot owner tries to invoke an owner command, completely ignore
        cmd_name = (
            ctx.command.qualified_name if ctx.command else (ctx.invoked_with or "")
        ).lower()
        if cmd_name in OWNER_COMMANDS:
            if not is_bot_owner(getattr(ctx.author, "id", 0)):
                return

        if isinstance(error, commands.CheckFailure):
            return await send_no_permission(ctx)
        if isinstance(error, commands.UserNotFound):
            return await ctx.reply("❌ User not found. Please mention a user or provide a valid user ID.")
        if isinstance(error, commands.BadArgument):
            return await ctx.reply(f"❌ Invalid argument: {error}")
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.reply(f"❌ Missing required argument: `{error.param.name}`")

        log.error(f"Error in prefix command '{ctx.command}': {error}")
