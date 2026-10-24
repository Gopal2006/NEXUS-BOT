"""
Nexus Bot Entry Point
Thin launcher initializing config, database, core listeners, cogs, and FastAPI server.
"""

import os
import sys
import asyncio
import logging
import discord

from core.config import (
    BOT_TOKEN,
    PORT,
    API_ENABLED,
    API_PORT,
    API_HOST,
    BRAND_NAME,
)
from core.bot import bot, disable_windows_quickedit
from core.errors import setup_error_handlers
from core.events import setup_core_events
from db.database import run_migrations, get_non_prefix_users, close_db

# ── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("Nexus")


async def setup_nexus():
    """Initializes database migrations, loads non-prefix users, and loads all bot cogs."""
    disable_windows_quickedit()

    # 1. Database migrations & preload non-prefix users
    log.info("Running database migrations...")
    await run_migrations()
    bot.non_prefix_users = await get_non_prefix_users()
    log.info(f"Loaded {len(bot.non_prefix_users)} authorized non-prefix user(s) ✓")

    # 2. Attach global error handlers & core lifecycle events
    setup_error_handlers(bot)
    setup_core_events(bot)

    # 3. Load active cogs
    cog_files = [
        "cogs.admin",
        "cogs.announcements",
        "cogs.dm",
        "cogs.giveaway",
        "cogs.moderation",
        "cogs.polls",
        "cogs.tickets",
        "cogs.help",
        "cogs.utility",
        "cogs.logging_events",
        "cogs.autorole",
        "cogs.reaction_roles",
        "cogs.leveling",
        "cogs.afk",
        "cogs.autoresponder",
        "cogs.games",
    ]
    for cog in cog_files:
        try:
            bot.load_extension(cog)
            log.info(f"  ✓ Loaded cog: {cog}")
        except Exception as e:
            log.error(f"  ✗ Failed to load {cog}: {e}")


def main():
    """Main launcher."""
    disable_windows_quickedit()

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        log.critical("BOT_TOKEN not configured! Set it in your .env file.")
        sys.exit(1)

    # Initialize bot and cogs on bot.loop
    bot.loop.run_until_complete(setup_nexus())

    # Launch dashboard API backend if enabled
    if API_ENABLED:
        from api.app import run_api_server
        server_port = int(PORT) if PORT else API_PORT
        bot.loop.create_task(run_api_server(host=API_HOST, port=server_port))

    try:
        log.info(f"Starting {BRAND_NAME} Discord Bot...")
        bot.run(BOT_TOKEN)
    except discord.errors.PrivilegedIntentsRequired:
        log.critical(
            "\n" + "=" * 65 + "\n"
            "❌ PRIVILEGED INTENTS REQUIRED!\n"
            "Please enable Privileged Gateway Intents in Discord Developer Portal:\n"
            "   • [✓] Server Members Intent\n"
            "   • [✓] Message Content Intent\n"
            + "=" * 65
        )
    except discord.errors.LoginFailure:
        log.critical("❌ Invalid BOT_TOKEN! Please check your .env file.")
    except Exception as e:
        log.error(f"Unexpected error running bot: {e}")
    finally:
        if not bot.is_closed():
            bot.loop.run_until_complete(bot.close())
        bot.loop.run_until_complete(close_db())


if __name__ == "__main__":
    main()
