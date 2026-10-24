"""
Announcements Cog — Dedicated Announcement System
Features:
  /announce — Interactive popup modal with Title, Message, Color Theme, Banner, Thumbnail, Ping, and Clickable Action Buttons
"""

import discord
from discord.ext import commands
from discord import option
import aiohttp
import io
from pathlib import Path

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


async def fetch_image_file(url: str) -> discord.File | None:
    """Download an image from a URL into a discord.File so it can be sent natively without raw URL pills."""
    if not url:
        return None
    try:
        clean_url = url.split("?")[0]
        fname = clean_url.split("/")[-1]
        valid_exts = (".png", ".jpg", ".jpeg", ".gif", ".webp")
        if not any(fname.lower().endswith(ext) for ext in valid_exts):
            fname = "announcement.png"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    if data:
                        return discord.File(io.BytesIO(data), filename=fname)
    except Exception:
        pass
    return None


# ── Announcement Modal ────────────────────────────────────────────────────────
class AnnouncementModal(discord.ui.Modal):
    """
    Interactive modal popup for creating announcements with rich formatting or plain text.
    Collects Title, Message, Color Theme, Banner Image, and Action Button.
    """

    def __init__(
        self,
        target_channel: discord.TextChannel,
        ping: str = None,
        thumbnail: str = None,
        as_embed: bool = True,
        initial_image: str = None,
        initial_attachment: discord.Attachment = None,
    ):
        modal_title = "📢 Create Announcement (Embed)" if as_embed else "📢 Create Announcement (Plain Text)"
        super().__init__(title=modal_title)
        self.target_channel = target_channel
        self.ping = ping
        self.thumbnail = thumbnail
        self.as_embed = as_embed
        self.initial_image = initial_image
        self.initial_attachment = initial_attachment

        self.add_item(discord.ui.InputText(
            label="Announcement Title (Optional)",
            placeholder="e.g. 📢 Important Community Update!",
            style=discord.InputTextStyle.short,
            max_length=256,
            required=False,
            custom_id="ann_title",
        ))
        self.add_item(discord.ui.InputText(
            label="Announcement Message (Optional)",
            placeholder="Write your announcement details here… (leave empty for photo-only)",
            style=discord.InputTextStyle.long,
            max_length=4000,
            required=False,
            custom_id="ann_message",
        ))
        self.add_item(discord.ui.InputText(
            label="Embed Color / Theme (Optional)" if as_embed else "Theme Tag / Subtitle (Optional)",
            placeholder="e.g. gold, red, green, blue, purple, or #5865F2" if as_embed else "Ignored in plain text format",
            style=discord.InputTextStyle.short,
            max_length=25,
            required=False,
            custom_id="ann_color",
        ))
        self.add_item(discord.ui.InputText(
            label="Banner / Photo Image URL (Optional)",
            placeholder="https://example.com/banner.png",
            value=self.initial_image,
            style=discord.InputTextStyle.short,
            max_length=500,
            required=False,
            custom_id="ann_image",
        ))
        self.add_item(discord.ui.InputText(
            label="Action Button (Optional)",
            placeholder="e.g. Visit Website | https://example.com",
            style=discord.InputTextStyle.short,
            max_length=250,
            required=False,
            custom_id="ann_button",
        ))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        title       = (self.children[0].value or "").strip() or None
        message     = (self.children[1].value or "").strip() or None
        color_val   = (self.children[2].value or "").strip()
        image_url   = (self.children[3].value or "").strip() or None
        button_val  = (self.children[4].value or "").strip() or None

        if not title and not message and not image_url:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Empty Announcement",
                    description="Please provide at least an **Announcement Title**, **Message**, or **Image URL**.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )

        color_int = parse_color(color_val, default=0x5865F2)

        content = None
        if self.ping and self.ping.lower() != "none":
            pv = self.ping.strip().lower()
            if pv in ("@everyone", "everyone"):
                content = "@everyone"
            elif pv in ("@here", "here"):
                content = "@here"
            else:
                clean_id = self.ping.replace("<@&", "").replace(">", "").strip()
                role = None
                if clean_id.isdigit():
                    role = interaction.guild.get_role(int(clean_id))
                if not role:
                    role = discord.utils.find(lambda r: r.name.lower() == self.ping.lower(), interaction.guild.roles)
                content = role.mention if role else self.ping

        button_view = build_button_view(button_val)

        # Download or convert image to a native discord.File attachment
        # This completely eliminates the ugly [📎 filename.png] text link pills!
        img_file = None
        if self.initial_attachment and (not image_url or image_url == self.initial_attachment.url):
            try:
                img_file = await self.initial_attachment.to_file()
            except Exception:
                img_file = None

        if not img_file and image_url:
            img_file = await fetch_image_file(image_url)

        try:
            if self.as_embed:
                embed = discord.Embed(
                    title=title,
                    description=message,
                    color=color_int,
                    timestamp=discord.utils.utcnow(),
                )
                if img_file:
                    embed.set_image(url=f"attachment://{img_file.filename}")
                elif image_url:
                    embed.set_image(url=image_url)

                # Thumbnail: user-provided or fallback to server icon if text content exists
                thumb_url = self.thumbnail
                if not thumb_url and (title or message):
                    thumb_url = interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None
                if thumb_url:
                    embed.set_thumbnail(url=thumb_url)

                embed.set_footer(
                    text=f"Announced by {interaction.user.display_name}",
                    icon_url=interaction.user.display_avatar.url,
                )

                sent_msg = await self.target_channel.send(
                    content=content,
                    embed=embed,
                    file=img_file,
                    view=button_view,
                    allowed_mentions=discord.AllowedMentions.all()
                )
            else:
                # Plain text format (no embed)
                body_parts = []
                if title:
                    body_parts.append(f"# {title}")
                if message:
                    body_parts.append(message)

                # If the image was converted to a native file, do NOT put image_url in text
                # That completely avoids Discord creating the [📎 filename.png] link chip!
                if not img_file and image_url:
                    body_parts.append(image_url)

                if title and message:
                    body = f"# {title}\n{message}"
                else:
                    body = "\n".join(body_parts)

                # Single newline between ping and content eliminates the empty line gap
                if content and body:
                    plain_content = f"{content}\n{body}"
                elif content:
                    plain_content = content
                else:
                    plain_content = body or None

                sent_msg = await self.target_channel.send(
                    content=plain_content,
                    file=img_file,
                    view=button_view,
                    allowed_mentions=discord.AllowedMentions.all()
                )
        except discord.Forbidden:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Missing Permissions",
                    description=f"I don't have permission to post messages in {self.target_channel.mention}.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )
        except Exception as e:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Error Sending Announcement",
                    description=f"Could not send announcement: `{e}`",
                    color=0xED4245,
                ),
                ephemeral=True,
            )

        fmt_name = "Embed" if self.as_embed else "Plain Text"
        await interaction.followup.send(
            embed=discord.Embed(
                title=f"✅ Announcement Dispatched ({fmt_name})",
                description=f"Your announcement has been posted in {self.target_channel.mention}!\n\n🔗 [Jump to Announcement]({sent_msg.jump_url})",
                color=0x57F287,
            ),
            ephemeral=True,
        )

        # Determine final image URL used (from sent message attachment or image_url)
        final_img = None
        if sent_msg and sent_msg.attachments:
            final_img = sent_msg.attachments[0].url
        elif image_url:
            final_img = image_url

        # Audit log
        log_embed = discord.Embed(
            title=f"📢 Announcement Posted ({fmt_name})",
            color=color_int if self.as_embed else 0x5865F2,
            timestamp=discord.utils.utcnow(),
        )
        log_embed.add_field(name="🛡️ Moderator", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=True)
        log_embed.add_field(name="📁 Channel",   value=self.target_channel.mention, inline=True)
        log_embed.add_field(name="📐 Format",    value=fmt_name, inline=True)
        if content:
            log_embed.add_field(name="🔔 Ping",    value=content, inline=True)
        log_embed.add_field(name="📌 Title",     value=title or "*(No Title - Photo Announcement)*", inline=False)
        if message:
            preview = message if len(message) <= 300 else message[:297] + "…"
            log_embed.add_field(name="💬 Preview",   value=f"```{preview}```", inline=False)
        if final_img:
            log_embed.set_image(url=final_img)
            log_embed.add_field(name="🖼️ Image",     value=f"[View Image]({final_img})", inline=False)
        if self.thumbnail:
            log_embed.set_thumbnail(url=self.thumbnail)
        log_embed.set_footer(text="Nexus  •  Activity Audit")
        await log_activity(interaction.guild, log_embed)


# ── Announcements Cog ─────────────────────────────────────────────────────────
class Announcements(commands.Cog):
    """📢 Announcement Tools."""

    def __init__(self, bot):
        self.bot = bot

    # ── /announce ─────────────────────────────────────────────────────────────
    @discord.slash_command(name="announce", description="Create an announcement via an interactive popup modal")
    @option("channel", discord.TextChannel, description="Channel to post in (defaults to current channel)", required=False, default=None)
    @option("embed", bool, description="Send as rich Embed (True) or plain text message (False)", required=False, default=True)
    @option("ping", str, description="Mention: @everyone, @here, or role name (optional)", required=False, default=None)
    @option("image", discord.Attachment, description="Upload an image/photo to announce (optional)", required=False, default=None)
    @option("thumbnail", str, description="Thumbnail / icon URL (optional, embed only)", required=False, default=None)
    async def announce(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel = None,
        embed: bool = True,
        ping: str = None,
        image: discord.Attachment = None,
        thumbnail: str = None,
    ):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)

        target_ch = channel or ctx.channel
        initial_img = image.url if image else None
        modal = AnnouncementModal(
            target_channel=target_ch,
            ping=ping,
            thumbnail=thumbnail,
            as_embed=embed,
            initial_image=initial_img,
            initial_attachment=image,
        )
        await ctx.send_modal(modal)


def setup(bot):
    bot.add_cog(Announcements(bot))
