"""
Shared UI design system, color palettes, and embed builders for Nexus Bot.
Follows a curated Discord-dark aesthetic with vibrant accents.
"""

import discord
from typing import Optional

# Standard Color Palette
COLOR_BLURPLE = 0x5865F2
COLOR_GREEN   = 0x57F287
COLOR_RED     = 0xED4245
COLOR_GOLD    = 0xFEE75C
COLOR_BLUE    = 0x3498DB
COLOR_PURPLE  = 0x9B59B6
COLOR_FUCHSIA = 0xEB459E
COLOR_PINK    = 0xFF70A6
COLOR_CYAN    = 0x1ABC9C
COLOR_ORANGE  = 0xE67E22
COLOR_DARK    = 0x2B2D31

COLOR_PRESETS = {
    "blurple": COLOR_BLURPLE,
    "blue":    COLOR_BLUE,
    "red":     COLOR_RED,
    "green":   COLOR_GREEN,
    "gold":    COLOR_GOLD,
    "yellow":  0xFFFF00,
    "purple":  COLOR_PURPLE,
    "fuchsia": COLOR_FUCHSIA,
    "pink":    COLOR_PINK,
    "cyan":    COLOR_CYAN,
    "teal":    0x008080,
    "orange":  COLOR_ORANGE,
    "dark":    COLOR_DARK,
    "black":   0x23272A,
    "white":   0xFFFFFF,
}


def parse_color(color_val: Optional[str], default: int = COLOR_BLURPLE) -> int:
    """Parses color preset names or hex strings (e.g., '#5865F2', 'gold') into an integer."""
    if not color_val:
        return default
    cleaned = color_val.strip().lower()
    if cleaned in COLOR_PRESETS:
        return COLOR_PRESETS[cleaned]
    clean_hex = cleaned.lstrip("#")
    try:
        return int(clean_hex, 16)
    except ValueError:
        return default


def success_embed(title: str, description: str = "") -> discord.Embed:
    """Returns a standardized green success embed."""
    return discord.Embed(
        title=f"✅ {title}" if not title.startswith("✅") else title,
        description=description,
        color=COLOR_GREEN,
    )


def error_embed(title: str, description: str = "") -> discord.Embed:
    """Returns a standardized red error embed."""
    return discord.Embed(
        title=f"❌ {title}" if not title.startswith("❌") else title,
        description=description,
        color=COLOR_RED,
    )


def warning_embed(title: str, description: str = "") -> discord.Embed:
    """Returns a standardized gold warning embed."""
    return discord.Embed(
        title=f"⚠️ {title}" if not title.startswith("⚠️") else title,
        description=description,
        color=COLOR_GOLD,
    )


def info_embed(title: str, description: str = "") -> discord.Embed:
    """Returns a standardized blurple informational embed."""
    return discord.Embed(
        title=title,
        description=description,
        color=COLOR_BLURPLE,
    )


def ui_embed(title: str = "", description: str = "", color: int = COLOR_BLURPLE) -> discord.Embed:
    """Returns a generic embed with custom title, description, and color."""
    return discord.Embed(title=title, description=description, color=color)


# Convenient UI aliases
ui_success = success_embed
ui_error = error_embed
ui_warning = warning_embed
ui_info = info_embed
