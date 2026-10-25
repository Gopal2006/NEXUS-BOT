"""
Configuration loader for Nexus Bot and Dashboard API.
Loads typed settings from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()

# Discord Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Brand Identity
BRAND_NAME = os.getenv("BRAND_NAME", "Nexus").strip()
SUPPORT_SERVER = os.getenv("SUPPORT_SERVER", "https://discord.gg/PLACEHOLDER").strip()

# Discord application permission bitfield used in generated invite URLs.
# Scoped to the bot's audited moderation, role/channel, message, and interaction
# features; it intentionally excludes Administrator (8).
BOT_INVITE_PERMISSIONS = 1374792445014

# Bot Owners: Comma-separated list of Discord user IDs
# Defaults to original developer ID if unspecified
_raw_owners = os.getenv("OWNER_IDS", "1201050377911554061")
OWNER_IDS: set[int] = set()
for item in _raw_owners.split(","):
    item = item.strip()
    if item.isdigit():
        OWNER_IDS.add(int(item))

if not OWNER_IDS:
    OWNER_IDS.add(1201050377911554061)

# Primary owner ID (for backward compatibility if needed)
PRIMARY_OWNER_ID: int = next(iter(OWNER_IDS))

# Database Settings
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "nexus.db"))

# Intents
ENABLE_PRESENCE_INTENT = os.getenv("ENABLE_PRESENCE_INTENT", "false").lower() in ("true", "1", "yes")

# Networking & Cloud Deployment
PORT = int(os.getenv("PORT") or os.getenv("API_PORT") or 8000)

# Dashboard API Settings
API_ENABLED = os.getenv("API_ENABLED", "true").lower() in ("true", "1", "yes")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT") or PORT)
DASHBOARD_API_KEY = os.getenv("DASHBOARD_API_KEY", "change_me_to_a_long_random_string").strip()
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,https://localhost:3000").split(",")
    if origin.strip()
]

# Cloudflare Tunnel (optional)
TUNNEL_ENABLED = os.getenv("TUNNEL_ENABLED", "false").lower() in ("true", "1", "yes")
CF_TUNNEL_TOKEN = os.getenv("CF_TUNNEL_TOKEN", "").strip()
CF_TUNNEL_URL = os.getenv("CF_TUNNEL_URL", "").strip()


def is_bot_owner(user_id: int) -> bool:
    """Checks whether a given Discord User ID is a designated bot owner."""
    return user_id in OWNER_IDS
