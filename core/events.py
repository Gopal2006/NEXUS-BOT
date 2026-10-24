"""
Core lifecycle events, member welcome/farewell dispatchers,
command audit logger, and bot-owner commands.
"""

import asyncio
import logging
import discord
from discord.ext import commands

from core.config import is_bot_owner, SUPPORT_SERVER, BRAND_NAME
from core.bot import disable_windows_quickedit
from db.database import get_config, add_non_prefix_user, remove_non_prefix_user
from db.repos.management import get_welcome_extras
from utils.placeholders import safe_format

log = logging.getLogger("Nexus.Events")


def setup_core_events(bot: commands.Bot):
    """Attaches core lifecycle listeners, audit logger, and owner commands to the bot."""

    # ── on_ready ──────────────────────────────────────────────────────────────
    @bot.event
    async def on_ready():
        if getattr(bot, "_ready_once", False):
            log.info(f"Reconnected as {bot.user} ({bot.user.id})")
            return
        bot._ready_once = True

        disable_windows_quickedit()
        await bot.change_presence(
            status=discord.Status.dnd,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="over the server",
            ),
        )
        log.info(f"Logged in as {bot.user} ({bot.user.id})")
        slash_count = len(bot.pending_application_commands) or len(bot.application_commands)
        log.info(f"Loaded {slash_count} slash command definition(s) ✓")

        invite_url = (
            f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"
        )
        log.info(f"Invite URL: {invite_url}")

        if not getattr(bot, "_commands_synced", False):
            bot._commands_synced = True
            asyncio.create_task(bot.sync_slash_commands_safely())

    # ── Command Audit Logging ─────────────────────────────────────────────────
    @bot.event
    async def on_command_completion(ctx: commands.Context):
        if not ctx.guild or not ctx.command:
            return

        is_non_prefix = not bool(ctx.prefix and ctx.prefix.strip())
        mode_text = "⚡ No Prefix" if is_non_prefix else f"🏷️ Prefix (`{ctx.prefix}`)"

        try:
            cfg = await get_config(ctx.guild.id)
            ch_id = (
                cfg.get("cmd_log_ch")
                or cfg.get("activity_log_ch")
                or cfg.get("mod_log_ch")
                or cfg.get("log_ch")
            )
            if not ch_id:
                return

            ch = ctx.guild.get_channel(ch_id)
            if not ch:
                try:
                    ch = await ctx.guild.fetch_channel(ch_id)
                except Exception:
                    try:
                        ch = await bot.fetch_channel(ch_id)
                    except Exception:
                        return

            cmd_name = ctx.command.qualified_name
            embed = discord.Embed(
                title="⌨️ Command Executed",
                color=0xFEE75C if is_non_prefix else 0x5865F2,
                timestamp=discord.utils.utcnow(),
            )
            if ctx.author.display_avatar:
                embed.set_author(
                    name=f"{ctx.author.display_name} ({ctx.author.name})",
                    icon_url=ctx.author.display_avatar.url,
                )
            embed.add_field(name="📌 Command", value=f"`{cmd_name}`", inline=True)
            embed.add_field(name="⚙️ Mode", value=mode_text, inline=True)
            embed.add_field(name="📁 Channel", value=ctx.channel.mention, inline=True)
            embed.add_field(
                name="👤 Executed By",
                value=f"{ctx.author.mention} (`{ctx.author.id}`)",
                inline=True,
            )

            content = ctx.message.content
            if content:
                preview = content if len(content) <= 500 else content[:497] + "…"
                embed.add_field(name="💬 Message Content", value=f"```{preview}```", inline=False)

            embed.set_footer(text=f"{BRAND_NAME}  •  Command Audit  •  Msg ID: {ctx.message.id}")
            await ch.send(embed=embed)
        except Exception as e:
            log.error(f"Failed to log command execution: {e}")

    # ── Onboarding on Guild Join ──────────────────────────────────────────────
    @bot.event
    async def on_guild_join(guild: discord.Guild):
        log.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        target_ch = guild.system_channel
        if not target_ch or not target_ch.permissions_for(guild.me).send_messages:
            target_ch = next(
                (c for c in guild.text_channels if c.permissions_for(guild.me).send_messages),
                None,
            )

        if target_ch:
            client_id = bot.user.id if bot.user else "1560655249276936192"
            reauth_url = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions=8&scope=bot%20applications.commands"
            embed = discord.Embed(
                title=f"👋 Thanks for adding {BRAND_NAME}!",
                description=(
                    f"{BRAND_NAME} is now active in **{guild.name}**! ⚡\n\n"
                    "**Quick Setup:**\n"
                    "• Configure bot management role: `/set-botrole` (Server Owner only)\n"
                    "• Set up server audit logs: `/setupbot`\n"
                    "• All commands list: `/help` or `n!help`\n\n"
                    "💡 **Slash commands (`/`) not showing up?**\n"
                    f"1. Make sure {BRAND_NAME} was invited with both `bot` and `applications.commands` scopes. If not, [click here to re-authorize]({reauth_url}).\n"
                    "2. Press `Ctrl + R` (desktop) or restart Discord (mobile) to refresh your command cache.\n"
                    "3. Ensure the **Use Application Commands** permission is enabled in server/channel role settings."
                ),
                color=0x5865F2,
            )
            embed.set_footer(text=f"{BRAND_NAME} — All-Purpose Discord Bot")
            try:
                await target_ch.send(embed=embed)
            except Exception:
                pass

    # ── Member Join ───────────────────────────────────────────────────────────
    @bot.event
    async def on_member_join(member: discord.Member):
        cfg = await get_config(member.guild.id)
        guild = member.guild
        extras = await get_welcome_extras(guild.id)

        ch_id = cfg.get("welcome_ch")
        if ch_id:
            ch = guild.get_channel(ch_id)
            if not ch:
                try:
                    ch = await guild.fetch_channel(ch_id)
                except Exception:
                    ch = None

            if ch and hasattr(ch, "send"):
                raw_template = cfg.get("welcome_msg") or "Welcome {mention} to **{guild}**! 🎉"
                msg = safe_format(
                    raw_template,
                    mention=member.mention,
                    name=str(member),
                    guild=guild.name,
                    member_count=guild.member_count,
                )

                welcome_fmt = extras.get("welcome_format", "embed")
                welcome_img = extras.get("welcome_image_url")

                if welcome_fmt == "text":
                    try:
                        content_str = msg
                        if welcome_img:
                            content_str += f"\n{welcome_img}"
                        await ch.send(content=content_str)
                    except Exception:
                        pass
                else:
                    hex_color = extras.get("welcome_color", "#5865F2")
                    try:
                        embed_color = int(hex_color.lstrip("#"), 16)
                    except Exception:
                        embed_color = 0x5865F2

                    human_count = sum(1 for m in guild.members if not m.bot)
                    embed = discord.Embed(
                        description=msg,
                        color=embed_color,
                        timestamp=discord.utils.utcnow(),
                    )
                    embed.set_author(
                        name=f"Welcome to {guild.name}!",
                        icon_url=guild.icon.url if guild.icon else None,
                    )
                    embed.set_thumbnail(url=member.display_avatar.url)
                    embed.add_field(
                        name="👤 Account Created",
                        value=f"<t:{int(member.created_at.timestamp())}:R>",
                        inline=True,
                    )
                    embed.add_field(
                        name="👥 Member Number",
                        value=f"`#{human_count}`",
                        inline=True,
                    )
                    if welcome_img:
                        embed.set_image(url=welcome_img)
                    embed.set_footer(text=guild.name)

                    try:
                        await ch.send(content=member.mention, embed=embed)
                    except Exception:
                        pass

        # Handle onboarding welcome extras (Direct Message & Join Role)
        try:
            if extras.get("dm_enabled") and extras.get("dm_message"):
                dm_raw = extras["dm_message"]
                dm_text = safe_format(
                    dm_raw,
                    mention=member.mention,
                    name=str(member),
                    guild=guild.name,
                    member_count=guild.member_count,
                )
                try:
                    await member.send(dm_text)
                except Exception:
                    pass

            role_id = extras.get("role_id")
            if role_id:
                w_role = guild.get_role(role_id)
                if w_role and guild.me.guild_permissions.manage_roles and w_role < guild.me.top_role:
                    try:
                        await member.add_roles(w_role, reason="Nexus Onboarding Welcome Role")
                    except Exception:
                        pass
        except Exception as e:
            log.warning(f"Error handling welcome extras on member join: {e}")

    # ── Member Leave ──────────────────────────────────────────────────────────
    @bot.event
    async def on_member_remove(member: discord.Member):
        cfg = await get_config(member.guild.id)
        guild = member.guild
        extras = await get_welcome_extras(guild.id)

        ch_id = cfg.get("leave_ch")
        if ch_id:
            ch = guild.get_channel(ch_id)
            if not ch:
                try:
                    ch = await guild.fetch_channel(ch_id)
                except Exception:
                    ch = None

            if ch and hasattr(ch, "send"):
                raw_template = cfg.get("leave_msg") or "**{name}** has left the server. Goodbye! 👋"
                msg = safe_format(
                    raw_template,
                    mention=member.mention,
                    name=str(member),
                    guild=guild.name,
                    member_count=guild.member_count,
                )

                leave_fmt = extras.get("leave_format", "embed")
                leave_img = extras.get("leave_image_url")

                if leave_fmt == "text":
                    try:
                        content_str = msg
                        if leave_img:
                            content_str += f"\n{leave_img}"
                        await ch.send(content=content_str)
                    except Exception:
                        pass
                else:
                    roles_str = ", ".join(
                        r.mention for r in reversed(member.roles) if r.name != "@everyone"
                    ) or "*None*"

                    embed = discord.Embed(
                        description=msg,
                        color=0xED4245,
                        timestamp=discord.utils.utcnow(),
                    )
                    embed.set_author(
                        name=f"Goodbye from {guild.name}",
                        icon_url=guild.icon.url if guild.icon else None,
                    )
                    embed.set_thumbnail(url=member.display_avatar.url)
                    embed.add_field(
                        name="📅 Joined Server",
                        value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "*Unknown*",
                        inline=True,
                    )
                    embed.add_field(
                        name="👥 Remaining Members",
                        value=f"`{guild.member_count}`",
                        inline=True,
                    )
                    embed.add_field(name="🏷️ Roles Held", value=roles_str[:1024], inline=False)
                    if leave_img:
                        embed.set_image(url=leave_img)
                    embed.set_footer(text=guild.name)

                    try:
                        await ch.send(embed=embed)
                    except Exception:
                        pass

    # ── Owner Commands: Non-Prefix Management ─────────────────────────────────
    async def _handle_addnp(ctx: commands.Context, target: str = None):
        if not is_bot_owner(ctx.author.id):
            return
        if not target:
            return await ctx.reply("❌ **Usage:** `addnp <@user / user_id>` (or `np add <@user / user_id>`)")

        clean_id = target.strip("<@!> ")
        user = None
        if clean_id.isdigit():
            uid = int(clean_id)
            user = bot.get_user(uid)
            if not user:
                try:
                    user = await bot.fetch_user(uid)
                except Exception:
                    user = None
        else:
            try:
                user = await commands.UserConverter().convert(ctx, target)
            except Exception:
                user = None

        if not user:
            return await ctx.reply("❌ Could not find that user. Please mention the user or provide a valid user ID.")
        if user.bot:
            return await ctx.reply("❌ Bots cannot be granted non-prefix access.")
        if is_bot_owner(user.id) or user.id in bot.non_prefix_users:
            return await ctx.reply(f"ℹ️ {user.mention} (`{user.id}`) already has non-prefix access.")

        await add_non_prefix_user(user.id, ctx.author.id)
        bot.non_prefix_users.add(user.id)

        embed = discord.Embed(
            title="✨ Non-Prefix Access Granted",
            description=f"Successfully granted non-prefix access to {user.mention} (`{user.id}`).\nThey can now run moderation commands without typing any prefix.",
            color=0x57F287,
        )
        await ctx.reply(embed=embed)

    async def _handle_removenp(ctx: commands.Context, target: str = None):
        if not is_bot_owner(ctx.author.id):
            return
        if not target:
            return await ctx.reply("❌ **Usage:** `removenp <@user / user_id>` (or `np remove <@user / user_id>`)")

        clean_id = target.strip("<@!> ")
        uid = None
        if clean_id.isdigit():
            uid = int(clean_id)
        else:
            try:
                u = await commands.UserConverter().convert(ctx, target)
                uid = u.id
            except Exception:
                pass

        if not uid:
            return await ctx.reply("❌ Could not find that user. Please mention the user or provide a valid user ID.")
        if uid not in bot.non_prefix_users:
            return await ctx.reply(f"❌ User `<@{uid}>` (`{uid}`) does not have non-prefix access.")

        await remove_non_prefix_user(uid)
        bot.non_prefix_users.discard(uid)

        embed = discord.Embed(
            title="🗑️ Non-Prefix Access Revoked",
            description=f"Successfully revoked non-prefix access from <@{uid}> (`{uid}`).",
            color=0xED4245,
        )
        await ctx.reply(embed=embed)

    async def _handle_listnp(ctx: commands.Context):
        if not is_bot_owner(ctx.author.id):
            return
        if not bot.non_prefix_users:
            embed = discord.Embed(
                title="⚡ Non-Prefix Users",
                description="*No non-prefix users have been registered.*",
                color=0x5865F2,
            )
            return await ctx.reply(embed=embed)

        user_lines = [f"• <@{uid}> (`{uid}`)" for uid in sorted(bot.non_prefix_users)]
        embed = discord.Embed(
            title="⚡ Non-Prefix Users",
            description="**Authorized Users:**\n" + "\n".join(user_lines),
            color=0x5865F2,
        )
        embed.set_footer(text=f"Total: {len(bot.non_prefix_users)} user(s)")
        await ctx.reply(embed=embed)

    @bot.command(name="addnp", aliases=["npadd"])
    async def cmd_addnp(ctx: commands.Context, target: str = None):
        await _handle_addnp(ctx, target)

    @bot.command(name="removenp", aliases=["npremove"])
    async def cmd_removenp(ctx: commands.Context, target: str = None):
        await _handle_removenp(ctx, target)

    @bot.command(name="nplist", aliases=["checknp"])
    async def cmd_nplist(ctx: commands.Context, *args):
        await _handle_listnp(ctx)

    @bot.group(name="np", invoke_without_command=True)
    async def cmd_np_group(ctx: commands.Context):
        await _handle_listnp(ctx)

    @cmd_np_group.command(name="add")
    async def cmd_np_add(ctx: commands.Context, target: str = None):
        await _handle_addnp(ctx, target)

    @cmd_np_group.command(name="remove")
    async def cmd_np_remove(ctx: commands.Context, target: str = None):
        await _handle_removenp(ctx, target)

    @cmd_np_group.command(name="list")
    async def cmd_np_list(ctx: commands.Context, *args):
        await _handle_listnp(ctx)

    # ── Owner Command: Sync ───────────────────────────────────────────────────
    @bot.command(name="sync")
    async def cmd_sync(ctx: commands.Context, mode: str = None):
        if not is_bot_owner(ctx.author.id):
            return
        if getattr(bot, "_is_syncing", False):
            return await ctx.reply("⏳ A slash command sync is currently running in the background. Please wait a moment.")

        bot._is_syncing = True
        mode_lower = (mode or "").lower()
        msg = await ctx.reply("🔄 Synchronizing slash commands with Discord...")

        try:
            if mode_lower == "guild" and ctx.guild:
                await asyncio.wait_for(ctx.bot.sync_commands(guild_ids=[ctx.guild.id], force=True), timeout=25.0)
                for cmd in ctx.bot.pending_application_commands:
                    cmd.guild_ids = None
                count = len(ctx.bot.application_commands) or len(ctx.bot.pending_application_commands)
                await msg.edit(
                    content=(
                        f"✅ Instantly synced **{count}** slash commands to **{ctx.guild.name}**!\n"
                        "💡 *Tip: If Discord still doesn't show them, press `Ctrl + R` in your Discord app to refresh.*"
                    )
                )
            elif mode_lower == "force":
                for cmd in ctx.bot.pending_application_commands:
                    cmd.guild_ids = None
                await asyncio.wait_for(ctx.bot.sync_commands(force=True, delete_existing=True), timeout=25.0)
                count = len(ctx.bot.application_commands) or len(ctx.bot.pending_application_commands)
                await msg.edit(content=f"✅ Force-synced **{count}** global slash commands!")
            else:
                for cmd in ctx.bot.pending_application_commands:
                    cmd.guild_ids = None
                await asyncio.wait_for(ctx.bot.sync_commands(), timeout=25.0)
                count = len(ctx.bot.application_commands) or len(ctx.bot.pending_application_commands)
                await msg.edit(content=f"✅ Successfully synchronized **{count}** global slash commands!")
        except asyncio.TimeoutError:
            count = len(ctx.bot.application_commands) or len(ctx.bot.pending_application_commands)
            await msg.edit(
                content=(
                    "⏳ **Discord Rate Limit Notice:** Discord API is temporarily rate-limiting command updates.\n"
                    f"⚡ Nexus's internal resilient dispatcher is handling all **{count}** slash commands!"
                )
            )
        except discord.HTTPException as e:
            if e.status == 429:
                await msg.edit(content="⏳ Discord rate limit cooling down. Resilient dispatcher is active!")
            else:
                await msg.edit(content=f"❌ Failed to sync commands: `{e}`")
        except Exception as e:
            await msg.edit(content=f"❌ Failed to sync commands: `{e}`")
        finally:
            bot._is_syncing = False

    # ── Invite Command ────────────────────────────────────────────────────────
    @bot.command(name="invite")
    async def cmd_invite(ctx: commands.Context):
        client_id = bot.user.id if bot.user else "1560655249276936192"
        url = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions=8&scope=bot%20applications.commands"
        embed = discord.Embed(
            title=f"🤖 Invite {BRAND_NAME} to Your Server",
            description=(
                f"[**Click here to invite {BRAND_NAME}**]({url})\n\n"
                "✨ **Note:** Includes both `bot` and `applications.commands` scopes for slash commands."
            ),
            color=0x5865F2,
        )
        await ctx.reply(embed=embed)
