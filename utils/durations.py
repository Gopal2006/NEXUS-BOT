"""
Duration parsing and formatting utilities.
Supports combinations like '30s', '10m', '2h', '1d', '1d12h', '3d4h30m'.
"""

import re

# Regex for finding sequence of numbers followed by d/h/m/s
TIME_REGEX = re.compile(r"(\d+)\s*([dhms])", re.IGNORECASE)

UNIT_MULTIPLIERS = {
    "d": 86400,
    "h": 3600,
    "m": 60,
    "s": 1,
}


def parse_duration(duration_str: str) -> int:
    """
    Parses a duration string into total seconds.
    Examples:
      '30s' -> 30
      '10m' -> 600
      '2h' -> 7200
      '1d' -> 86400
      '1d12h' -> 129600
      '2h30m' -> 9000
    Returns 0 if no valid units found.
    """
    if not duration_str:
        return 0

    s = duration_str.strip().lower()

    # Direct match with regex
    matches = TIME_REGEX.findall(s)
    if matches:
        total = 0
        for val_str, unit in matches:
            total += int(val_str) * UNIT_MULTIPLIERS.get(unit, 0)
        return total

    # Fallback character-by-character parser (original bot method)
    total = 0
    buf = ""
    for c in s:
        if c.isdigit():
            buf += c
        elif c in "dhms" and buf:
            total += int(buf) * UNIT_MULTIPLIERS.get(c, 0)
            buf = ""
    return total


def format_duration(seconds: float) -> str:
    """Formats a number of seconds into a human-readable duration string."""
    secs = int(max(0, seconds))
    if secs == 0:
        return "0s"

    days, r = divmod(secs, 86400)
    hours, r = divmod(r, 3600)
    minutes, s = divmod(r, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if s or not parts:
        parts.append(f"{s}s")

    return " ".join(parts)
