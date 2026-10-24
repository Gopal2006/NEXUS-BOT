"""
Reaction Roles Cog
Button-based interactive role selection.
Uses persistent custom_ids so buttons survive bot restarts indefinitely.
"""

import logging
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup, option

from core.permissions import requires_tier
from core.ui import ui_embed, ui_error, ui_success, ui_info
from db.repos.management import add_reaction_role, delete_reaction_role, get_reaction_roles_for_message

log = logging.getLogger("Nexus.ReactionRoles")


class PersistentReactionRoleButton(discord.ui.Button):
    def __init__(self, role_id: int, label: str = None, emoji: str = None, style: discord.ButtonStyle = discord.ButtonStyle.primary):
        super().__init__(
            label=label or "Get Role",
            emoji=emoji,
            style=style,
            custom_id=f"rr:toggle:{role_id}",
        )


class ReactionRolesCog(commands.Cog, name="ReactionRoles"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    rr_group = SlashCommandGroup("reactionrole", "Create and manage interactive button reaction roles")

    # ── Slash: /reactionrole panel ────────────────────────────────────────────
    @rr_group.command(name="panel", description="Send a reaction role panel with buttons")
    @requires_tier("staff")
    @option("title", description="Title for the reaction role panel")
    @option("description", description="Description / instructions for members")
    @option("role1", description="First role to include")
    @option("role2", description="Second role (optional)", required=False)
    @option("role3", description="Third role (optional)", required=False)
    @option("role4", description="Fourth role (optional)", required=False)
    @option("role5", description="Fifth role (optional)", required=False)
    @option("channel", description="Channel to send the panel in (default: current)", required=False)
    async def slash_rr_panel(
        self,
        ctx: discord.ApplicationContext,
        title: str,
        description: str,
        role1: discord.Role,
        role2: discord.Role = None,
        role3: discord.Role = None,
        role4: discord.Role = None,
        role5: discord.Role = None,
        channel: discord.TextChannel = None,
    ):
        target_ch = channel or ctx.channel
        roles = [r for r in [role1, role2, role3, role4, role5] if r is not None]

        # Verify role hierarchy
        for r in roles:
            if r >= ctx.guild.me.top_role:
                return await ctx.respond(
                    embed=ui_error("Hierarchy Error", f"I cannot assign {r.mention} because it is equal to or higher than my highest role."),
                    ephemeral=True,
                )

        view = discord.ui.View(timeout=None)
        styles = [
            discord.ButtonStyle.primary,
            discord.ButtonStyle.secondary,
            discord.ButtonStyle.success,
            discord.ButtonStyle.primary,
            discord.ButtonStyle.secondary,
        ]

        embed_lines = [description, ""]
        for idx, r in enumerate(roles):
            view.add_item(PersistentReactionRoleButton(role_id=r.id, label=r.name, style=styles[idx % len(styles)]))
            embed_lines.append(f"• Click **{r.name}** to get or remove the {r.mention} role")

        embed = ui_embed(title=f"🎭 {title}", description="\n".join(embed_lines), color=0x5865F2)
        embed.set_footer(text="Click any button to toggle your role!")

        sent_msg = await target_ch.send(embed=embed, view=view)

        # Store in database
        for r in roles:
            await add_reaction_role(
                guild_id=ctx.guild.id,
                channel_id=target_ch.id,
                message_id=sent_msg.id,
                role_id=r.id,
                label=r.name,
            )

        await ctx.respond(
            embed=ui_success("Reaction Role Panel Created", f"Successfully created reaction role panel in {target_ch.mention}!"),
            ephemeral=True,
        )

    # ── Prefix: n!reactionrole ────────────────────────────────────────────────
    @commands.command(name="reactionrole", aliases=["rr"])
    @requires_tier("staff")
    async def prefix_reactionrole(self, ctx: commands.Context, role: discord.Role = None, *, label: str = None):
        if not role:
            return await ctx.reply(
                embed=ui_info(
                    "Reaction Roles Usage",
                    f"`{ctx.prefix}reactionrole <@role> [label]` — Quickly creates a single-role button panel.\n"
                    f"Use `/reactionrole panel` for up to 5 roles with custom title & description."
                )
            )

        if role >= ctx.guild.me.top_role:
            return await ctx.reply(
                embed=ui_error("Hierarchy Error", f"I cannot assign {role.mention} because it is equal to or higher than my highest role.")
            )

        btn_label = label or role.name
        view = discord.ui.View(timeout=None)
        view.add_item(PersistentReactionRoleButton(role_id=role.id, label=btn_label))

        embed = ui_embed(
            title=f"🎭 Role Assignment: {role.name}",
            description=f"Click the button below to claim or remove the {role.mention} role.",
            color=0x5865F2,
        )
        msg = await ctx.send(embed=embed, view=view)
        await add_reaction_role(
            guild_id=ctx.guild.id,
            channel_id=ctx.channel.id,
            message_id=msg.id,
            role_id=role.id,
            label=btn_label,
        )

    # ── Gateway Listener for Persistent Button Clicks ─────────────────────────
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        cid = interaction.data.get("custom_id", "")
        if not cid.startswith("rr:toggle:"):
            return

        parts = cid.split(":")
        if len(parts) < 3:
            return

        try:
            role_id = int(parts[2])
        except ValueError:
            return

        guild = interaction.guild
        if not guild:
            return

        role = guild.get_role(role_id)
        if not role:
            return await interaction.response.send_message(
                embed=ui_error("Role Not Found", "The role associated with this button no longer exists."),
                ephemeral=True,
            )

        member = interaction.user
        if not isinstance(member, discord.Member):
            member = guild.get_member(member.id)
            if not member:
                return

        if role >= guild.me.top_role:
            return await interaction.response.send_message(
                embed=ui_error("Permission Error", "I lack permission to assign or remove this role."),
                ephemeral=True,
            )

        # Toggle role
        if role in member.roles:
            try:
                await member.remove_roles(role, reason="Nexus Reaction Role button toggle")
                await interaction.response.send_message(
                    embed=ui_info("Role Removed", f"Removed the **{role.name}** role from your profile."),
                    ephemeral=True,
                )
            except Exception as e:
                await interaction.response.send_message(f"❌ Failed to remove role: {e}", ephemeral=True)
        else:
            try:
                await member.add_roles(role, reason="Nexus Reaction Role button toggle")
                await interaction.response.send_message(
                    embed=ui_success("Role Added", f"Added the **{role.name}** role to your profile!"),
                    ephemeral=True,
                )
            except Exception as e:
                await interaction.response.send_message(f"❌ Failed to add role: {e}", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(ReactionRolesCog(bot))
