"""
Autorole Cog
Automatically assigns configured roles to newly joined humans and bots separately.
"""

import logging
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup, option

from core.permissions import requires_tier
from core.ui import ui_success, ui_error, ui_info
from db.repos.management import get_autorole_settings, update_autorole_settings

log = logging.getLogger("Nexus.Autorole")


class AutoroleCog(commands.Cog, name="Autorole"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    autorole_group = SlashCommandGroup("autorole", "Configure automatic role for new members")

    # ── Slash: /autorole set-human ────────────────────────────────────────────
    @autorole_group.command(name="set-human", description="Set automatic role for new human members")
    @requires_tier("staff")
    @option("role", description="Role to automatically grant to human members", required=True)
    async def slash_autorole_set_human(
        self,
        ctx: discord.ApplicationContext,
        role: discord.Role,
    ):
        if role >= ctx.guild.me.top_role:
            return await ctx.respond(
                embed=ui_error("Role Hierarchy Error", f"I cannot assign {role.mention} because it is higher than or equal to my highest role."),
                ephemeral=True,
            )

        await update_autorole_settings(ctx.guild.id, human_role_id=role.id)
        await ctx.respond(
            embed=ui_success("Autorole Configured", f"Newly joined members will automatically receive {role.mention}.")
        )

    # ── Slash: /autorole view ─────────────────────────────────────────────────
    @autorole_group.command(name="view", description="View current autorole settings")
    @requires_tier("staff")
    async def slash_autorole_view(self, ctx: discord.ApplicationContext):
        s = await get_autorole_settings(ctx.guild.id)
        hr_id = s.get("human_role_id")
        hr_str = f"<@&{hr_id}>" if hr_id and ctx.guild.get_role(hr_id) else "`None (Disabled)`"

        embed = ui_info(
            "⚙️ Autorole Configuration",
            f"**Member Autorole:** {hr_str}\n\n*Applied automatically to human accounts upon joining.*",
        )
        await ctx.respond(embed=embed)

    # ── Slash: /autorole clear ────────────────────────────────────────────────
    @autorole_group.command(name="clear", description="Clear autorole configuration")
    @requires_tier("staff")
    async def slash_autorole_clear(self, ctx: discord.ApplicationContext):
        await update_autorole_settings(ctx.guild.id, human_role_id=None)
        await ctx.respond(embed=ui_success("Autorole Cleared", "Member autorole has been disabled."))

    # ── Prefix: n!autorole ────────────────────────────────────────────────────
    @commands.group(name="autorole", invoke_without_command=True)
    @requires_tier("staff")
    async def prefix_autorole(self, ctx: commands.Context):
        s = await get_autorole_settings(ctx.guild.id)
        hr_id = s.get("human_role_id")
        hr_str = f"<@&{hr_id}>" if hr_id and ctx.guild.get_role(hr_id) else "`None (Disabled)`"

        lines = [
            f"**Member Autorole:** {hr_str}",
            "",
            f"Use `{ctx.prefix}autorole set <@role>` to configure.",
            f"Use `{ctx.prefix}autorole clear` to remove autorole.",
        ]
        await ctx.reply(embed=ui_info("⚙️ Autorole Configuration", "\n".join(lines)))

    @prefix_autorole.command(name="set")
    @requires_tier("staff")
    async def prefix_autorole_set(
        self,
        ctx: commands.Context,
        role: discord.Role = None,
    ):
        if not role:
            return await ctx.reply(
                embed=ui_error("Usage", f"`{ctx.prefix}autorole set <@role>`")
            )

        if role >= ctx.guild.me.top_role:
            return await ctx.reply(
                embed=ui_error("Role Hierarchy Error", f"I cannot assign {role.mention} because it is higher than my bot role.")
            )

        await update_autorole_settings(ctx.guild.id, human_role_id=role.id)
        await ctx.reply(embed=ui_success("Autorole Configured", f"Successfully set member autorole to {role.mention}."))

    @prefix_autorole.command(name="clear")
    @requires_tier("staff")
    async def prefix_autorole_clear(self, ctx: commands.Context):
        await update_autorole_settings(ctx.guild.id, human_role_id=None)
        await ctx.reply(embed=ui_success("Autorole Cleared", "Cleared member autorole."))

    # ── Gateway Listener ──────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        guild = member.guild
        s = await get_autorole_settings(guild.id)

        target_role_id = s.get("human_role_id")
        if not target_role_id:
            return

        role = guild.get_role(target_role_id)
        if not role or role >= guild.me.top_role:
            return

        try:
            await member.add_roles(role, reason="Nexus Autorole on join")
            log.info(f"[AUTOROLE] Assigned {role.name} to {member} in {guild.name}")
        except discord.Forbidden:
            log.warning(f"[AUTOROLE] Missing permissions to assign {role.name} in {guild.name}")
        except Exception as e:
            log.error(f"[AUTOROLE] Error assigning role to {member}: {e}")


def setup(bot: commands.Bot):
    bot.add_cog(AutoroleCog(bot))
