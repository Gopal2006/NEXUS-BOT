r"""
╔══════════════════════════════════════════════════════════╗
║           NEXUS — All-Purpose Discord Bot               ║
║   Features: Announcements · DM · Giveaways · Moderation ║
║            Polls · Tickets · Welcome/Leave              ║
╚══════════════════════════════════════════════════════════╝
"""

import os
import sys
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
import aiosqlite
import logging
from pathlib import Path

# ── Windows Console Freeze Fix ────────────────────────────────────────────────
def disable_windows_quickedit():
    """Prevents Windows Console from freezing the asyncio loop when clicked or highlighted."""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.CreateFileW.restype = ctypes.c_void_p
            kernel32.GetStdHandle.restype = ctypes.c_void_p

            # Use CONIN$ directly to access the console input buffer (handles 64-bit properly)
            h = kernel32.CreateFileW("CONIN$", 0xC0000000, 3, None, 3, 0, None)
            if not h or h == ctypes.c_void_p(-1).value:
                h = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE

            if h and h != ctypes.c_void_p(-1).value:
                mode = ctypes.c_uint32()
                if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
                    # Clear ENABLE_QUICK_EDIT_MODE (0x0040), set ENABLE_EXTENDED_FLAGS (0x0080)
                    new_mode = (mode.value & ~0x0040) | 0x0080
                    kernel32.SetConsoleMode(h, new_mode)
        except Exception:
            pass

disable_windows_quickedit()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("Nexus")

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "")
if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
    log.critical("BOT_TOKEN not set — copy .env.example to .env and add your token!")
    raise SystemExit(1)


# ── Global constants ──────────────────────────────────────────────────────────
GLOBAL_OWNER_ID = 1201050377911554061   # Bot developer — bypasses all checks
SUPPORT_SERVER  = "https://discord.gg/PLACEHOLDER"  # Fill in your invite link

DB_PATH = Path("nexus.db")

# ── Intents ───────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members         = True
intents.message_content = True
intents.guilds          = True
intents.presences       = True   # needed for online-count in serverstats

# ── Non-Prefix System ─────────────────────────────────────────────────────────
NON_PREFIX_USERS: set[int] = set()

def get_prefix(client, message: discord.Message):
    prefixes = ["n!", "N!"]
    author = getattr(message, "author", None)
    if author and not author.bot:
        if author.id == GLOBAL_OWNER_ID or author.id in getattr(client, "non_prefix_users", set()):
            return ["n!", "N!", ""]
    return prefixes

# ── Bot ───────────────────────────────────────────────────────────────────────
bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None,   # custom help command in cogs/help.py
    description="Nexus — All-Purpose Discord Bot",
)
bot.non_prefix_users = NON_PREFIX_USERS

# ── Database setup ────────────────────────────────────────────────────────────
async def load_non_prefix_users():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT user_id FROM non_prefix_users") as cur:
                rows = await cur.fetchall()
                bot.non_prefix_users.clear()
                bot.non_prefix_users.update(row[0] for row in rows)
        log.info(f"Loaded {len(bot.non_prefix_users)} non-prefix user(s) ✓")
    except Exception as e:
        log.error(f"Failed to load non-prefix users: {e}")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id        INTEGER PRIMARY KEY,
                bot_role_id     INTEGER DEFAULT NULL,
                ticket_role_id  INTEGER DEFAULT NULL,
                welcome_ch      INTEGER DEFAULT NULL,
                leave_ch        INTEGER DEFAULT NULL,
                member_log_ch   INTEGER DEFAULT NULL,
                welcome_msg     TEXT    DEFAULT 'Welcome {mention} to **{guild}**! 🎉',
                leave_msg       TEXT    DEFAULT '**{name}** has left the server. Goodbye! 👋',
                log_ch          INTEGER DEFAULT NULL,
                mod_log_ch      INTEGER DEFAULT NULL,
                server_log_ch   INTEGER DEFAULT NULL,
                activity_log_ch INTEGER DEFAULT NULL,
                cmd_log_ch      INTEGER DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS non_prefix_users (
                user_id   INTEGER PRIMARY KEY,
                added_by  INTEGER NOT NULL,
                added_at  REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS giveaways (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id         INTEGER NOT NULL,
                channel_id       INTEGER NOT NULL,
                message_id       INTEGER NOT NULL,
                host_id          INTEGER NOT NULL,
                prize            TEXT    NOT NULL,
                winners          INTEGER NOT NULL DEFAULT 1,
                ends_at          REAL    NOT NULL,
                ended            INTEGER NOT NULL DEFAULT 0,
                required_role_id INTEGER DEFAULT NULL,
                required_role_ids TEXT DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS giveaway_ineligible_dms (
                giveaway_id INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                notified_at REAL NOT NULL,
                PRIMARY KEY (giveaway_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS warns (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id  INTEGER NOT NULL,
                user_id   INTEGER NOT NULL,
                mod_id    INTEGER NOT NULL,
                reason    TEXT,
                timestamp REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tickets (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id   INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                status     TEXT NOT NULL DEFAULT 'open'
            );

            CREATE TABLE IF NOT EXISTS mutes (
                guild_id INTEGER NOT NULL,
                user_id  INTEGER NOT NULL,
                ends_at  REAL,
                PRIMARY KEY (guild_id, user_id)
            );
        """)

        # Auto-migrate columns if table already existed
        async with db.execute("PRAGMA table_info(guild_config)") as cur:
            columns = [row[1] for row in await cur.fetchall()]
        new_cols = [
            ("ticket_role_id",  "INTEGER DEFAULT NULL"),
            ("mod_log_ch",      "INTEGER DEFAULT NULL"),
            ("server_log_ch",   "INTEGER DEFAULT NULL"),
            ("activity_log_ch", "INTEGER DEFAULT NULL"),
            ("member_log_ch",   "INTEGER DEFAULT NULL"),
            ("cmd_log_ch",      "INTEGER DEFAULT NULL"),
        ]
        for col_name, col_type in new_cols:
            if col_name not in columns:
                try:
                    await db.execute(f"ALTER TABLE guild_config ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass

        # Auto-migrate giveaways table
        async with db.execute("PRAGMA table_info(giveaways)") as cur:
            gw_cols = [row[1] for row in await cur.fetchall()]
        if "required_role_id" not in gw_cols:
            try:
                await db.execute("ALTER TABLE giveaways ADD COLUMN required_role_id INTEGER DEFAULT NULL")
            except Exception:
                pass
        if "required_role_ids" not in gw_cols:
            try:
                await db.execute("ALTER TABLE giveaways ADD COLUMN required_role_ids TEXT DEFAULT NULL")
            except Exception:
                pass

        await db.commit()
    log.info("Database initialised ✓")

# ── Helper: fetch/create guild config ─────────────────────────────────────────
async def get_config(guild_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO guild_config (guild_id) VALUES (?)", (guild_id,)
            )
            await db.commit()
            async with db.execute(
                "SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)
            ) as cur:
                row = await cur.fetchone()
        return dict(row)

async def set_config(guild_id: int, **kwargs):
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [guild_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE guild_config SET {sets} WHERE guild_id = ?", vals
        )
        await db.commit()

# ── Permission helpers ────────────────────────────────────────────────────────
async def has_bot_permission(ctx) -> bool:
    """
    True if user is:
      - the global bot owner, OR
      - a registered non-prefix user, OR
      - the server owner, OR
      - has the configured bot-role.

    Administrators WITHOUT the bot-role are NOT granted access.
    """
    author = getattr(ctx, "author", None)
    if not author:
        return False
    if author.id == GLOBAL_OWNER_ID:
        return True
    if author.id in getattr(bot, "non_prefix_users", set()):
        return True
    if ctx.guild is None:
        return False
    if author.id == ctx.guild.owner_id:
        return True
    cfg = await get_config(ctx.guild.id)
    role_id = cfg.get("bot_role_id")
    if role_id:
        member = ctx.guild.get_member(author.id) or author
        if hasattr(member, "roles"):
            return any(r.id == role_id for r in member.roles)
    return False


async def send_no_permission(ctx):
    """Ephemeral 'ask server owner for bot role' message."""
    if ctx.guild is None:
        embed = discord.Embed(
            title="🔒 Access Denied",
            description="Commands can only be used inside a server.",
            color=0xED4245,
        )
        if hasattr(ctx, "respond"):
            if getattr(ctx, "response", None) and ctx.response.is_done():
                return await ctx.followup.send(embed=embed, ephemeral=True)
            return await ctx.respond(embed=embed, ephemeral=True)
        return await ctx.reply(embed=embed)

    cfg = await get_config(ctx.guild.id)
    role_id  = cfg.get("bot_role_id")
    bot_role = ctx.guild.get_role(role_id) if role_id else None

    if bot_role:
        tip = (
            f"You need the **{bot_role.name}** role to use bot commands.\n"
            "Please ask the **server owner** to grant you this role."
        )
    else:
        tip = (
            "You don't have permission to use bot commands.\n"
            "Please ask the **server owner** to assign a bot-role using `/set-botrole`."
        )

    embed = discord.Embed(
        title="🔒 Access Denied",
        description=tip,
        color=0xED4245,
    )
    if hasattr(ctx, "respond"):
        if getattr(ctx, "response", None) and ctx.response.is_done():
            return await ctx.followup.send(embed=embed, ephemeral=True)
        return await ctx.respond(embed=embed, ephemeral=True)
    return await ctx.reply(embed=embed)


# ── Global Command Check ──────────────────────────────────────────────────────
@bot.check
async def globally_enforce_bot_role(ctx):
    """
    Global security lock:
    Enforces that ONLY the Server Owner, Bot Owner (1201050377911554061),
    or members with the configured Bot Role can use ANY command across the bot.
    """
    allowed = await has_bot_permission(ctx)
    if not allowed:
        raise commands.CheckFailure("User lacks permission to use bot commands.")
    return True


# ── Global Error Handlers ─────────────────────────────────────────────────────
@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error: discord.DiscordException):
    if isinstance(error, (commands.CheckFailure, discord.CheckFailure)):
        return await send_no_permission(ctx)
    log.error(f"Error in slash command '{ctx.command}': {error}")
    try:
        if not ctx.response.is_done():
            await ctx.respond(
                embed=discord.Embed(description=f"❌ An error occurred: `{error}`", color=0xED4245),
                ephemeral=True,
            )
    except Exception:
        pass


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return

    # If any member other than the bot owner tries to invoke an owner command, completely ignore
    cmd_name = (ctx.command.qualified_name if ctx.command else (ctx.invoked_with or "")).lower()
    owner_cmds = {"addnp", "removenp", "nplist", "np", "np add", "np remove", "np list", "npadd", "npremove", "checknp", "sync"}
    if cmd_name in owner_cmds:
        if getattr(ctx.author, "id", None) != GLOBAL_OWNER_ID:
            return

    if isinstance(error, commands.CheckFailure):
        return await send_no_permission(ctx)
    if isinstance(error, commands.UserNotFound):
        return await ctx.reply("❌ User not found. Please mention a user or provide a valid user ID.")
    if isinstance(error, commands.BadArgument):
        return await ctx.reply(f"❌ Invalid argument: {error}")
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.reply(f"❌ Missing argument: `{error.param.name}`")
    log.error(f"Error in prefix command '{ctx.command}': {error}")


# ── Command Audit Logging (Prefix & Non-Prefix) ──────────────────────────────
@bot.event
async def on_command_completion(ctx: commands.Context):
    """
    Audit log whenever a command is executed with prefix (e.g. n!kick)
    or without prefix (e.g. kick).
    """
    if not ctx.guild or not ctx.command:
        return

    # Check if executed with prefix or no prefix
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
        embed.add_field(name="👤 Executed By", value=f"{ctx.author.mention} (`{ctx.author.id}`)", inline=True)

        content = ctx.message.content
        if content:
            preview = content if len(content) <= 500 else content[:497] + "…"
            embed.add_field(name="💬 Message Content", value=f"```{preview}```", inline=False)

        embed.set_footer(text=f"Nexus  •  Command Audit  •  Msg ID: {ctx.message.id}")
        await ch.send(embed=embed)
    except Exception as e:
        log.error(f"Failed to log command execution: {e}")


# ── Bot Events ────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    disable_windows_quickedit()
    await init_db()
    await load_non_prefix_users()
    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="over the server",
        ),
    )
    log.info(f"Logged in as {bot.user} ({bot.user.id})")
    log.info(f"Loaded {len(bot.application_commands)} slash command definitions")

    # Instantly sync slash commands to all connected guilds (0-delay visibility)
    try:
        guild_ids = [g.id for g in bot.guilds]
        if guild_ids:
            await bot.sync_commands(force=True, guild_ids=guild_ids, delete_existing=True)
            log.info(f"Instantly synced slash commands across {len(guild_ids)} guild(s) ✓")
    except Exception as e:
        log.warning(f"Could not instant-sync commands to guilds: {e}")


# ── Non-Prefix Management Logic ──────────────────────────────────────────────
async def add_non_prefix_user(ctx: commands.Context, target: str = None):
    """Grant non-prefix command access to a user (Bot Owner only)."""
    if ctx.author.id != GLOBAL_OWNER_ID:
        return
    if not target:
        return await ctx.reply("❌ **Usage:** `addnp <@user / user_id>` (or `np add <@user / user_id>`)")

    user = None
    clean_id = target.strip("<@!> ")
    if clean_id.isdigit():
        uid = int(clean_id)
        user = ctx.bot.get_user(uid)
        if not user:
            try:
                user = await ctx.bot.fetch_user(uid)
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
    if user.id == GLOBAL_OWNER_ID or user.id in bot.non_prefix_users:
        return await ctx.reply(f"ℹ️ {user.mention} (`{user.id}`) already has non-prefix access.")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO non_prefix_users (user_id, added_by, added_at) VALUES (?, ?, ?)",
            (user.id, ctx.author.id, discord.utils.utcnow().timestamp()),
        )
        await db.commit()
    bot.non_prefix_users.add(user.id)

    embed = discord.Embed(
        title="✨ Non-Prefix Access Granted",
        description=f"Successfully granted non-prefix access to {user.mention} (`{user.id}`).\nThey can now run moderation commands without typing any prefix.",
        color=0x57F287,
    )
    await ctx.reply(embed=embed)


async def remove_non_prefix_user(ctx: commands.Context, target: str = None):
    """Revoke non-prefix command access from a user (Bot Owner only)."""
    if ctx.author.id != GLOBAL_OWNER_ID:
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

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM non_prefix_users WHERE user_id = ?", (uid,))
        await db.commit()
    bot.non_prefix_users.discard(uid)

    embed = discord.Embed(
        title="🗑️ Non-Prefix Access Revoked",
        description=f"Successfully revoked non-prefix access from <@{uid}> (`{uid}`).",
        color=0xED4245,
    )
    await ctx.reply(embed=embed)


async def list_non_prefix_users(ctx: commands.Context):
    """View all users with non-prefix command access (Bot Owner only)."""
    if ctx.author.id != GLOBAL_OWNER_ID:
        return

    if not bot.non_prefix_users:
        embed = discord.Embed(
            title="⚡ Non-Prefix Users",
            description="*No non-prefix users have been registered.*",
            color=0x5865F2,
        )
        return await ctx.reply(embed=embed)

    user_lines = []
    for uid in sorted(bot.non_prefix_users):
        user_lines.append(f"• <@{uid}> (`{uid}`)")

    desc = "**Authorized Users:**\n" + "\n".join(user_lines)
    embed = discord.Embed(
        title="⚡ Non-Prefix Users",
        description=desc,
        color=0x5865F2,
    )
    embed.set_footer(text=f"Total: {len(bot.non_prefix_users)} user(s)")
    await ctx.reply(embed=embed)


# ── Non-Prefix Management Commands (Prefix & Non-Prefix for Bot Owner) ───────
@bot.command(name="addnp", aliases=["npadd"])
async def cmd_addnp(ctx: commands.Context, target: str = None):
    """Grant non-prefix access: addnp <user> or n!addnp <user>"""
    await add_non_prefix_user(ctx, target=target)


@bot.command(name="removenp", aliases=["npremove"])
async def cmd_removenp(ctx: commands.Context, target: str = None):
    """Revoke non-prefix access: removenp <user> or n!removenp <user>"""
    await remove_non_prefix_user(ctx, target=target)


@bot.command(name="nplist", aliases=["checknp"])
async def cmd_nplist(ctx: commands.Context, *args):
    """List non-prefix users: nplist or n!nplist"""
    await list_non_prefix_users(ctx)


@bot.group(name="np", invoke_without_command=True)
async def cmd_np_group(ctx: commands.Context):
    """'np' or 'np list' / 'n!np list' to check non-prefix users."""
    await list_non_prefix_users(ctx)


@cmd_np_group.command(name="add")
async def cmd_np_group_add(ctx: commands.Context, target: str = None):
    """np add <user> or n!np add <user>"""
    await add_non_prefix_user(ctx, target=target)


@cmd_np_group.command(name="remove")
async def cmd_np_group_remove(ctx: commands.Context, target: str = None):
    """np remove <user> or n!np remove <user>"""
    await remove_non_prefix_user(ctx, target=target)


@cmd_np_group.command(name="list")
async def cmd_np_group_list(ctx: commands.Context, *args):
    """np list or n!np list"""
    await list_non_prefix_users(ctx)


# ── Command Sync (Bot Owner Only) ─────────────────────────────────────────────
@bot.command(name="sync")
async def cmd_sync(ctx: commands.Context):
    """Force re-sync all slash commands with Discord API (Bot Owner only)."""
    if ctx.author.id != GLOBAL_OWNER_ID:
        return
    msg = await ctx.reply("🔄 Synchronizing all slash commands with Discord...")
    try:
        guild_ids = [g.id for g in ctx.bot.guilds]
        if guild_ids:
            await ctx.bot.sync_commands(force=True, guild_ids=guild_ids, delete_existing=True)
        await ctx.bot.sync_commands(force=True, delete_existing=True)
        await msg.edit(content=f"✅ Successfully synced **{len(ctx.bot.application_commands)}** slash commands instantly!\n💡 *Tip: If Discord still shows old commands, press `Ctrl + R` in your Discord app to refresh the client cache.*")
    except Exception as e:
        await msg.edit(content=f"❌ Failed to sync commands: `{e}`")


# ── Member Join ───────────────────────────────────────────────────────────────
@bot.event
async def on_member_join(member: discord.Member):
    cfg   = await get_config(member.guild.id)
    guild = member.guild

    # Welcome message channel
    ch_id = cfg.get("welcome_ch")
    if ch_id:
        ch = guild.get_channel(ch_id)
        if ch:
            msg = cfg["welcome_msg"].format(
                mention=member.mention,
                name=str(member),
                guild=guild.name,
            )
            human_count = sum(1 for m in guild.members if not m.bot)

            embed = discord.Embed(
                description=msg,
                color=0x57F287,
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
            embed.set_footer(text=guild.name)
            try:
                await ch.send(content=member.mention, embed=embed)
            except Exception:
                pass


# ── Member Leave ──────────────────────────────────────────────────────────────
@bot.event
async def on_member_remove(member: discord.Member):
    cfg   = await get_config(member.guild.id)
    guild = member.guild

    # Leave message channel
    ch_id = cfg.get("leave_ch")
    if ch_id:
        ch = guild.get_channel(ch_id)
        if ch:
            msg = cfg["leave_msg"].format(
                mention=member.mention,
                name=str(member),
                guild=guild.name,
            )
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
            embed.add_field(name="📅 Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "*Unknown*", inline=True)
            embed.add_field(name="👥 Remaining Members", value=f"`{guild.member_count}`", inline=True)
            embed.add_field(name="🏷️ Roles Held", value=roles_str[:1024], inline=False)
            embed.set_footer(text=guild.name)
            try:
                await ch.send(embed=embed)
            except Exception:
                pass

# ── Load Cogs ─────────────────────────────────────────────────────────────────
async def main():
    cog_files = [
        "cogs.admin",
        "cogs.announcements",
        "cogs.dm",
        "cogs.giveaway",
        "cogs.moderation",
        "cogs.polls",
        "cogs.tickets",
    ]
    for cog in cog_files:
        try:
            bot.load_extension(cog)
            log.info(f"  ✓ Loaded cog: {cog}")
        except Exception as e:
            log.error(f"  ✗ Failed to load {cog}: {e}")

    try:
        await bot.start(TOKEN)
    except discord.errors.PrivilegedIntentsRequired:
        log.critical(
            "\n" + "=" * 65 + "\n"
            "❌ PRIVILEGED INTENTS REQUIRED!\n"
            "Discord rejected the connection because Privileged Gateway Intents\n"
            "are not toggled ON in your Discord Developer Portal.\n\n"
            "Quick fix (takes ~15 seconds):\n"
            "1. Open https://discord.com/developers/applications/\n"
            "2. Click your Bot Application\n"
            "3. Click 'Bot' in the left sidebar\n"
            "4. Scroll down to 'Privileged Gateway Intents'\n"
            "5. Turn ON all three:\n"
            "   • [✓] Presence Intent\n"
            "   • [✓] Server Members Intent\n"
            "   • [✓] Message Content Intent\n"
            "6. Click 'Save Changes' at the bottom\n"
            "7. Run 'python bot.py' again!\n"
            + "=" * 65
        )
    except discord.errors.LoginFailure:
        log.critical("❌ Invalid BOT_TOKEN! Please check your .env file.")
    except Exception as e:
        log.error(f"Unexpected error: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
