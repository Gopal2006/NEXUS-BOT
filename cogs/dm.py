"""
DM Cog — Dedicated Direct Messaging System
Features:
  /dm-user — Interactive popup modal to send rich formatted DMs with action buttons to a member
  /dm      — Convenient alias for /dm-user
  /dm-role — Interactive popup modal to broadcast rich formatted DMs to an entire role
"""

import asyncio
import discord
from discord.ext import commands
from discord import option
from core.permissions import has_tier_permission, send_no_permission
from db.database import get_config
from core.ui import COLOR_PRESETS, parse_color

def build_button_view(button_str: str) -> discord.ui.View | None:
    """Constructs a clickable Link Button View if formatted as 'Label | URL' or 'URL'."""
    if not button_str:
        return None
    raw = button_str.strip()
    if "|" in raw:
        parts = raw.split("|", 1)
        label = parts[0].strip()[:80]
        url   = parts[1].strip()
    else:
        label = "Visit Link"
        url   = raw

    if not (url.startswith("http://") or url.startswith("https://") or url.startswith("discord://")):
        return None

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label=label or "Visit Link", url=url, style=discord.ButtonStyle.link))
    return view

async def is_bot_admin(ctx) -> bool:
    return await has_tier_permission(ctx, tier="staff")

async def no_perm(ctx):
    return await send_no_permission(ctx)



async def log_activity(guild: discord.Guild, embed: discord.Embed):
    cfg = await get_config(guild.id)
    ch_id = cfg.get("activity_log_ch") or cfg.get("mod_log_ch") or cfg.get("log_ch")
    if not ch_id:
        return
    ch = guild.get_channel(ch_id)
    if ch:
        try:
            await ch.send(embed=embed)
        except Exception:
            pass


# ── User DM Modal ────────────────────────────────────────────────────────────
class UserDMModal(discord.ui.Modal):
    """Interactive modal popup for sending a direct message to a user."""
    def __init__(self, target_member: discord.Member):
        super().__init__(title="✉️ Send Direct Message")
        self.target_member = target_member

        self.add_item(discord.ui.InputText(
            label="Subject / Title (Optional)",
            placeholder="e.g. Important Notice from Staff",
            style=discord.InputTextStyle.short,
            max_length=256,
            required=False,
            custom_id="user_dm_title",
        ))
        self.add_item(discord.ui.InputText(
            label="Message Content",
            placeholder="Write your message here… (supports markdown, bold, links, etc.)",
            style=discord.InputTextStyle.long,
            max_length=4000,
            required=True,
            custom_id="user_dm_message",
        ))
        self.add_item(discord.ui.InputText(
            label="Embed Color / Theme (Optional)",
            placeholder="e.g. gold, red, green, blue, purple, or #5865F2",
            style=discord.InputTextStyle.short,
            max_length=25,
            required=False,
            custom_id="user_dm_color",
        ))
        self.add_item(discord.ui.InputText(
            label="Banner / Image URL (Optional)",
            placeholder="https://example.com/banner.png",
            style=discord.InputTextStyle.short,
            max_length=500,
            required=False,
            custom_id="user_dm_image",
        ))
        self.add_item(discord.ui.InputText(
            label="Action Button (Optional)",
            placeholder="e.g. Appeal Server | https://example.com",
            style=discord.InputTextStyle.short,
            max_length=250,
            required=False,
            custom_id="user_dm_button",
        ))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        title       = (self.children[0].value or "").strip() or None
        message     = self.children[1].value.strip()
        color_val   = (self.children[2].value or "").strip()
        image_url   = (self.children[3].value or "").strip() or None
        button_val  = (self.children[4].value or "").strip() or None

        color_int = parse_color(color_val, default=0x5865F2)

        guild = interaction.guild
        dm_embed = discord.Embed(
            title=title,
            description=message,
            color=color_int,
            timestamp=discord.utils.utcnow(),
        )
        if guild:
            dm_embed.set_author(
                name=f"Message from {guild.name}",
                icon_url=guild.icon.url if guild.icon else None,
            )
            dm_embed.set_footer(
                text=f"Sent via {guild.name} Staff",
                icon_url=guild.icon.url if guild.icon else None,
            )
        if image_url:
            dm_embed.set_image(url=image_url)

        button_view = build_button_view(button_val)

        dm_delivered = False
        try:
            await self.target_member.send(embed=dm_embed, view=button_view)
            dm_delivered = True
            await interaction.followup.send(
                embed=discord.Embed(
                    title="✅ Direct Message Sent",
                    description=f"Your message was successfully delivered to **{self.target_member.mention}** (`{self.target_member}`).",
                    color=0x57F287,
                ),
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ DM Failed",
                    description=f"Could not DM **{self.target_member.mention}** — their DMs may be closed or they blocked the bot.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Delivery Error",
                    description=f"An error occurred while sending the DM: `{e}`",
                    color=0xED4245,
                ),
                ephemeral=True,
            )

        if guild:
            log_embed = discord.Embed(
                title="📩 Staff DM Dispatched",
                color=0x5865F2 if dm_delivered else 0xED4245,
                timestamp=discord.utils.utcnow(),
            )
            log_embed.add_field(name="🛡️ Moderator", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=True)
            log_embed.add_field(name="👤 Recipient",  value=f"{self.target_member.mention} (`{self.target_member.id}`)", inline=True)
            log_embed.add_field(name="📋 Status",     value="✅ Delivered" if dm_delivered else "❌ Failed (DMs Closed)", inline=True)
            log_embed.add_field(name="📌 Subject",    value=title or "*(no subject)*", inline=False)
            preview = message if len(message) <= 500 else message[:497] + "…"
            log_embed.add_field(name="💬 Content",    value=f"```{preview}```", inline=False)
            if image_url:
                log_embed.set_image(url=image_url)
                log_embed.add_field(name="🖼️ Image",  value=f"[View Image]({image_url})", inline=False)
            log_embed.set_footer(text="Nexus  •  Activity Audit")
            await log_activity(guild, log_embed)


# ── Role DM Modal ────────────────────────────────────────────────────────────
class RoleDMModal(discord.ui.Modal):
    """Interactive modal popup for broadcasting a direct message to a role."""
    def __init__(self, target_role: discord.Role):
        super().__init__(title=f"📨 Broadcast DM to @{target_role.name[:25]}")
        self.target_role = target_role

        self.add_item(discord.ui.InputText(
            label="Subject / Title (Optional)",
            placeholder="e.g. Important Announcement for Staff",
            style=discord.InputTextStyle.short,
            max_length=256,
            required=False,
            custom_id="role_dm_title",
        ))
        self.add_item(discord.ui.InputText(
            label="Broadcast Message Content",
            placeholder="Write your broadcast message here… (supports markdown, bold, links, etc.)",
            style=discord.InputTextStyle.long,
            max_length=4000,
            required=True,
            custom_id="role_dm_message",
        ))
        self.add_item(discord.ui.InputText(
            label="Embed Color / Theme (Optional)",
            placeholder="e.g. gold, red, green, blue, purple, or #5865F2",
            style=discord.InputTextStyle.short,
            max_length=25,
            required=False,
            custom_id="role_dm_color",
        ))
        self.add_item(discord.ui.InputText(
            label="Banner / Image URL (Optional)",
            placeholder="https://example.com/banner.png",
            style=discord.InputTextStyle.short,
            max_length=500,
            required=False,
            custom_id="role_dm_image",
        ))
        self.add_item(discord.ui.InputText(
            label="Action Button (Optional)",
            placeholder="e.g. Join Event | https://example.com",
            style=discord.InputTextStyle.short,
            max_length=250,
            required=False,
            custom_id="role_dm_button",
        ))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        title       = (self.children[0].value or "").strip() or None
        message     = self.children[1].value.strip()
        color_val   = (self.children[2].value or "").strip()
        image_url   = (self.children[3].value or "").strip() or None
        button_val  = (self.children[4].value or "").strip() or None

        color_int = parse_color(color_val, default=0x5865F2)

        guild = interaction.guild
        dm_embed = discord.Embed(
            title=title,
            description=message,
            color=color_int,
            timestamp=discord.utils.utcnow(),
        )
        if guild:
            dm_embed.set_author(
                name=f"Message from {guild.name}",
                icon_url=guild.icon.url if guild.icon else None,
            )
            dm_embed.set_footer(
                text=f"Sent via {guild.name} Staff",
                icon_url=guild.icon.url if guild.icon else None,
            )
        if image_url:
            dm_embed.set_image(url=image_url)

        button_view = build_button_view(button_val)

        if guild and not guild.chunked:
            try:
                await guild.chunk()
            except Exception:
                pass

        members = [m for m in self.target_role.members if not m.bot]
        if not members:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="⚠️ No Members Found",
                    description=f"The role {self.target_role.mention} has no human members to DM.",
                    color=0xFEE75C,
                ),
                ephemeral=True,
            )

        # Safety cap: max 100 recipients per broadcast
        MAX_DM_ROLE_RECIPIENTS = 100
        target_members = members[:MAX_DM_ROLE_RECIPIENTS]
        sent, failed = 0, 0
        for m in target_members:
            try:
                await m.send(embed=dm_embed, view=button_view)
                sent += 1
                await asyncio.sleep(0.5)  # Throttled 500ms delay between DMs
            except Exception:
                failed += 1

        await interaction.followup.send(
            embed=discord.Embed(
                title="📨 Role Broadcast Complete",
                description=(
                    f"**Target Role:** {self.target_role.mention}\n\n"
                    f"✅ **Delivered:** `{sent}` members\n"
                    f"❌ **Failed / DMs Closed:** `{failed}` members"
                ),
                color=0x57F287,
            ),
            ephemeral=True,
        )

        if guild:
            log_embed = discord.Embed(
                title="📨 Role DM Broadcast",
                color=0x57F287,
                timestamp=discord.utils.utcnow(),
            )
            log_embed.add_field(name="🛡️ Moderator", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=True)
            log_embed.add_field(name="👥 Target Role", value=f"{self.target_role.mention} (`{self.target_role.name}`)", inline=True)
            log_embed.add_field(name="📊 Results",     value=f"✅ `{sent}` sent | ❌ `{failed}` failed", inline=True)
            log_embed.add_field(name="📌 Subject",     value=title or "*(no subject)*", inline=False)
            preview = message if len(message) <= 500 else message[:497] + "…"
            log_embed.add_field(name="💬 Content",     value=f"```{preview}```", inline=False)
            if image_url:
                log_embed.set_image(url=image_url)
                log_embed.add_field(name="🖼️ Image",   value=f"[View Image]({image_url})", inline=False)
            log_embed.set_footer(text="Nexus  •  Activity Audit")
            await log_activity(guild, log_embed)


# ── DM Cog ────────────────────────────────────────────────────────────────────
class DMCog(commands.Cog):
    """✉️ Direct Message Tools."""

    def __init__(self, bot):
        self.bot = bot

    # ── /dm-user ──────────────────────────────────────────────────────────────
    @discord.slash_command(name="dm-user", description="Send a direct message to a member via an interactive popup modal")
    @option("member", discord.Member, description="Select the member to DM")
    async def dm_user(self, ctx: discord.ApplicationContext, member: discord.Member):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        if member.bot:
            return await ctx.respond("❌ You cannot send direct messages to bots.", ephemeral=True)
        modal = UserDMModal(target_member=member)
        await ctx.send_modal(modal)

    # ── /dm alias ─────────────────────────────────────────────────────────────
    @discord.slash_command(name="dm", description="Send a direct message to a member via an interactive popup modal")
    @option("member", discord.Member, description="Select the member to DM")
    async def dm_alias(self, ctx: discord.ApplicationContext, member: discord.Member):
        await self.dm_user(ctx, member)

    # ── /dm-role ──────────────────────────────────────────────────────────────
    @discord.slash_command(name="dm-role", description="Send a direct message to all members of a role via popup modal")
    @option("role", discord.Role, description="Select the target role")
    async def dm_role(self, ctx: discord.ApplicationContext, role: discord.Role):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        modal = RoleDMModal(target_role=role)
        await ctx.send_modal(modal)


def setup(bot):
    bot.add_cog(DMCog(bot))
