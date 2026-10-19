"""
Giveaway Cog
Commands:
  /giveaway start  — create a giveaway in any channel
  /giveaway end    — force-end a giveaway
  /giveaway reroll — re-pick a winner
  /giveaway list   — list active giveaways
"""

import discord
from discord.ext import commands, tasks
from discord import option
import aiosqlite
import asyncio
import random
import time
import re
from pathlib import Path

DB_PATH = Path("nexus.db")
GLOBAL_OWNER_ID = 1201050377911554061


def parse_roles_from_string(guild: discord.Guild, text: str) -> list[discord.Role]:
    """Parse Discord roles from text containing role mentions, IDs, or role names in a single string."""
    if not text or not guild:
        return []

    roles = []
    seen_ids = set()

    def try_add_role(target):
        if not target:
            return False
        clean = str(target).strip().lstrip("@").strip()
        if not clean:
            return False
        if clean.isdigit():
            r = guild.get_role(int(clean))
            if r and r.id not in seen_ids:
                roles.append(r)
                seen_ids.add(r.id)
                return True
        r = discord.utils.find(lambda x: x.name.lower() == clean.lower(), guild.roles)
        if r and r.id not in seen_ids:
            roles.append(r)
            seen_ids.add(r.id)
            return True
        return False

    # 1. Extract role mentions <@&123456789>
    mention_pattern = re.compile(r"<@&(\d+)>")
    for match in mention_pattern.finditer(text):
        role_id = int(match.group(1))
        role = guild.get_role(role_id)
        if role and role.id not in seen_ids:
            roles.append(role)
            seen_ids.add(role.id)

    # Replace mentions with spaces so we don't re-match raw IDs from mentions
    clean_text = mention_pattern.sub(" ", text)

    # 2. Split remaining tokens by comma, newline, semicolon, or pipe
    delimiters = [",", "\n", ";", "|"]
    tokens = [clean_text]
    for d in delimiters:
        new_tokens = []
        for t in tokens:
            new_tokens.extend(t.split(d))
        tokens = new_tokens

    for raw_token in tokens:
        token = raw_token.strip()
        if not token:
            continue

        # If token directly matches a role or ID
        if try_add_role(token):
            continue

        # If token has multiple '@' symbols (e.g. "@VIP @Booster")
        if "@" in token:
            at_parts = [p.strip() for p in token.split("@") if p.strip()]
            for part in at_parts:
                if not try_add_role(part):
                    # Check individual words in part
                    for w in part.split():
                        try_add_role(w)
            continue

        # Otherwise split by whitespace and check individual tokens
        for word in token.split():
            try_add_role(word)

    return roles


def parse_required_role_ids(row: dict) -> list[int]:
    """Extract list of required role IDs from row, supporting both required_role_ids and required_role_id."""
    raw = row.get("required_role_ids")
    if raw:
        ids = [int(x.strip()) for x in str(raw).split(",") if x.strip().isdigit()]
        if ids:
            return ids
    single = row.get("required_role_id")
    if single:
        return [int(single)]
    return []


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
    """Server owner, global owner, or member with the bot-role.
    Administrators without the bot-role are NOT granted access."""
    if ctx.author.id == GLOBAL_OWNER_ID:
        return True
    if ctx.guild is None:
        return False
    if ctx.author.id == ctx.guild.owner_id:
        return True
    cfg = await get_config(ctx.guild.id)
    role_id = cfg.get("bot_role_id")
    if role_id and any(r.id == role_id for r in ctx.author.roles):
        return True
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



def parse_duration(s: str) -> int:
    """Convert e.g. '1d', '2h30m', '45s' to seconds."""
    s = s.strip().lower()
    total = 0
    buf = ""
    for c in s:
        if c.isdigit():
            buf += c
        elif c in "dhms" and buf:
            n = int(buf)
            total += n * {"d": 86400, "h": 3600, "m": 60, "s": 1}[c]
            buf = ""
    return total


def fmt_time(secs: float) -> str:
    secs = int(max(0, secs))
    d, r = divmod(secs, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if s or not parts: parts.append(f"{s}s")
    return " ".join(parts)


GIVEAWAY_EMOJI = "🎉"


def build_giveaway_embed(
    prize,
    winners,
    host_id,
    ends_at,
    ended=False,
    winner_ids=None,
    required_role_ids=None,
    required_role_id=None,
):
    if required_role_ids is None:
        required_role_ids = [required_role_id] if required_role_id else []
    elif isinstance(required_role_ids, int):
        required_role_ids = [required_role_ids]

    remaining = ends_at - time.time()
    color = 0x57F287 if not ended else 0x5865F2
    embed = discord.Embed(
        title=f"🎉 GIVEAWAY — {prize}",
        color=color,
    )
    embed.add_field(name="🏆 Winners", value=str(winners), inline=True)
    embed.add_field(name="👤 Hosted by", value=f"<@{host_id}>", inline=True)

    if required_role_ids:
        roles_val = ", ".join(f"<@&{rid}>" for rid in required_role_ids)
        if len(roles_val) > 1024:
            roles_val = roles_val[:1020] + "..."
        field_title = "🔒 Required Role" if len(required_role_ids) == 1 else "🔒 Required Roles"
        embed.add_field(name=field_title, value=roles_val, inline=True)
    else:
        embed.add_field(name="👥 Eligibility", value="Everyone", inline=True)

    if not ended:
        embed.add_field(name="⏰ Ends in", value=fmt_time(remaining), inline=True)
        if required_role_ids:
            if len(required_role_ids) == 1:
                role_note = f"\n🔒 **Eligible Role:** <@&{required_role_ids[0]}> only"
            else:
                roles_mentions = ", ".join(f"<@&{rid}>" for rid in required_role_ids)
                role_note = f"\n🔒 **Eligible Roles (Any):** {roles_mentions}"
        else:
            role_note = ""
        embed.description = f"React with {GIVEAWAY_EMOJI} to enter!{role_note}\n\n**Ends:** <t:{int(ends_at)}:R>"
    else:
        embed.add_field(name="Status", value="✅ Ended", inline=True)
        if winner_ids:
            mentions = " ".join(f"<@{w}>" for w in winner_ids)
            embed.description = f"🎊 **Winner(s):** {mentions}\n\n**Prize:** {prize}"
        else:
            embed.description = "😔 No valid entries — no winner picked."
    embed.set_footer(text="React with 🎉 to enter! | Nexus Giveaways")
    return embed


# ── Giveaway Modal ────────────────────────────────────────────────────────────
class GiveawayModal(discord.ui.Modal):
    """
    Interactive modal popup for launching giveaways.
    Collects Prize, Duration, Number of Winners, Description, and Required Roles.
    """
    def __init__(self, target_channel: discord.TextChannel, initial_roles: list[discord.Role] = None):
        super().__init__(title="🎉 Create a Giveaway")
        self.target_channel = target_channel
        self.initial_roles = initial_roles or []

        self.add_item(discord.ui.InputText(
            label="Giveaway Prize",
            placeholder="e.g. Discord Nitro (1 Month), $10 Gift Card, etc.",
            style=discord.InputTextStyle.short,
            max_length=256,
            required=True,
            custom_id="gw_prize",
        ))
        self.add_item(discord.ui.InputText(
            label="Duration",
            placeholder="e.g. 10m, 2h, 1d, 3d (min 10s)",
            style=discord.InputTextStyle.short,
            max_length=20,
            required=True,
            custom_id="gw_duration",
        ))
        self.add_item(discord.ui.InputText(
            label="Number of Winners",
            placeholder="1 (default) or enter e.g. 2, 3",
            style=discord.InputTextStyle.short,
            max_length=5,
            required=False,
            custom_id="gw_winners",
        ))
        self.add_item(discord.ui.InputText(
            label="Description / Details (Optional)",
            placeholder="e.g. Sponsored by staff, congratulations to our community!",
            style=discord.InputTextStyle.long,
            max_length=500,
            required=False,
            custom_id="gw_desc",
        ))
        initial_roles_val = ", ".join(r.name for r in self.initial_roles) if self.initial_roles else None
        self.add_item(discord.ui.InputText(
            label="Required Roles (Optional)",
            placeholder="e.g. @VIP, @Booster, Level 5 (leave blank for everyone)",
            value=initial_roles_val,
            style=discord.InputTextStyle.short,
            max_length=300,
            required=False,
            custom_id="gw_roles",
        ))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        prize     = self.children[0].value.strip()
        dur_str   = self.children[1].value.strip()
        win_str   = (self.children[2].value or "1").strip()
        desc      = (self.children[3].value or "").strip() or None
        roles_str = (self.children[4].value or "").strip()

        secs = parse_duration(dur_str)
        if secs < 10:
            return await interaction.followup.send(
                embed=discord.Embed(description="❌ Duration too short (minimum 10 seconds). Example: `30m`, `2h`, `1d`.", color=0xED4245),
                ephemeral=True,
            )

        try:
            winners = max(1, min(50, int(win_str)))
        except ValueError:
            winners = 1

        ends_at = time.time() + secs

        # Resolve required roles from input or slash command
        final_roles = []
        if roles_str:
            final_roles = parse_roles_from_string(interaction.guild, roles_str)
        elif self.initial_roles:
            final_roles = list(self.initial_roles)

        req_role_ids = [r.id for r in final_roles]
        primary_role_id = req_role_ids[0] if req_role_ids else None
        req_role_ids_str = ",".join(str(rid) for rid in req_role_ids) if req_role_ids else None

        embed = build_giveaway_embed(prize, winners, interaction.user.id, ends_at, required_role_ids=req_role_ids)
        if desc:
            embed.description = (embed.description or "") + f"\n\n📝 **Details:** {desc}"

        try:
            msg = await self.target_channel.send(embed=embed)
            await msg.add_reaction(GIVEAWAY_EMOJI)
        except discord.Forbidden:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Missing Permissions",
                    description=f"I don't have permission to post messages or add reactions in {self.target_channel.mention}.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )
        except Exception as e:
            return await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Error Launching Giveaway",
                    description=f"Could not start giveaway: `{e}`",
                    color=0xED4245,
                ),
                ephemeral=True,
            )

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO giveaways
                   (guild_id, channel_id, message_id, host_id, prize, winners, ends_at, required_role_id, required_role_ids)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (interaction.guild.id, self.target_channel.id, msg.id, interaction.user.id, prize, winners, ends_at, primary_role_id, req_role_ids_str),
            )
            await db.commit()

        await interaction.followup.send(
            embed=discord.Embed(
                title="🎉 Giveaway Started!",
                description=f"Giveaway for **{prize}** is live in {self.target_channel.mention}!\n\n🔗 [Jump to Giveaway]({msg.jump_url})",
                color=0x57F287,
            ),
            ephemeral=True,
        )

        role_label = ", ".join(r.mention for r in final_roles) if final_roles else "Everyone"
        log_emb = discord.Embed(
            title="🎉 Giveaway Launched",
            description=(
                f"**Prize:** {prize}\n"
                f"**Host:** {interaction.user.mention}\n"
                f"**Channel:** {self.target_channel.mention}\n"
                f"**Winners:** `{winners}`\n"
                f"**Required Roles:** {role_label}\n"
                f"**Ends:** <t:{int(ends_at)}:R>"
            ),
            color=0x57F287,
            timestamp=discord.utils.utcnow(),
        )
        log_emb.set_footer(text="Nexus Activity Audit")
        await log_activity(interaction.guild, log_emb)


class Giveaway(commands.Cog):
    """🎉 Giveaway management system."""

    def __init__(self, bot):
        self.bot = bot
        asyncio.create_task(self._ensure_db())
        self.giveaway_loop.start()

    async def _ensure_db(self):
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("""
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
                """)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS giveaway_ineligible_dms (
                        giveaway_id INTEGER NOT NULL,
                        user_id     INTEGER NOT NULL,
                        notified_at REAL NOT NULL,
                        PRIMARY KEY (giveaway_id, user_id)
                    );
                """)
                async with db.execute("PRAGMA table_info(giveaways)") as cur:
                    gw_cols = [r[1] for r in await cur.fetchall()]
                if "required_role_ids" not in gw_cols:
                    await db.execute("ALTER TABLE giveaways ADD COLUMN required_role_ids TEXT DEFAULT NULL")
                await db.commit()
        except Exception:
            pass

    def cog_unload(self):
        self.giveaway_loop.cancel()

    # ── Background task: auto-end giveaways ───────────────────────────────────
    @tasks.loop(seconds=30)
    async def giveaway_loop(self):
        now = time.time()
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM giveaways WHERE ended=0 AND ends_at <= ?", (now,)
            ) as cur:
                rows = await cur.fetchall()
        for row in rows:
            await self._end_giveaway(dict(row))

    @giveaway_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    async def _end_giveaway(self, row: dict):
        guild = self.bot.get_guild(row["guild_id"])
        if not guild:
            return
        channel = guild.get_channel(row["channel_id"])
        if not channel:
            return
        try:
            message = await channel.fetch_message(row["message_id"])
        except Exception:
            return

        reaction = discord.utils.get(message.reactions, emoji=GIVEAWAY_EMOJI)
        entries = []
        req_role_ids = parse_required_role_ids(row)
        if reaction:
            async for user in reaction.users():
                if not user.bot:
                    member = guild.get_member(user.id)
                    if not member:
                        try:
                            member = await guild.fetch_member(user.id)
                        except Exception:
                            member = None
                    if member:
                        if req_role_ids:
                            if any(r.id in req_role_ids for r in member.roles):
                                entries.append(user.id)
                        else:
                            entries.append(user.id)

        n_winners = min(row["winners"], len(entries))
        winner_ids = random.sample(entries, n_winners) if entries else []

        embed = build_giveaway_embed(
            row["prize"], row["winners"], row["host_id"], row["ends_at"],
            ended=True, winner_ids=winner_ids, required_role_ids=req_role_ids,
        )
        await message.edit(embed=embed)

        if winner_ids:
            mentions = " ".join(f"<@{w}>" for w in winner_ids)
            await channel.send(
                f"🎊 Congratulations {mentions}! You won **{row['prize']}**!\n"
                f"Hosted by <@{row['host_id']}>."
            )
        else:
            await channel.send(f"😔 No valid entries for **{row['prize']}**.")

        end_log = discord.Embed(
            title="🏁 Giveaway Concluded",
            description=f"**Prize:** {row['prize']}\n**Channel:** {channel.mention}\n**Winners:** {mentions if winner_ids else 'No valid entries'}",
            color=0x5865F2,
            timestamp=discord.utils.utcnow(),
        )
        end_log.set_footer(text="Nexus Activity Audit")
        await log_activity(channel.guild, end_log)

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE giveaways SET ended=1 WHERE id=?", (row["id"],))
            await db.commit()

    # ── Listener: Check Role on Reaction ──────────────────────────────────────
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id or str(payload.emoji) != GIVEAWAY_EMOJI:
            return

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM giveaways WHERE message_id=? AND ended=0",
                (payload.message_id,),
            ) as cur:
                row = await cur.fetchone()

        if not row:
            return

        row_dict = dict(row)
        req_role_ids = parse_required_role_ids(row_dict)
        if not req_role_ids:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = payload.member or guild.get_member(payload.user_id)
        if not member:
            try:
                member = await guild.fetch_member(payload.user_id)
            except Exception:
                return

        if member.bot:
            return

        # Check if member has at least one of the required roles
        if any(r.id in req_role_ids for r in member.roles):
            return

        # Member is NOT eligible!
        # 1. Immediately remove their reaction from the giveaway message
        channel = guild.get_channel(payload.channel_id)
        if channel:
            try:
                msg = await channel.fetch_message(payload.message_id)
                await msg.remove_reaction(payload.emoji, member)
            except Exception:
                pass

        # 2. Check if this member has already received a DM for THIS specific giveaway
        gw_id = row_dict["id"]
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT 1 FROM giveaway_ineligible_dms WHERE giveaway_id=? AND user_id=?",
                (gw_id, member.id),
            ) as cur:
                already_dm = await cur.fetchone() is not None

            if not already_dm:
                await db.execute(
                    "INSERT OR IGNORE INTO giveaway_ineligible_dms (giveaway_id, user_id, notified_at) VALUES (?, ?, ?)",
                    (gw_id, member.id, time.time()),
                )
                await db.commit()

        # If already DMed previously for this giveaway: auto-remove was completed, do not send another DM
        if already_dm:
            return

        # 3. First time trying this giveaway: send DM notification
        try:
            role_mentions = []
            for rid in req_role_ids:
                r = guild.get_role(rid)
                role_mentions.append(f"@{r.name}" if r else f"Role ID {rid}")
            role_str = ", ".join(role_mentions) if role_mentions else "Required Role"

            embed = discord.Embed(
                title="⚠️ Giveaway Entry Ineligible",
                description=(
                    f"You cannot enter the giveaway for **{row_dict['prize']}** in **{guild.name}** "
                    f"because you are not eligible.\n\n"
                    f"🔒 **Required Role(s):** {role_str}\n"
                    f"*(You must have at least one of these roles to enter)*"
                ),
                color=0xED4245,
                timestamp=discord.utils.utcnow(),
            )
            embed.set_footer(text=f"{guild.name} • Nexus Giveaways")
            await member.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

    # ── /giveaway start ───────────────────────────────────────────────────────
    giveaway_group = discord.SlashCommandGroup("giveaway", "Giveaway commands")

    @giveaway_group.command(name="start", description="Launch a giveaway via an interactive popup modal")
    @option("channel", discord.TextChannel, description="Channel to host the giveaway (defaults to current)", required=False, default=None)
    @option("role", str, description="Required role(s) to enter — add one or multiple roles (e.g. @VIP @Booster)", required=False, default=None)
    async def giveaway_start(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel = None,
        role: str = None,
    ):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)

        target_ch = channel or ctx.channel
        selected_roles = parse_roles_from_string(ctx.guild, role) if role else []
        modal = GiveawayModal(target_channel=target_ch, initial_roles=selected_roles)
        await ctx.send_modal(modal)

    # ── /giveaway end ─────────────────────────────────────────────────────────
    @giveaway_group.command(name="end", description="End a giveaway by message ID")
    @option("message_id", str, description="The message ID of the giveaway")
    async def giveaway_end(self, ctx: discord.ApplicationContext, message_id: str):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        try:
            mid = int(message_id)
        except ValueError:
            return await ctx.respond(
                embed=discord.Embed(description="❌ Invalid message ID.", color=0xED4245), ephemeral=True
            )
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM giveaways WHERE message_id=? AND guild_id=? AND ended=0",
                (mid, ctx.guild.id),
            ) as cur:
                row = await cur.fetchone()

        if not row:
            return await ctx.respond(
                embed=discord.Embed(description="❌ No active giveaway found with that message ID.", color=0xED4245),
                ephemeral=True,
            )
        await self._end_giveaway(dict(row))
        await ctx.respond(
            embed=discord.Embed(description="✅ Giveaway ended!", color=0x57F287), ephemeral=True
        )

    # ── /giveaway reroll ──────────────────────────────────────────────────────
    @giveaway_group.command(name="reroll", description="Reroll winners for an ended giveaway")
    @option("message_id", str, description="The message ID of the ended giveaway")
    @option("winners", int, description="How many new winners to pick", required=False, default=1)
    async def giveaway_reroll(self, ctx: discord.ApplicationContext, message_id: str, winners: int = 1):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        try:
            mid = int(message_id)
        except ValueError:
            return await ctx.respond(
                embed=discord.Embed(description="❌ Invalid message ID.", color=0xED4245), ephemeral=True
            )
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM giveaways WHERE message_id=? AND guild_id=?", (mid, ctx.guild.id)
            ) as cur:
                row = await cur.fetchone()

        if not row:
            return await ctx.respond(
                embed=discord.Embed(description="❌ Giveaway not found.", color=0xED4245), ephemeral=True
            )

        channel = ctx.guild.get_channel(row["channel_id"])
        try:
            message = await channel.fetch_message(mid)
        except Exception:
            return await ctx.respond(
                embed=discord.Embed(description="❌ Could not fetch the giveaway message.", color=0xED4245),
                ephemeral=True,
            )

        reaction = discord.utils.get(message.reactions, emoji=GIVEAWAY_EMOJI)
        entries = []
        req_role_ids = parse_required_role_ids(row)
        if reaction:
            async for user in reaction.users():
                if not user.bot:
                    member = ctx.guild.get_member(user.id)
                    if not member:
                        try:
                            member = await ctx.guild.fetch_member(user.id)
                        except Exception:
                            member = None
                    if member:
                        if req_role_ids:
                            if any(r.id in req_role_ids for r in member.roles):
                                entries.append(user.id)
                        else:
                            entries.append(user.id)

        if not entries:
            return await ctx.respond(
                embed=discord.Embed(description="😔 No valid entries to reroll from.", color=0xED4245),
                ephemeral=True,
            )

        n = min(winners, len(entries))
        winner_ids = random.sample(entries, n)
        mentions = " ".join(f"<@{w}>" for w in winner_ids)
        await channel.send(f"🔄 **Reroll!** New winner(s): {mentions} — congratulations on **{row['prize']}**!")
        await ctx.respond(
            embed=discord.Embed(
                title="🔄 Rerolled!",
                description=f"New winner(s): {mentions}",
                color=0x57F287,
            ),
            ephemeral=True,
        )

    # ── /giveaway list ────────────────────────────────────────────────────────
    @giveaway_group.command(name="list", description="List all active giveaways in this server")
    async def giveaway_list(self, ctx: discord.ApplicationContext):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM giveaways WHERE guild_id=? AND ended=0 ORDER BY ends_at ASC",
                (ctx.guild.id,),
            ) as cur:
                rows = await cur.fetchall()

        if not rows:
            return await ctx.respond(
                embed=discord.Embed(description="📭 No active giveaways.", color=0xFEE75C),
                ephemeral=True,
            )

        embed = discord.Embed(title="🎉 Active Giveaways", color=0x5865F2)
        for r in rows:
            remaining = r["ends_at"] - time.time()
            req_role_ids = parse_required_role_ids(dict(r))
            if req_role_ids:
                roles_str = ", ".join(f"<@&{rid}>" for rid in req_role_ids)
                role_info = f"Required Roles: {roles_str}\n"
            else:
                role_info = "Eligibility: Everyone\n"
            embed.add_field(
                name=f"🏆 {r['prize']}",
                value=(
                    f"Channel: <#{r['channel_id']}>\n"
                    f"{role_info}"
                    f"Ends in: `{fmt_time(remaining)}`\n"
                    f"Winners: {r['winners']} | ID: `{r['message_id']}`"
                ),
                inline=False,
            )
        await ctx.respond(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(Giveaway(bot))
