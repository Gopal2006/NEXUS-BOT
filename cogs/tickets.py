"""
Tickets Cog
Commands:
  /ticket setup     — post the ticket creation panel in a channel
  /ticket set-role  — assign which role handles support tickets
  /ticket close     — close the current ticket (restricted to staff/bot-role)
  /ticket add       — add a user to the ticket channel
  /ticket remove    — remove a user from the ticket channel

Feature: ticket creation shows a modal asking for issue details
         so staff have full context when they open the channel.
"""

import io
import discord
from discord.ext import commands
from discord import option
import asyncio
from pathlib import Path

from core.config import is_bot_owner
from core.permissions import has_tier_permission, send_no_permission
from db.database import get_config, set_config, get_db

async def is_bot_admin(ctx) -> bool:
    return await has_tier_permission(ctx, tier="staff")

async def can_close_ticket(member: discord.Member, guild: discord.Guild) -> bool:
    if is_bot_owner(member.id) or member.id == guild.owner_id:
        return True
    cfg = await get_config(guild.id)
    bot_role_id    = cfg.get("bot_role_id")
    ticket_role_id = cfg.get("ticket_role_id")
    user_roles = [r.id for r in member.roles]
    if bot_role_id and bot_role_id in user_roles:
        return True
    if ticket_role_id and ticket_role_id in user_roles:
        return True
    return False

async def no_perm(ctx):
    return await send_no_permission(ctx)



async def log_activity(guild: discord.Guild, embed: discord.Embed, file: discord.File = None):
    cfg = await get_config(guild.id)
    ch_id = cfg.get("activity_log_ch") or cfg.get("mod_log_ch") or cfg.get("log_ch")
    if not ch_id:
        return
    ch = guild.get_channel(ch_id)
    if ch:
        try:
            if file:
                await ch.send(embed=embed, file=file)
            else:
                await ch.send(embed=embed)
        except Exception:
            pass


# ── Ticket Intake Modal ───────────────────────────────────────────────────────
class TicketIntakeModal(discord.ui.Modal):
    """
    Shown when a member clicks 'Open a Ticket'.
    Collects structured info so staff have full context on arrival.
    """

    def __init__(self, guild: discord.Guild, member: discord.Member):
        super().__init__(title="📋 Open a Support Ticket")
        self.guild  = guild
        self.member = member

        self.add_item(discord.ui.InputText(
            label="What do you need help with?",
            placeholder="Describe your issue or request in a few words…",
            style=discord.InputTextStyle.short,
            max_length=100,
            custom_id="ticket_subject",
        ))
        self.add_item(discord.ui.InputText(
            label="Please describe your issue in detail",
            placeholder="Give as much information as possible so our staff can help you quickly.",
            style=discord.InputTextStyle.long,
            max_length=1000,
            custom_id="ticket_description",
        ))
        self.add_item(discord.ui.InputText(
            label="Priority level",
            placeholder="Low / Medium / High / Urgent",
            style=discord.InputTextStyle.short,
            max_length=20,
            required=False,
            custom_id="ticket_priority",
        ))
        self.add_item(discord.ui.InputText(
            label="Any additional information?",
            placeholder="Order IDs, usernames, screenshots you'll share, or anything else relevant…",
            style=discord.InputTextStyle.long,
            max_length=500,
            required=False,
            custom_id="ticket_extra",
        ))

    async def callback(self, interaction: discord.Interaction):
        subject     = self.children[0].value
        description = self.children[1].value
        priority    = self.children[2].value or "Not specified"
        extra       = self.children[3].value or "None"

        await interaction.response.defer(ephemeral=True)

        guild  = interaction.guild
        member = interaction.user
        cfg    = await get_config(guild.id)

        # Find or create Tickets category
        category = discord.utils.get(guild.categories, name="🎫 Tickets")
        if not category:
            category = await guild.create_category("🎫 Tickets")

        # Overwrites
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(
                view_channel=True, read_messages=True, send_messages=True,
                attach_files=True, read_message_history=True,
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, read_messages=True, send_messages=True,
                manage_channels=True, embed_links=True, attach_files=True,
                read_message_history=True,
            ),
        }

        bot_role_id = cfg.get("bot_role_id")
        if bot_role_id:
            bot_role = guild.get_role(bot_role_id)
            if bot_role:
                overwrites[bot_role] = discord.PermissionOverwrite(
                    view_channel=True, read_messages=True, send_messages=True,
                    attach_files=True, read_message_history=True,
                )

        ticket_role_id = cfg.get("ticket_role_id")
        ticket_role    = None
        if ticket_role_id:
            ticket_role = guild.get_role(ticket_role_id)
            if ticket_role:
                overwrites[ticket_role] = discord.PermissionOverwrite(
                    view_channel=True, read_messages=True, send_messages=True,
                    attach_files=True, read_message_history=True,
                )

        ch_name = f"ticket-{member.name.lower()[:15]}"
        ch = await guild.create_text_channel(
            ch_name,
            category=category,
            overwrites=overwrites,
            topic=f"Support ticket for {member} ({member.id}) — {subject}",
        )

        db = await get_db()
        await db.execute(
            "INSERT INTO tickets (guild_id, channel_id, user_id, status) VALUES (?,?,?,'open')",
            (guild.id, ch.id, member.id),
        )
        await db.commit()

        # ── Ticket welcome embed with full intake details ──────────────────────
        priority_colors = {
            "low": "🟢", "medium": "🟡", "high": "🟠", "urgent": "🔴",
        }
        priority_icon = priority_colors.get(priority.lower().strip(), "⚪")

        welcome_embed = discord.Embed(
            title=f"🎫 Ticket — {subject}",
            color=0x5865F2,
            timestamp=discord.utils.utcnow(),
        )
        welcome_embed.set_author(
            name=f"{member.display_name} opened a ticket",
            icon_url=member.display_avatar.url,
        )
        welcome_embed.add_field(name="👤 Member",      value=member.mention,              inline=True)
        welcome_embed.add_field(name="🆔 User ID",     value=f"`{member.id}`",            inline=True)
        welcome_embed.add_field(name="\u200b",          value="\u200b",                    inline=True)
        welcome_embed.add_field(name="📌 Subject",     value=subject,                     inline=False)
        welcome_embed.add_field(name="📋 Description", value=description,                 inline=False)
        welcome_embed.add_field(name=f"{priority_icon} Priority", value=priority,         inline=True)
        welcome_embed.add_field(name="📎 Extra Info",  value=extra,                       inline=False)
        welcome_embed.set_footer(text=f"Ticket Channel ID: {ch.id}  •  Nexus Support System")

        mention_content = f"{member.mention}"
        if ticket_role:
            mention_content += f" | {ticket_role.mention}"

        await ch.send(content=mention_content, embed=welcome_embed, view=TicketCloseButton())

        await interaction.followup.send(
            embed=discord.Embed(
                title="✅ Ticket Created",
                description=f"Your support ticket has been opened: {ch.mention}\n\nA staff member will assist you shortly.",
                color=0x57F287,
            ),
            ephemeral=True,
        )

        # Log to activity log
        log_embed = discord.Embed(
            title="🎫 New Support Ticket",
            color=0x00B0FF,
            timestamp=discord.utils.utcnow(),
        )
        log_embed.add_field(name="👤 Creator",    value=f"{member.mention} (`{member.id}`)", inline=True)
        log_embed.add_field(name="📁 Channel",    value=ch.mention,                          inline=True)
        log_embed.add_field(name="📌 Subject",    value=subject,                             inline=False)
        log_embed.add_field(name=f"{priority_icon} Priority", value=priority,                inline=True)
        log_embed.set_footer(text="Nexus Ticket Audit")
        await log_activity(guild, log_embed)


# ── Ticket Open Button ─────────────────────────────────────────────────────────
class TicketOpenButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Open a Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="nexus:ticket_open",
    )
    async def open_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        guild  = interaction.guild
        member = interaction.user

        # Check existing open ticket
        db = await get_db()
        async with db.execute(
            "SELECT * FROM tickets WHERE guild_id=? AND user_id=? AND status='open'",
            (guild.id, member.id),
        ) as cur:
            existing = await cur.fetchone()

        if existing:
            ch = guild.get_channel(existing["channel_id"])
            if ch:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        description=f"❌ You already have an open ticket: {ch.mention}",
                        color=0xED4245,
                    ),
                    ephemeral=True,
                )

        # Show intake modal — no defer needed before send_modal
        await interaction.response.send_modal(TicketIntakeModal(guild, member))


# Alias for dashboard compatibility
TicketLaunchView = TicketOpenButton



# ── Ticket Close Button ───────────────────────────────────────────────────────
class TicketCloseButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="nexus:ticket_close",
    )
    async def close_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await can_close_ticket(interaction.user, interaction.guild):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ Only members with the **Bot-Role** or **Ticket-Role** can close tickets.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )

        await interaction.response.send_message("🔒 Closing ticket…", ephemeral=True)
        await _close_ticket(interaction.channel, interaction.guild, interaction.user)


async def _close_ticket(channel: discord.TextChannel, guild: discord.Guild, closer: discord.Member):
    ticket_user_id = None
    db = await get_db()
    async with db.execute("SELECT * FROM tickets WHERE channel_id=?", (channel.id,)) as cur:
        row = await cur.fetchone()
        if row:
            ticket_user_id = row["user_id"]

    await db.execute("UPDATE tickets SET status='closed' WHERE channel_id=?", (channel.id,))
    await db.commit()

    embed = discord.Embed(
        title="🔒 Ticket Closed",
        description=f"Ticket closed by {closer.mention}.\nThis channel will be deleted in **5 seconds**.",
        color=0xED4245,
        timestamp=discord.utils.utcnow(),
    )
    embed.set_footer(text="Nexus Support System")
    await channel.send(embed=embed)

    # ── Generate full transcript ──────────────────────────────────────────────
    transcript_lines = [
        f"=== NEXUS TICKET TRANSCRIPT ===",
        f"Channel: #{channel.name} ({channel.id})",
        f"Guild: {guild.name} ({guild.id})",
        f"Closed By: {closer} ({closer.id})",
        f"Closed At: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "=" * 40,
        "",
    ]
    try:
        async for m in channel.history(limit=500, oldest_first=True):
            ts = m.created_at.strftime("%Y-%m-%d %H:%M:%S")
            att = f" [Attachment: {m.attachments[0].url}]" if m.attachments else ""
            transcript_lines.append(f"[{ts}] {m.author} ({m.author.id}): {m.content}{att}")
    except Exception:
        pass

    transcript_bytes = "\n".join(transcript_lines).encode("utf-8")
    log_file = discord.File(io.BytesIO(transcript_bytes), filename=f"transcript-{channel.name}.txt")

    # Activity log
    log_embed = discord.Embed(
        title="🔒 Support Ticket Closed",
        color=0xED4245,
        timestamp=discord.utils.utcnow(),
    )
    log_embed.add_field(name="🛡️ Closed By",    value=f"{closer.mention} (`{closer.id}`)", inline=True)
    if ticket_user_id:
        log_embed.add_field(name="👤 Ticket Owner", value=f"<@{ticket_user_id}> (`{ticket_user_id}`)", inline=True)
    log_embed.add_field(name="📁 Channel",       value=f"`#{channel.name}`", inline=True)
    log_embed.set_footer(text="Nexus Ticket Audit • Transcript Attached")
    await log_activity(guild, log_embed, file=log_file)

    # DM transcript to ticket owner if accessible
    if ticket_user_id:
        try:
            owner = guild.get_member(ticket_user_id) or await guild.fetch_member(ticket_user_id)
            if owner:
                dm_file = discord.File(io.BytesIO(transcript_bytes), filename=f"transcript-{channel.name}.txt")
                dm_embed = discord.Embed(
                    title="🎫 Support Ticket Closed",
                    description=f"Your ticket **#{channel.name}** in **{guild.name}** was closed by {closer.mention}.\nAttached is your full ticket transcript for your records.",
                    color=0x5865F2,
                )
                await owner.send(embed=dm_embed, file=dm_file)
        except Exception:
            pass

    await asyncio.sleep(5)
    try:
        await channel.delete(reason=f"Ticket closed by {closer}")
    except Exception:
        pass



class Tickets(commands.Cog):
    """🎫 Ticket support system."""

    def __init__(self, bot):
        self.bot = bot
        bot.add_view(TicketOpenButton())
        bot.add_view(TicketCloseButton())

    ticket_group = discord.SlashCommandGroup("ticket", "Ticket system commands")

    # ── /ticket setup ─────────────────────────────────────────────────────────
    @ticket_group.command(name="setup", description="Post the ticket creation panel")
    @option("channel",     discord.TextChannel, description="Channel to post the panel in")
    @option("title",       str, description="Panel title",       required=False, default="🎫 Support Tickets")
    @option("description", str, description="Panel description", required=False,
            default="Click the button below to open a private support ticket. A modal will ask for details so our staff can help you right away.")
    @option("color", str, description="Hex color for the embed", required=False, default="#5865F2")
    async def ticket_setup(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel,
        title: str = "🎫 Support Tickets",
        description: str = "Click the button below to open a private support ticket. A modal will ask for details so our staff can help you right away.",
        color: str = "#5865F2",
    ):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        try:
            color_int = int(color.lstrip("#"), 16)
        except ValueError:
            color_int = 0x5865F2

        embed = discord.Embed(title=title, description=description, color=color_int)
        embed.set_footer(text="Nexus Support System  •  Your information stays private")
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        await channel.send(embed=embed, view=TicketOpenButton())
        await ctx.respond(
            embed=discord.Embed(
                description=f"✅ Ticket panel sent to {channel.mention}!",
                color=0x57F287,
            ),
            ephemeral=True,
        )

    # ── /ticket set-role ──────────────────────────────────────────────────────
    @ticket_group.command(name="set-role", description="Set the support staff role for tickets (Server Owner only)")
    @option("role", discord.Role, description="Staff role to assign for ticket support")
    async def ticket_set_role(self, ctx: discord.ApplicationContext, role: discord.Role):
        if ctx.author.id != ctx.guild.owner_id and not is_bot_owner(ctx.author.id):
            return await ctx.respond(
                embed=discord.Embed(
                    title="🔒 Server Owner Only",
                    description="Only the **server owner** can assign the ticket support staff role.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )
        await set_config(ctx.guild.id, ticket_role_id=role.id)
        embed = discord.Embed(
            title="✅ Ticket Support Role Assigned",
            description=(
                f"Members with {role.mention} will now be automatically added to all new "
                "support tickets and have permission to manage and close them."
            ),
            color=0x57F287,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(text=f"Assigned by {ctx.author.name}")
        await ctx.respond(embed=embed)

    # ── /ticket remove-role ───────────────────────────────────────────────────
    @ticket_group.command(name="remove-role", description="Remove the ticket support staff role (Server Owner only)")
    async def ticket_remove_role(self, ctx: discord.ApplicationContext):
        if ctx.author.id != ctx.guild.owner_id and not is_bot_owner(ctx.author.id):
            return await ctx.respond(
                embed=discord.Embed(
                    title="🔒 Server Owner Only",
                    description="Only the **server owner** can remove the ticket support staff role.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )
        await set_config(ctx.guild.id, ticket_role_id=None)
        await ctx.respond(
            embed=discord.Embed(
                title="✅ Ticket Support Role Removed",
                description="The ticket support role restriction has been cleared. Only the Server Owner and Bot-Role holders will have default access.",
                color=0x57F287,
            ),
            ephemeral=True,
        )

    # ── /ticket close ─────────────────────────────────────────────────────────
    @ticket_group.command(name="close", description="Close the current ticket channel")
    async def ticket_close(self, ctx: discord.ApplicationContext):
        if not await can_close_ticket(ctx.author, ctx.guild):
            return await ctx.respond(
                embed=discord.Embed(
                    title="🔒 Access Denied",
                    description="❌ Only staff members (holding the Bot-Role or Ticket-Role) and the Server Owner can close tickets.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )

        db = await get_db()
        async with db.execute(
            "SELECT * FROM tickets WHERE channel_id=? AND status='open'", (ctx.channel.id,)
        ) as cur:
            ticket = await cur.fetchone()

        if not ticket:
            return await ctx.respond(
                embed=discord.Embed(
                    description="❌ This channel is not an active support ticket.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )

        await ctx.respond(embed=discord.Embed(description="🔒 Closing ticket…", color=0xFEE75C))
        await _close_ticket(ctx.channel, ctx.guild, ctx.author)

    # ── /ticket add ───────────────────────────────────────────────────────────
    @ticket_group.command(name="add", description="Add a member to the current ticket")
    @option("member", discord.Member, description="Member to add")
    async def ticket_add(self, ctx: discord.ApplicationContext, member: discord.Member):
        if not await can_close_ticket(ctx.author, ctx.guild):
            return await no_perm(ctx)
        await ctx.channel.set_permissions(
            member, read_messages=True, send_messages=True, attach_files=True
        )
        await ctx.respond(
            embed=discord.Embed(
                description=f"✅ {member.mention} has been added to the ticket.",
                color=0x57F287,
            )
        )

    # ── /ticket remove ────────────────────────────────────────────────────────
    @ticket_group.command(name="remove", description="Remove a member from the current ticket")
    @option("member", discord.Member, description="Member to remove")
    async def ticket_remove(self, ctx: discord.ApplicationContext, member: discord.Member):
        if not await can_close_ticket(ctx.author, ctx.guild):
            return await no_perm(ctx)
        await ctx.channel.set_permissions(member, overwrite=None)
        await ctx.respond(
            embed=discord.Embed(
                description=f"✅ {member.mention} has been removed from the ticket.",
                color=0x57F287,
            )
        )

    # ── Prefix: n!ticket close / add / remove ─────────────────────────────────
    @commands.group(name="ticket", invoke_without_command=True)
    async def prefix_ticket(self, ctx: commands.Context):
        if not await can_close_ticket(ctx.author, ctx.guild):
            return await no_perm(ctx)
        await ctx.reply("ℹ️ Usage: `n!ticket close`, `n!ticket add <@member>`, `n!ticket remove <@member>`")

    @prefix_ticket.command(name="close")
    async def prefix_ticket_close(self, ctx: commands.Context):
        if not await can_close_ticket(ctx.author, ctx.guild):
            return await ctx.reply("❌ Only staff members and the Server Owner have permission to close tickets.")
        db = await get_db()
        async with db.execute(
            "SELECT * FROM tickets WHERE channel_id=? AND status='open'", (ctx.channel.id,)
        ) as cur:
            ticket = await cur.fetchone()
        if not ticket:
            return await ctx.reply("❌ This channel is not an active support ticket.")
        await ctx.reply("🔒 Closing ticket…")
        await _close_ticket(ctx.channel, ctx.guild, ctx.author)

    @prefix_ticket.command(name="add")
    async def prefix_ticket_add(self, ctx: commands.Context, member: discord.Member):
        if not await can_close_ticket(ctx.author, ctx.guild):
            return await no_perm(ctx)
        await ctx.channel.set_permissions(member, read_messages=True, send_messages=True, attach_files=True)
        await ctx.reply(f"✅ Added {member.mention} to the ticket.")

    @prefix_ticket.command(name="remove")
    async def prefix_ticket_remove(self, ctx: commands.Context, member: discord.Member):
        if not await can_close_ticket(ctx.author, ctx.guild):
            return await no_perm(ctx)
        await ctx.channel.set_permissions(member, overwrite=None)
        await ctx.reply(f"✅ Removed {member.mention} from the ticket.")


def setup(bot):
    bot.add_cog(Tickets(bot))
