"""
Mini-Games System Cog
Interactive button-based games for server members:
1. Tic-Tac-Toe (2 players)
2. Rock-Paper-Scissors (vs Bot or 2-player)
3. Number Guessing (1-100, edits same message on every guess)
"""

import random
import logging
import discord
from discord.ext import commands
from discord import option

from core.ui import ui_embed, ui_error, ui_success, ui_info

log = logging.getLogger("Nexus.Games")


# ── 1. Tic-Tac-Toe ────────────────────────────────────────────────────────────

class TTTButton(discord.ui.Button):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToeView = self.view
        if interaction.user.id != view.current_player.id:
            return await interaction.response.send_message("❌ It is not your turn!", ephemeral=True)

        if self.label != "\u200b":
            return await interaction.response.send_message("❌ That tile is already taken!", ephemeral=True)

        symbol = "X" if view.current_player.id == view.player_x.id else "O"
        self.label = symbol
        self.style = discord.ButtonStyle.primary if symbol == "X" else discord.ButtonStyle.danger
        self.disabled = True
        view.board[self.y][self.x] = symbol

        winner = view.check_winner()
        if winner:
            for child in view.children:
                child.disabled = True
            await interaction.response.edit_message(
                embed=ui_embed(
                    title="🎉 Tic-Tac-Toe: Game Over!",
                    description=f"🏆 **{view.current_player.mention} ({winner}) has WON!**",
                    color=0x57F287,
                ),
                view=view,
            )
            view.stop()
            return

        if view.is_full():
            for child in view.children:
                child.disabled = True
            await interaction.response.edit_message(
                embed=ui_embed(
                    title="🤝 Tic-Tac-Toe: Tie Game!",
                    description="It's a draw! Well played by both players.",
                    color=0xFEE75C,
                ),
                view=view,
            )
            view.stop()
            return

        # Switch turns
        view.current_player = view.player_o if view.current_player.id == view.player_x.id else view.player_x
        await interaction.response.edit_message(
            embed=ui_embed(
                title="🎮 Tic-Tac-Toe",
                description=f"**Turn:** {view.current_player.mention} ({'X' if view.current_player.id == view.player_x.id else 'O'})\n"
                            f"**Players:** {view.player_x.mention} (X) vs {view.player_o.mention} (O)",
                color=0x5865F2,
            ),
            view=view,
        )


class TicTacToeView(discord.ui.View):
    def __init__(self, player_x: discord.Member, player_o: discord.Member):
        super().__init__(timeout=120)
        self.player_x = player_x
        self.player_o = player_o
        self.current_player = player_x
        self.board = [["\u200b" for _ in range(3)] for _ in range(3)]

        for y in range(3):
            for x in range(3):
                self.add_item(TTTButton(x, y))

    def check_winner(self) -> str | None:
        b = self.board
        # Horizontal & Vertical
        for i in range(3):
            if b[i][0] == b[i][1] == b[i][2] != "\u200b":
                return b[i][0]
            if b[0][i] == b[1][i] == b[2][i] != "\u200b":
                return b[0][i]
        # Diagonals
        if b[0][0] == b[1][1] == b[2][2] != "\u200b":
            return b[0][0]
        if b[0][2] == b[1][1] == b[2][0] != "\u200b":
            return b[0][2]
        return None

    def is_full(self) -> bool:
        return all(cell != "\u200b" for row in self.board for cell in row)


# ── 2. Rock-Paper-Scissors (Solo vs Bot & 2-Player) ───────────────────────────

class RPSButton(discord.ui.Button):
    def __init__(self, choice: str, emoji: str):
        super().__init__(style=discord.ButtonStyle.primary, label=choice, emoji=emoji)
        self.choice_name = choice

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if isinstance(view, RPSSoloView):
            await view.handle_choice(interaction, self.choice_name)
        elif isinstance(view, RPSTwoPlayerView):
            await view.handle_choice(interaction, self.choice_name)


class RPSSoloView(discord.ui.View):
    def __init__(self, player: discord.Member):
        super().__init__(timeout=60)
        self.player = player
        self.add_item(RPSButton("Rock", "🪨"))
        self.add_item(RPSButton("Paper", "📄"))
        self.add_item(RPSButton("Scissors", "✂️"))

    async def handle_choice(self, interaction: discord.Interaction, user_choice: str):
        if interaction.user.id != self.player.id:
            return await interaction.response.send_message("❌ This is not your game!", ephemeral=True)

        bot_choice = random.choice(["Rock", "Paper", "Scissors"])

        for child in self.children:
            child.disabled = True

        outcomes = {
            ("Rock", "Scissors"): "win",
            ("Scissors", "Paper"): "win",
            ("Paper", "Rock"): "win",
        }

        if user_choice == bot_choice:
            result = "🤝 It's a Tie!"
            color = 0xFEE75C
        elif (user_choice, bot_choice) in outcomes:
            result = "🎉 You Win!"
            color = 0x57F287
        else:
            result = "💀 You Lost!"
            color = 0xED4245

        embed = ui_embed(
            title=f"✂️ Rock-Paper-Scissors: {result}",
            description=f"**Your Choice:** {user_choice}\n**Bot Choice:** {bot_choice}",
            color=color,
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()


class RPSTwoPlayerView(discord.ui.View):
    def __init__(self, p1: discord.Member, p2: discord.Member):
        super().__init__(timeout=90)
        self.p1 = p1
        self.p2 = p2
        self.choices: dict[int, str] = {}
        self.add_item(RPSButton("Rock", "🪨"))
        self.add_item(RPSButton("Paper", "📄"))
        self.add_item(RPSButton("Scissors", "✂️"))

    async def handle_choice(self, interaction: discord.Interaction, choice: str):
        uid = interaction.user.id
        if uid not in (self.p1.id, self.p2.id):
            return await interaction.response.send_message("❌ You are not a player in this match!", ephemeral=True)

        if uid in self.choices:
            return await interaction.response.send_message("⚠️ You have already locked in your move!", ephemeral=True)

        self.choices[uid] = choice
        await interaction.response.send_message(f"✅ You chose **{choice}**! Waiting for opponent...", ephemeral=True)

        # Both have chosen!
        if len(self.choices) == 2:
            p1_c = self.choices[self.p1.id]
            p2_c = self.choices[self.p2.id]

            for child in self.children:
                child.disabled = True

            outcomes = {
                ("Rock", "Scissors"): self.p1,
                ("Scissors", "Paper"): self.p1,
                ("Paper", "Rock"): self.p1,
                ("Scissors", "Rock"): self.p2,
                ("Paper", "Scissors"): self.p2,
                ("Rock", "Paper"): self.p2,
            }

            if p1_c == p2_c:
                result_title = "🤝 Tie Game!"
                result_desc = f"Both players selected **{p1_c}**!"
                color = 0xFEE75C
            else:
                winner = outcomes[(p1_c, p2_c)]
                result_title = f"🎉 {winner.display_name} Wins!"
                result_desc = (
                    f"**{self.p1.mention}:** {p1_c}\n"
                    f"**{self.p2.mention}:** {p2_c}\n\n"
                    f"🏆 **Winner:** {winner.mention}"
                )
                color = 0x57F287

            embed = ui_embed(
                title=f"✂️ Rock-Paper-Scissors: {result_title}",
                description=result_desc,
                color=color,
            )
            if interaction.message:
                await interaction.message.edit(embed=embed, view=self)
            self.stop()


# ── 3. Number Guessing (Edits existing message on each guess) ─────────────────

class GuessView(discord.ui.View):
    def __init__(self, player: discord.Member, target: int, max_attempts: int = 7):
        super().__init__(timeout=120)
        self.player = player
        self.target = target
        self.attempts_left = max_attempts
        self.total_attempts = max_attempts
        self.history = []

    @discord.ui.button(label="Submit Guess", emoji="🔢", style=discord.ButtonStyle.primary)
    async def guess_btn(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user.id != self.player.id:
            return await interaction.response.send_message("❌ This is not your game! Run `/guess` to start your own.", ephemeral=True)
        modal = GuessInputModal(game_view=self)
        await interaction.response.send_modal(modal)


class GuessInputModal(discord.ui.Modal):
    def __init__(self, game_view: GuessView):
        super().__init__(title="🔢 Guess the Number (1-100)")
        self.game_view = game_view
        self.add_item(discord.ui.InputText(
            label="Your Number Guess",
            placeholder="Enter an integer between 1 and 100",
            max_length=3,
        ))

    async def callback(self, interaction: discord.Interaction):
        raw = self.children[0].value.strip()
        if not raw.isdigit():
            return await interaction.response.send_message("❌ Please enter a valid number (1-100).", ephemeral=True)

        guess = int(raw)
        if guess < 1 or guess > 100:
            return await interaction.response.send_message("❌ Number must be between 1 and 100.", ephemeral=True)

        view = self.game_view
        view.attempts_left -= 1
        used = view.total_attempts - view.attempts_left

        if guess == view.target:
            for child in view.children:
                child.disabled = True
            embed = discord.Embed(
                title="🎉 BINGO! You Won!",
                description=(
                    f"**{interaction.user.mention}** correctly guessed the secret number **{view.target}**!\n\n"
                    f"🎯 **Attempts Used:** `{used}/{view.total_attempts}`"
                ),
                color=0x57F287,
            )
            await interaction.response.edit_message(embed=embed, view=view)
            view.stop()
            return

        if view.attempts_left <= 0:
            for child in view.children:
                child.disabled = True
            embed = discord.Embed(
                title="💀 Game Over!",
                description=(
                    f"You ran out of attempts! The secret number was **{view.target}**.\n\n"
                    "Better luck next time!"
                ),
                color=0xED4245,
            )
            await interaction.response.edit_message(embed=embed, view=view)
            view.stop()
            return

        hint = "Higher 📈" if guess < view.target else "Lower 📉"
        view.history.append(f"`{guess}` → **{hint}**")

        history_str = "\n".join(view.history[-5:])
        embed = discord.Embed(
            title="🔢 Number Guessing Game (1-100)",
            description=(
                f"**Current Status:** {hint}\n"
                f"**Attempts Remaining:** `{view.attempts_left}/{view.total_attempts}`\n\n"
                f"**Recent Guesses:**\n{history_str}\n\n"
                "Click **Submit Guess** below to try again!"
            ),
            color=0x5865F2,
        )
        await interaction.response.edit_message(embed=embed, view=view)


# ── Games Cog ─────────────────────────────────────────────────────────────────

class GamesCog(commands.Cog, name="Games"):
    """🎮 Interactive mini-games."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Slash: /tictactoe ─────────────────────────────────────────────────────
    @discord.slash_command(name="tictactoe", description="Challenge another player to Tic-Tac-Toe")
    @option("opponent", discord.Member, description="The member you want to challenge")
    async def slash_ttt(self, ctx: discord.ApplicationContext, opponent: discord.Member):
        if opponent.bot:
            return await ctx.respond(embed=ui_error("Invalid Opponent", "You cannot challenge a bot."), ephemeral=True)
        if opponent.id == ctx.author.id:
            return await ctx.respond(embed=ui_error("Invalid Opponent", "You cannot challenge yourself."), ephemeral=True)

        view = TicTacToeView(player_x=ctx.author, player_o=opponent)
        embed = ui_embed(
            title="🎮 Tic-Tac-Toe Challenge",
            description=f"**Players:** {ctx.author.mention} (X) vs {opponent.mention} (O)\n**Turn:** {ctx.author.mention} (X)",
            color=0x5865F2,
        )
        await ctx.respond(embed=embed, view=view)

    # ── Slash: /rps ───────────────────────────────────────────────────────────
    @discord.slash_command(name="rps", description="Play Rock, Paper, Scissors against another member or the bot")
    @option("opponent", discord.Member, description="Opponent to challenge (leave empty to play vs bot)", required=False, default=None)
    async def slash_rps(self, ctx: discord.ApplicationContext, opponent: discord.Member = None):
        if opponent and opponent.id == ctx.author.id:
            return await ctx.respond(embed=ui_error("Invalid Opponent", "You cannot challenge yourself."), ephemeral=True)
        if opponent and opponent.bot:
            return await ctx.respond(embed=ui_error("Invalid Opponent", "To play against the bot, omit the opponent parameter."), ephemeral=True)

        if opponent:
            view = RPSTwoPlayerView(p1=ctx.author, p2=opponent)
            embed = ui_embed(
                title="✂️ Rock-Paper-Scissors Match",
                description=(
                    f"**Players:** {ctx.author.mention} vs {opponent.mention}\n\n"
                    "Both players, choose your move below! Selections are hidden until both players choose."
                ),
                color=0x5865F2,
            )
            await ctx.respond(embed=embed, view=view)
        else:
            view = RPSSoloView(player=ctx.author)
            embed = ui_embed(
                title="✂️ Rock-Paper-Scissors",
                description="Choose your move below against the bot!",
                color=0x5865F2,
            )
            await ctx.respond(embed=embed, view=view)

    # ── Slash: /guess ─────────────────────────────────────────────────────────
    @discord.slash_command(name="guess", description="Number guessing game (1-100)")
    async def slash_guess(self, ctx: discord.ApplicationContext):
        secret = random.randint(1, 100)
        view = GuessView(player=ctx.author, target=secret, max_attempts=7)
        embed = discord.Embed(
            title="🔢 Number Guessing Game (1-100)",
            description=(
                f"I've picked a secret number between **1** and **100**!\n"
                f"You have **7 attempts** to find it.\n\n"
                f"Click **Submit Guess** below to make your first guess."
            ),
            color=0x5865F2,
        )
        await ctx.respond(embed=embed, view=view)

    # ── Prefix: n!tictactoe, n!rps, n!guess ───────────────────────────────────
    @commands.command(name="tictactoe", aliases=["ttt"])
    async def prefix_ttt(self, ctx: commands.Context, opponent: discord.Member = None):
        if not opponent or opponent.bot or opponent.id == ctx.author.id:
            return await ctx.reply("ℹ️ Usage: `n!tictactoe <@opponent>` (cannot challenge bots or yourself)")
        view = TicTacToeView(player_x=ctx.author, player_o=opponent)
        embed = ui_embed(
            title="🎮 Tic-Tac-Toe Challenge",
            description=f"**Players:** {ctx.author.mention} (X) vs {opponent.mention} (O)\n**Turn:** {ctx.author.mention} (X)",
            color=0x5865F2,
        )
        await ctx.reply(embed=embed, view=view)

    @commands.command(name="rps")
    async def prefix_rps(self, ctx: commands.Context, opponent: discord.Member = None):
        if opponent and opponent.id == ctx.author.id:
            return await ctx.reply("❌ You cannot challenge yourself.")
        if opponent and opponent.bot:
            return await ctx.reply("❌ To play vs the bot, run `n!rps` without an opponent.")

        if opponent:
            view = RPSTwoPlayerView(p1=ctx.author, p2=opponent)
            embed = ui_embed(
                title="✂️ Rock-Paper-Scissors Match",
                description=(
                    f"**Players:** {ctx.author.mention} vs {opponent.mention}\n\n"
                    "Both players, choose your move below! Selections are hidden until both players choose."
                ),
                color=0x5865F2,
            )
            await ctx.reply(embed=embed, view=view)
        else:
            view = RPSSoloView(player=ctx.author)
            embed = ui_embed(title="✂️ Rock-Paper-Scissors", description="Choose your move below against the bot!", color=0x5865F2)
            await ctx.reply(embed=embed, view=view)

    @commands.command(name="guess", aliases=["numberguess"])
    async def prefix_guess(self, ctx: commands.Context):
        secret = random.randint(1, 100)
        view = GuessView(player=ctx.author, target=secret, max_attempts=7)
        embed = discord.Embed(
            title="🔢 Number Guessing Game (1-100)",
            description=(
                f"I've picked a secret number between **1** and **100**!\n"
                f"You have **7 attempts** to find it.\n\n"
                f"Click **Submit Guess** below to make your first guess."
            ),
            color=0x5865F2,
        )
        await ctx.reply(embed=embed, view=view)


def setup(bot: commands.Bot):
    bot.add_cog(GamesCog(bot))
