"""
Polls Cog — Interactive Polls with Clickable Discord UI Buttons
Commands:
  /poll    — create a multi-choice or yes/no poll with interactive voting buttons
  /endpoll — manually conclude a poll and lock voting
"""

import discord
from discord.ext import commands
from discord import option
import aiosqlite
import asyncio
from pathlib import Path

DB_PATH = Path("nexus.db")
GLOBAL_OWNER_ID = 1201050377911554061

NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


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


class PollView(discord.ui.View):
    def __init__(
        self,
        question: str,
        choices: list[str],
        emojis: list[str],
        host_id: int,
        description: str = None,
        required_role: discord.Role = None,
    ):
        super().__init__(timeout=None)  # Active persistent view
        self.question = question
        self.choices = choices
        self.emojis = emojis
        self.host_id = host_id
        self.description = description
        self.required_role = required_role
        # user_id -> choice_index (0-based)
        self.votes: dict[int, int] = {}
        self.ended = False

        # Add buttons for each choice (up to 5 per row, max 2 rows)
        is_yes_no = (len(choices) == 2 and choices[0].lower() == "yes" and choices[1].lower() == "no")

        for idx, (choice, emoji) in enumerate(zip(choices, emojis)):
            row = 0 if idx < 5 else 1
            if is_yes_no:
                style = discord.ButtonStyle.success if idx == 0 else discord.ButtonStyle.danger
            else:
                style = discord.ButtonStyle.primary if idx % 2 == 0 else discord.ButtonStyle.secondary

            button = discord.ui.Button(
                label=choice[:80],
                emoji=emoji,
                style=style,
                row=row,
                custom_id=f"poll_opt_{idx}",
            )
            button.callback = self.make_vote_callback(idx)
            self.add_item(button)

        # End Poll button for host / staff
        end_btn = discord.ui.Button(
            label="End Poll",
            style=discord.ButtonStyle.danger,
            emoji="🏁",
            row=1 if len(choices) <= 4 else 2,
            custom_id="poll_end_btn",
        )
        end_btn.callback = self.end_poll_callback
        self.add_item(end_btn)

    def make_vote_callback(self, choice_idx: int):
        async def vote_callback(interaction: discord.Interaction):
            if self.ended:
                return await interaction.response.send_message("❌ This poll has already concluded.", ephemeral=True)

            if self.required_role:
                member = interaction.guild.get_member(interaction.user.id) or interaction.user
                if not hasattr(member, "roles") or not any(r.id == self.required_role.id for r in member.roles):
                    return await interaction.response.send_message(
                        f"🔒 Only members with the {self.required_role.mention} role can vote in this poll.",
                        ephemeral=True,
                    )

            user_id = interaction.user.id
            choice_name = self.choices[choice_idx]

            if user_id in self.votes and self.votes[user_id] == choice_idx:
                return await interaction.response.send_message(
                    f"ℹ️ You already voted for **{choice_name}**.", ephemeral=True
                )

            changed = user_id in self.votes
            self.votes[user_id] = choice_idx

            # Live update the embed
            new_embed = self.build_embed()
            await interaction.response.edit_message(embed=new_embed, view=self)

            if changed:
                await interaction.followup.send(
                    f"🔄 Your vote has been changed to **{choice_name}**!", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"✅ You voted for **{choice_name}**!", ephemeral=True
                )

        return vote_callback

    async def end_poll_callback(self, interaction: discord.Interaction):
        # Only poll creator, bot owner, server owner, or bot-role holder can end poll
        is_host = interaction.user.id == self.host_id
        is_owner = interaction.user.id in (GLOBAL_OWNER_ID, interaction.guild.owner_id)
        cfg = await get_config(interaction.guild.id)
        bot_role_id = cfg.get("bot_role_id")
        author = interaction.guild.get_member(interaction.user.id) or interaction.user
        has_bot_role = (
            bot_role_id
            and hasattr(author, "roles")
            and any(r.id == bot_role_id for r in author.roles)
        )

        if not (is_host or is_owner or has_bot_role):
            return await interaction.response.send_message(
                "❌ Only the poll creator, server owner, or members with the bot-role can end this poll.",
                ephemeral=True,
            )

        self.ended = True
        for item in self.children:
            item.disabled = True

        embed = self.build_embed(ended=True, ended_by=interaction.user)
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    def build_embed(self, ended: bool = False, ended_by: discord.Member = None) -> discord.Embed:
        total_votes = len(self.votes)

        # Count votes per choice
        counts = [0] * len(self.choices)
        for choice_idx in self.votes.values():
            counts[choice_idx] += 1

        # Determine winner if ended
        max_votes = max(counts) if counts else 0

        embed = discord.Embed(
            title=f"📊 {'[ENDED] ' if ended else ''}{self.question}",
            color=0x57F287 if ended else 0x5865F2,
            timestamp=discord.utils.utcnow(),
        )

        lines = []
        if getattr(self, "required_role", None):
            lines.append(f"🔒 **Eligible Voters:** {self.required_role.mention} only\n")
        if getattr(self, "description", None):
            lines.append(f"{self.description}\n")
        for idx, (choice, emoji, count) in enumerate(zip(self.choices, self.emojis, counts)):
            pct = round((count / total_votes * 100)) if total_votes > 0 else 0
            filled = round(pct / 10)
            bar = "█" * filled + "░" * (10 - filled)
            is_winner = ended and total_votes > 0 and count == max_votes
            trophy = " 🏆 **[WINNER]**" if is_winner else ""

            lines.append(f"{emoji} **{choice}**{trophy}\n`{bar}` **{pct}%** ({count} votes)")

        embed.description = "\n\n".join(lines)

        if ended:
            closer_str = f"Ended by {ended_by.display_name} • " if ended_by else ""
            embed.set_footer(text=f"🏁 Poll Concluded • {closer_str}Total Votes: {total_votes}")
        else:
            embed.set_footer(text=f"Click the buttons below to vote! • Total Votes: {total_votes}")

        return embed


# ── Poll Modal ────────────────────────────────────────────────────────────────
class PollModal(discord.ui.Modal):
    """
    Interactive modal popup for creating polls.
    Collects Question, Options, Duration, and optional Context Description.
    """
    def __init__(self, target_channel: discord.TextChannel, active_polls: dict, required_role: discord.Role = None):
        super().__init__(title="📊 Create Interactive Poll")
        self.target_channel = target_channel
        self.active_polls = active_polls
        self.required_role = required_role

        self.add_item(discord.ui.InputText(
            label="Poll Question",
            placeholder="e.g. Which server event should we host next?",
            style=discord.InputTextStyle.short,
            max_length=256,
            required=True,
            custom_id="poll_question",
        ))
        self.add_item(discord.ui.InputText(
            label="Poll Options (1 per line or separated by |)",
            placeholder="Option 1\nOption 2\nOption 3\n(Leave blank for Yes / No)",
            style=discord.InputTextStyle.long,
            max_length=1000,
            required=False,
            custom_id="poll_options",
        ))
        self.add_item(discord.ui.InputText(
            label="Duration in Minutes (Optional)",
            placeholder="0 = open indefinitely, or enter minutes (e.g. 60)",
            style=discord.InputTextStyle.short,
            max_length=10,
            required=False,
            custom_id="poll_duration",
        ))
        self.add_item(discord.ui.InputText(
            label="Extra Description / Context (Optional)",
            placeholder="Additional context or voting rules…",
            style=discord.InputTextStyle.long,
            max_length=500,
            required=False,
            custom_id="poll_description",
        ))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        question    = self.children[0].value.strip()
        raw_options = (self.children[1].value or "").strip()
        raw_dur     = (self.children[2].value or "0").strip()
        extra_desc  = (self.children[3].value or "").strip() or None

        try:
            duration = max(0, int(raw_dur))
        except ValueError:
            duration = 0

        if raw_options:
            choices = [
                opt.strip()
                for opt in raw_options.replace("|", "\n").split("\n")
                if opt.strip()
            ]
            if len(choices) < 2:
                return await interaction.followup.send(
                    embed=discord.Embed(description="❌ Please provide at least 2 options (or leave blank for Yes/No).", color=0xED4245),
                    ephemeral=True,
                )
            if len(choices) > 10:
                return await interaction.followup.send(
                    embed=discord.Embed(description="❌ Maximum 10 options allowed.", color=0xED4245),
                    ephemeral=True,
                )
        else:
            choices = ["Yes", "No"]

        is_yes_no = (len(choices) == 2 and choices[0].lower() == "yes" and choices[1].lower() == "no")
        emojis = ["✅", "❌"] if is_yes_no else NUMBER_EMOJIS[:len(choices)]

        view = PollView(
            question=question,
            choices=choices,
            emojis=emojis,
            host_id=interaction.user.id,
            description=extra_desc,
            required_role=self.required_role,
        )
        embed = view.build_embed()

        try:
            msg = await self.target_channel.send(embed=embed, view=view)
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
                    title="❌ Error Posting Poll",
                    description=f"Could not post poll: `{e}`",
                    color=0xED4245,
                ),
                ephemeral=True,
            )

        self.active_polls[msg.id] = view

        role_info = f"\n🔒 **Eligible Role:** {self.required_role.mention}" if self.required_role else ""
        await interaction.followup.send(
            embed=discord.Embed(
                title="✅ Poll Created",
                description=f"Your poll has been posted in {self.target_channel.mention} with interactive voting buttons!{role_info}\n\n🔗 [Jump to Poll]({msg.jump_url})",
                color=0x57F287,
            ),
            ephemeral=True,
        )

        if duration > 0:
            await asyncio.sleep(duration * 60)
            if not view.ended:
                view.ended = True
                for item in view.children:
                    item.disabled = True
                end_embed = view.build_embed(ended=True)
                try:
                    await msg.edit(embed=end_embed, view=view)
                except Exception:
                    pass
                self.active_polls.pop(msg.id, None)


class Polls(commands.Cog):
    """📊 Button-based Interactive Poll System."""

    def __init__(self, bot):
        self.bot = bot
        self.active_polls: dict[int, PollView] = {}

    @discord.slash_command(name="poll", description="Create an interactive poll via a popup modal")
    @option("channel", discord.TextChannel, description="Channel to post poll in (defaults to current)", required=False, default=None)
    @option("role", discord.Role, description="Only members with this role can vote (defaults to everyone)", required=False, default=None)
    async def poll(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel = None,
        role: discord.Role = None,
    ):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)

        target_ch = channel or ctx.channel
        modal = PollModal(target_channel=target_ch, active_polls=self.active_polls, required_role=role)
        await ctx.send_modal(modal)

    @discord.slash_command(name="endpoll", description="End an active poll by message ID")
    @option("message_id", str, description="The message ID of the poll")
    async def endpoll(self, ctx: discord.ApplicationContext, message_id: str):
        if not await is_bot_admin(ctx):
            return await no_perm(ctx)
        try:
            mid = int(message_id.strip())
        except ValueError:
            return await ctx.respond(
                embed=discord.Embed(description="❌ Invalid Message ID.", color=0xED4245), ephemeral=True
            )

        if mid in self.active_polls:
            view = self.active_polls[mid]
            view.ended = True
            for item in view.children:
                item.disabled = True
            try:
                msg = await ctx.channel.fetch_message(mid)
                await msg.edit(embed=view.build_embed(ended=True, ended_by=ctx.author), view=view)
            except Exception:
                pass
            self.active_polls.pop(mid, None)
            return await ctx.respond(
                embed=discord.Embed(description="🏁 Poll has been concluded.", color=0x57F287),
                ephemeral=True,
            )

        # Fallback: fetch message directly
        try:
            msg = await ctx.channel.fetch_message(mid)
            if msg.embeds:
                emb = msg.embeds[0]
                emb.title = f"🏁 [ENDED] {emb.title or ''}"
                emb.color = 0x57F287
                emb.set_footer(text=f"Poll concluded by {ctx.author.name}")
                await msg.edit(embed=emb, view=None)
                return await ctx.respond(
                    embed=discord.Embed(description="🏁 Poll closed.", color=0x57F287), ephemeral=True
                )
        except Exception as e:
            return await ctx.respond(
                embed=discord.Embed(description=f"❌ Could not find poll message in this channel: `{e}`", color=0xED4245),
                ephemeral=True,
            )


def setup(bot):
    bot.add_cog(Polls(bot))
