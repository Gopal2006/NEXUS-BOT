"""
Help Cog — Categorized, interactive, paginated help menu.
Tier: Staff Only (As configured by server management)
Commands:
  /help [command_or_category]
  n!help [command_or_category]
"""

import discord
from discord.ext import commands
from discord import option

from core.config import BRAND_NAME, SUPPORT_SERVER
from core.permissions import requires_tier
from core.ui import COLOR_BLURPLE, COLOR_GREEN

CATEGORIES = {
    "overview": {
        "title": "🏠 Nexus Overview & Quickstart",
        "description": (
            f"Welcome to **{BRAND_NAME}** — the streamlined, high-performance Discord bot.\n\n"
            "**Key Command Invocation Modes:**\n"
            "• **Slash Commands:** `/` (recommended)\n"
            "• **Text Prefix:** `n!` or `N!` (e.g. `n!help`, `n!ping`)\n"
            "• **Non-Prefix:** Direct command execution for authorized users\n\n"
            "Use the dropdown menu below to explore features by category, "
            "or type `n!help <category>` for direct access."
        ),
        "fields": [
            ("🛡️ Moderation", "Ban, kick, softban, mute, warn, warnings, clearwarns, purge, lock/unlock, lockdown, nick, role", False),
            ("⚙️ Administration", "Setup logs, bot-role permissions, welcome/leave messages, server configuration", False),
            ("📢 Announcements & DMs", "Interactive announcement builder, user DMs, role broadcasts with buttons", False),
            ("🎁 Giveaways & Polls", "Automated giveaways with role requirements, interactive button voting", False),
            ("🎫 Support Tickets", "Private ticket channels with intake modal, transcript generation, staff role", False),
            ("🎮 Mini-Games", "Interactive Tic-Tac-Toe, Rock-Paper-Scissors (solo & 2P), and Number Guessing", False),
            ("💡 Utility", "Profile inspection (/userinfo), comprehensive server info (/serverinfo), and bot owner telemetry", False),
        ],
    },
    "moderation": {
        "title": "🛡️ Moderation System",
        "description": "Staff-level disciplinary tools with strict reason requirements, case IDs, and audit logging.",
        "fields": [
            ("`/kick <member> <reason>`", "Kick member from server. Mandatory reason. DMs target.", False),
            ("`/ban <member> <reason> [delete_days]`", "Ban member permanently with optional 0-7 day message prune.", False),
            ("`/unban <user_id> [reason]`", "Unban user by their 18-19 digit Discord ID.", False),
            ("`/softban <member> <reason>`", "Ban and immediately unban to clear past 24h messages. Mandatory reason.", False),
            ("`/mute <member> <duration> <reason>`", "Timeout member (`10m`, `2h`, `1d`). Mandatory reason.", False),
            ("`/unmute <member> [reason]`", "Remove active timeout from member.", False),
            ("`/warn <member> <reason>`", "Issue a formal recorded warning case with DM notification.", False),
            ("`/warnings <member>`", "View warning case history, moderator names, and timestamps.", False),
            ("`/clearwarns <member>`", "Delete all warning cases for a member.", False),
            ("`/purge <amount> [member]`", "Bulk delete between 1 and 100 messages in current channel.", False),
            ("`/lock [#channel] [reason]`", "Lock channel: prevents @everyone from chatting.", False),
            ("`/unlock [#channel]`", "Unlock channel: restores normal messaging.", False),
            ("`/lockdown [scope] [reason]`", "Emergency server lockdown: locks all text channels across server.", False),
            ("`/unlockdown [scope]`", "Lifts emergency server lockdown.", False),
            ("`/nick <member> [nickname]`", "Change or reset member server nickname.", False),
            ("`/role add <member> <role>`", "Assign role adhering to hierarchy.", False),
            ("`/role remove <member> <role>`", "Revoke role adhering to hierarchy.", False),
        ],
    },
    "admin": {
        "title": "⚙️ Administration & Server Setup",
        "description": "Server configuration, audit logging, and security role isolation.",
        "fields": [
            ("`/setupbot`", "Creates `📁 NEXUS LOGS` with 4 private audit channels: mod, server, activity, cmd.", False),
            ("`/set-botrole <role>`", "**Server Owner Only.** Designates the management role that can run bot commands.", False),
            ("`/remove-botrole`", "**Server Owner Only.** Removes the bot-role restriction.", False),
            ("`/set-welcome <channel> [message]`", "Configure welcome channel and customizable join message template.", False),
            ("`/set-leave <channel> [message]`", "Configure farewell channel and customizable leave message template.", False),
            ("`/set-log <channel>`", "Set primary moderation audit log channel.", False),
            ("`/set-cmdlog <channel>`", "Set dedicated execution log channel for commands.", False),
            ("`/config`", "View sleek server configuration, assigned roles, and channels.", False),
        ],
    },
    "announcements": {
        "title": "📢 Announcements & Direct Messaging",
        "description": "Rich announcement tools and official server direct messaging.",
        "fields": [
            ("`/announce`", "Opens modal popup for Title, Message, Color theme, Banner image, and URL buttons.", False),
            ("`/dm-user <member>` (alias `/dm`)", "Opens modal popup to send a formatted direct message with buttons to a user.", False),
            ("`/dm-role <role>`", "Opens modal popup to broadcast a formatted direct message to every human member in a role.", False),
        ],
    },
    "giveaways": {
        "title": "🎁 Giveaways & Interactive Polls",
        "description": "Community engagement systems with live button interactions.",
        "fields": [
            ("`/gstart <duration> <winners> <prize> [roles]`", "Launch giveaway with interactive modal (survives restarts).", False),
            ("`/gend <message_id>`", "Force-conclude an active giveaway early.", False),
            ("`/greroll <message_id>`", "Re-pick new winner(s) from eligible entrants.", False),
            ("`/glist`", "List all active giveaways in the server.", False),
            ("`/poll`", "Create an interactive button poll (up to 5 choices). One vote per user.", False),
            ("`/endpoll <message_id>`", "Conclude a poll early and show final vote breakdown.", False),
        ],
    },
    "tickets": {
        "title": "🎫 Support Ticket System",
        "description": "Private support channels with intake modals and staff roles.",
        "fields": [
            ("`/ticket setup <channel>`", "Post the official ticket creation panel with 'Open Ticket' button.", False),
            ("`/ticket set-role <role>`", "Assign which staff role handles and answers support tickets.", False),
            ("`/ticket close`", "Close support ticket (staff and server owner only, generates transcript).", False),
            ("`/ticket add <member>`", "Add member into private ticket channel.", False),
            ("`/ticket remove <member>`", "Remove member from ticket channel.", False),
        ],
    },
    "games": {
        "title": "🎮 Mini-Games",
        "description": "Interactive Discord button games for members.",
        "fields": [
            ("`/tictactoe <opponent>`", "Interactive 3x3 Tic-Tac-Toe button game with turn enforcement.", False),
            ("`/rps [opponent]`", "Rock-Paper-Scissors against bot or challenge another member.", False),
            ("`/guess`", "Number guessing game (1-100) with interactive hints in a single edited message.", False),
        ],
    },
    "utility": {
        "title": "💡 Utility & Information Commands",
        "description": "Profile inspection and server analytics.",
        "fields": [
            ("`/userinfo [member]` or `n!userinfo`", "Deep inspection: account creation, join date, roles, and permissions.", False),
            ("`/serverinfo` or `n!serverinfo`", "Comprehensive server overview, demographics, channels, and security.", False),
            ("`/ping`, `/stats`, `/uptime`", "**Bot Owner Only.** Process diagnostics, cluster reach, and latency.", False),
        ],
    },
}


class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Overview & Quickstart", value="overview", emoji="🏠", description="Bot summary and invocation modes"),
            discord.SelectOption(label="Moderation System", value="moderation", emoji="🛡️", description="Kick, ban, softban, mute, warn, purge, lock"),
            discord.SelectOption(label="Administration & Setup", value="admin", emoji="⚙️", description="Audit logs, bot-role, welcome/leave"),
            discord.SelectOption(label="Announcements & DMs", value="announcements", emoji="📢", description="Announcements and direct message modals"),
            discord.SelectOption(label="Giveaways & Polls", value="giveaways", emoji="🎁", description="Timed giveaways and interactive button polls"),
            discord.SelectOption(label="Support Tickets", value="tickets", emoji="🎫", description="Ticket intake panels and staff management"),
            discord.SelectOption(label="Mini-Games", value="games", emoji="🎮", description="Tic-Tac-Toe, Rock-Paper-Scissors, Guess"),
            discord.SelectOption(label="General Utility", value="utility", emoji="💡", description="Userinfo, serverinfo, and owner telemetry"),
        ]
        super().__init__(placeholder="Select a category to browse...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        cat_data = CATEGORIES.get(selected, CATEGORIES["overview"])

        embed = discord.Embed(
            title=cat_data["title"],
            description=cat_data["description"],
            color=COLOR_BLURPLE,
            timestamp=discord.utils.utcnow(),
        )
        for name, val, inline in cat_data["fields"]:
            embed.add_field(name=name, value=val, inline=inline)

        embed.set_footer(text=f"{BRAND_NAME} Help Center  •  Support: {SUPPORT_SERVER}")
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpDropdown())


class HelpCog(commands.Cog):
    """📖 Interactive help center."""

    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="help", description="View the interactive command manual and feature guide (Staff)")
    @requires_tier("staff")
    @option(
        "category",
        str,
        description="Category to view directly",
        choices=["overview", "moderation", "admin", "announcements", "giveaways", "tickets", "games", "utility"],
        required=False,
        default="overview",
    )
    async def slash_help(self, ctx: discord.ApplicationContext, category: str = "overview"):
        cat_data = CATEGORIES.get(category.lower(), CATEGORIES["overview"])
        embed = discord.Embed(
            title=cat_data["title"],
            description=cat_data["description"],
            color=COLOR_BLURPLE,
            timestamp=discord.utils.utcnow(),
        )
        for name, val, inline in cat_data["fields"]:
            embed.add_field(name=name, value=val, inline=inline)

        embed.set_footer(text=f"{BRAND_NAME} Help Center  •  Support: {SUPPORT_SERVER}")
        await ctx.respond(embed=embed, view=HelpView(), ephemeral=True)

    @commands.command(name="help")
    @requires_tier("staff")
    async def prefix_help(self, ctx: commands.Context, category: str = "overview"):
        """n!help [category] — Interactive help menu (Staff)"""
        cat_data = CATEGORIES.get(category.lower(), CATEGORIES["overview"])
        embed = discord.Embed(
            title=cat_data["title"],
            description=cat_data["description"],
            color=COLOR_BLURPLE,
            timestamp=discord.utils.utcnow(),
        )
        for name, val, inline in cat_data["fields"]:
            embed.add_field(name=name, value=val, inline=inline)

        embed.set_footer(text=f"{BRAND_NAME} Help Center  •  Support: {SUPPORT_SERVER}")
        await ctx.reply(embed=embed, view=HelpView())


def setup(bot):
    bot.add_cog(HelpCog(bot))
