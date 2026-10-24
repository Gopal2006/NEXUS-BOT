"""
NexusBot subclass featuring the resilient slash command interaction dispatcher,
dynamic non-prefix prefix handler, and gateway intents.
"""

import sys
import asyncio
import logging
import discord
from discord.ext import commands

from core.config import is_bot_owner, ENABLE_PRESENCE_INTENT

log = logging.getLogger("Nexus.Bot")


def disable_windows_quickedit():
    """Prevents Windows Console from freezing the asyncio loop when clicked or highlighted."""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.CreateFileW.restype = ctypes.c_void_p
            kernel32.GetStdHandle.restype = ctypes.c_void_p

            h = kernel32.CreateFileW("CONIN$", 0xC0000000, 3, None, 3, 0, None)
            if not h or h == ctypes.c_void_p(-1).value:
                h = kernel32.GetStdHandle(-10)

            if h and h != ctypes.c_void_p(-1).value:
                mode = ctypes.c_uint32()
                if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
                    new_mode = (mode.value & ~0x0040) | 0x0080
                    kernel32.SetConsoleMode(h, new_mode)
        except Exception:
            pass


disable_windows_quickedit()


def get_prefix(client, message: discord.Message) -> list[str]:
    """
    Dynamic prefix handler:
    Returns ['n!', 'N!', ''] for bot owners and authorized non-prefix users,
    and ['n!', 'N!'] for everyone else.
    """
    prefixes = ["n!", "N!"]
    author = getattr(message, "author", None)
    if author and not author.bot:
        if is_bot_owner(author.id) or author.id in getattr(client, "non_prefix_users", set()):
            return ["n!", "N!", ""]
    return prefixes


class NexusBot(commands.Bot):
    """
    Subclass of commands.Bot featuring a resilient slash command interaction dispatcher.
    Resolves Pycord's limitation where global commands fail to match guild interactions
    if Discord's /applications/commands registration endpoint is rate-limited (HTTP 429)
    or during delayed syncs.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_syncing = False
        self.non_prefix_users: set[int] = set()

    async def process_application_commands(
        self, interaction: discord.Interaction, auto_sync: bool | None = None
    ) -> None:
        if interaction.type not in (
            discord.InteractionType.application_command,
            discord.InteractionType.auto_complete,
        ):
            return

        command = None
        if interaction.data:
            cmd_id = interaction.data.get("id")
            cmd_name = interaction.data.get("name")
            guild_id = interaction.data.get("guild_id")
            if guild_id:
                guild_id = int(guild_id)

            # 1. Fast cache lookup
            if cmd_id and cmd_id in self._application_commands:
                command = self._application_commands[cmd_id]

            # 2. Resilient fallback: search registered & pending commands by name
            if command is None and cmd_name:
                all_cmds = list(self.application_commands) + list(self.pending_application_commands)
                for cmd in all_cmds:
                    if cmd.name == cmd_name:
                        # Global commands have cmd.guild_ids as None or [] -> matches ALL guilds!
                        if (
                            cmd.guild_ids is None
                            or not cmd.guild_ids
                            or (guild_id and (guild_id == cmd.guild_ids or (isinstance(cmd.guild_ids, (list, tuple, set)) and guild_id in cmd.guild_ids)))
                        ):
                            command = cmd
                            if cmd_id:
                                cmd.id = cmd_id
                                self._application_commands[cmd_id] = cmd
                            break

        if command is None:
            log.warning(f"Unknown slash command invoked: {interaction.data.get('name') if interaction.data else 'None'}")
            return self.dispatch("unknown_application_command", interaction)

        if interaction.type is discord.InteractionType.auto_complete:
            return self.dispatch(
                "application_command_auto_complete", interaction, command
            )

        ctx = await self.get_application_context(interaction)
        interaction.command = command
        await self.invoke_application_command(ctx)

    def get_application_command(
        self,
        name: str,
        guild_ids: list[int] | None = None,
        type: type = discord.ApplicationCommand,
    ):
        cmd = super().get_application_command(name, guild_ids=guild_ids, type=type)
        if cmd is not None:
            return cmd
        for c in self.pending_application_commands:
            if c.name == name and isinstance(c, type):
                if guild_ids is not None and c.guild_ids != guild_ids:
                    continue
                return c
        return None

    async def sync_slash_commands_safely(self):
        """
        Safely synchronizes global slash commands in the background without
        blocking the gateway event loop or hanging indefinitely during Discord rate limits.
        """
        if getattr(self, "_is_syncing", False):
            return
        self._is_syncing = True
        try:
            # Guarantee every command is marked global (guild_ids = None)
            for cmd in self.pending_application_commands:
                cmd.guild_ids = None

            log.info("Checking & registering global slash commands with Discord...")
            await asyncio.wait_for(self.sync_commands(), timeout=20.0)
            count = len(self.application_commands) or len(self.pending_application_commands)
            log.info(f"Loaded {count} global slash command(s) ✓")
        except asyncio.TimeoutError:
            count = len(self.application_commands) or len(self.pending_application_commands)
            log.warning(
                f"Discord command sync timed out (likely 429 rate limit backoff). "
                f"Internal resilient dispatcher is active; all {count} slash commands remain fully functional!"
            )
        except discord.HTTPException as e:
            if e.status == 429:
                log.warning(
                    f"Discord is currently rate-limiting command updates: {e}. "
                    "Resilient dispatcher is active; slash commands are fully functional."
                )
            else:
                log.error(f"Failed to sync slash commands with Discord: {e}")
        except Exception as e:
            log.error(f"Error while syncing slash commands: {e}")
        finally:
            self._is_syncing = False


# ── Gateway Intents ───────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
if ENABLE_PRESENCE_INTENT:
    intents.presences = True

# ── Primary Bot Instance ──────────────────────────────────────────────────────
bot = NexusBot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None,
    description="Nexus — All-Purpose Discord Bot",
    auto_sync_commands=False,
)
