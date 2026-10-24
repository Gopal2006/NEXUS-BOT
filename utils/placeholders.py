"""
Safe placeholder string replacement utility.
Replaces placeholders like {mention}, {name}, {guild} without eval,
arbitrary attribute access, or KeyError exceptions.
"""

import re
from typing import Any

# Matches {identifier} patterns
PLACEHOLDER_REGEX = re.compile(r"\{([a-zA-Z0-9_]+)\}")


def safe_format(template: str, **kwargs: Any) -> str:
    """
    Safely substitutes {key} placeholders in a user-provided string template.
    If a placeholder is not present in kwargs, it is left unchanged or substituted
    with an empty string if malformed. Never raises KeyError or allows attribute traversal.
    """
    if not template:
        return ""

    def replacer(match: re.Match) -> str:
        key = match.group(1)
        if key in kwargs:
            val = kwargs[key]
            return str(val) if val is not None else ""
        return match.group(0)  # Keep original {key} if unknown

    try:
        return PLACEHOLDER_REGEX.sub(replacer, template)
    except Exception:
        return template
