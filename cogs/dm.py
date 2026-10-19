"""
DM Cog — Dedicated Direct Messaging System
Features:
  /dm-user — Interactive popup modal to send rich formatted DMs with action buttons to a member
  /dm      — Convenient alias for /dm-user
  /dm-role — Interactive popup modal to broadcast rich formatted DMs to an entire role
"""

import discord
from discord.ext import commands
from discord import option
import aiosqlite
import asyncio
from pathlib import Path

DB_PATH = Path("nexus.db")
GLOBAL_OWNER_ID = 1201050377911554061

# ── Color Presets ─────────────────────────────────────────────────────────────
COLOR_PRESETS = {
    "blurple": 0x5865F2,
    "blue":    0x3498DB,
    "red":     0xED4245,
    "green":   0x57F287,
    "gold":    0xFEE75C,
    "yellow":  0xFFFF00,
    "purple":  0x9B59B6,
    "fuchsia": 0xEB459E,
    "pink":    0xFF70A6,
    "cyan":    0x1ABC9C,
    "teal":    0x008080,
    "orange":  0xE67E22,
    "black":   0x23272A,
    "dark":    0x2B2D31,
    "white":   0xFFFFFF,
}


def parse_color(color_val: str, default: int = 0x5865F2) -> int:
    """Parses color names (e.g. 'gold', 'red') or hex codes (e.g. '#5865F2')."""
    if not color_val:
        return default
    cleaned = color_val.strip().lower()
    if cleaned in COLOR_PRESETS:
        return COLOR_PRESETS[cleaned]
    clean_hex = cleaned.lstrip("#")
    try:
        return int(clean_hex, 16)
    except ValueError:
        return default


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


async def get_config(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM guild_config WHERE guild_id=?", (guild_id,)) as cur:
            row = await cur.fetchone()
        if row is None:
            await db.execute("INSERT INTO guild_config (guild_id) VALUES (?)", (guild_id,))
            await db.commit()
            async with db.execute("SELECT * FROM guild_config WHERE guild_id=?", (guild_id,)) as cur:
                row = await cur.fetchone()
        return dict(row)


async def is_bot_admin(ctx) -> bool:
    """Server owner, global owner, non-prefix user, or member with the configured bot-role."""
    if ctx.author.id == GLOBAL_OWNER_ID:
        return True
    if hasattr(ctx, "bot") and ctx.author.id in getattr(ctx.bot, "non_prefix_users", set()):
        return True
    if ctx.guild is None:
        return False
    if ctx.author.id == ctx.guild.owner_id:
        return True
    cfg = await get_config(ctx.guild.id)
    role_id = cfg.get("bot_role_id")
    if role_id:
        member = ctx.guild.get_member(ctx.author.id) or ctx.author
        if hasattr(member, "roles"):
            return any(r.id == role_id for r in member.roles)
    return False


async def no_perm(ctx):
    """Ephemeral 'ask server owner for bot role' response."""
    if ctx.guild is None:
        embed = discord.Embed(
            title="🔒 Access Denied",
            description="Commands can only be used inside a server.",
            color=0xED4245,
        )
        if hasattr(ctx, "respond"):
            return await ctx.respond(embed=embed, ephemeral=True)
        return await ctx.reply(embed=embed)

    cfg = await get_config(ctx.guild.id)
    role_id  = cfg.get("bot_role_id")
    bot_role = ctx.guild.get_role(role_id) if role_id else None
    tip = (
        f"You need the **{bot_role.name}** role to use bot commands.\n"
        "Please ask the **server owner** to grant you this role."
        if bot_role else
        "You don't have permission to use bot commands.\n"
        "Please ask the **server owner** to assign a bot-role using `/set-botrole`."
    )
    embed = discord.Embed(title="🔒 Bot-Role Required", description=tip, color=0xED4245)
    if hasattr(ctx, "respond"):
        await ctx.respond(embed=embed, ephemeral=True)
    else:
        await ctx.reply(embed=embed, delete_after=15)


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

        sent, failed = 0, 0
        for m in members:
            try:
                await m.send(embed=dm_embed, view=button_view)
                sent += 1
                await asyncio.sleep(0.35)
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
