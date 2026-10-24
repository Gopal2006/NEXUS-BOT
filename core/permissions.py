"""
Tiered permission system for Nexus Bot.
Enforces role isolation across Public, Staff, Guild Owner, and Bot Owner tiers.
"""

from typing import Union, Optional
import discord
from discord.ext import commands

from core.config import is_bot_owner
from db.database import get_config

ContextType = Union[commands.Context, discord.ApplicationContext, discord.Interaction]


async def has_tier_permission(ctx: ContextType, tier: str = "staff") -> bool:
    """
    Evaluates whether the command invoker meets the specified tier requirement:
      - 'public': Accessible by all guild members.
      - 'staff': Bot owner, non-prefix user, guild owner, or holder of configured bot-role/ticket-role.
                 (Administrators without the bot role are explicitly blocked).
      - 'owner': Guild owner or Bot owner.
      - 'bot_owner': Listed in OWNER_IDS only.
    """
    if tier == "public":
        return True

    # Resolve author/user object
    author = getattr(ctx, "author", None)
    if author is None and hasattr(ctx, "user"):
        author = ctx.user
    if author is None:
        return False

    user_id = author.id

    # Bot owners always satisfy all permission tiers
    if is_bot_owner(user_id):
        return True

    if tier == "bot_owner":
        return False

    # Guild-level checks require a guild context
    guild = getattr(ctx, "guild", None)
    if guild is None:
        return False

    # Server owner satisfies 'owner' and 'staff' tiers
    if user_id == guild.owner_id:
        return True

    if tier == "owner":
        return False

    # Tier: 'staff'
    if tier == "staff":
        # Check if user is an authorized non-prefix user
        bot = getattr(ctx, "bot", None)
        if bot and hasattr(bot, "non_prefix_users") and user_id in bot.non_prefix_users:
            return True

        # Fetch guild configuration
        cfg = await get_config(guild.id)
        bot_role_id = cfg.get("bot_role_id")
        ticket_role_id = cfg.get("ticket_role_id")

        member = guild.get_member(user_id) or author
        if hasattr(member, "roles"):
            role_ids = {r.id for r in member.roles}
            if bot_role_id and bot_role_id in role_ids:
                return True
            if ticket_role_id and ticket_role_id in role_ids:
                return True

        return False

    return False


async def send_no_permission(ctx: ContextType):
    """Sends the standard friendly 'Access Denied: Bot-Role Required' response."""
    guild = getattr(ctx, "guild", None)
    if guild is None:
        embed = discord.Embed(
            title="🔒 Access Denied",
            description="Commands can only be used inside a server.",
            color=0xED4245,
        )
        if hasattr(ctx, "respond"):
            if getattr(ctx, "response", None) and ctx.response.is_done():
                return await ctx.followup.send(embed=embed, ephemeral=True)
            return await ctx.respond(embed=embed, ephemeral=True)
        return await ctx.reply(embed=embed)

    cfg = await get_config(guild.id)
    role_id = cfg.get("bot_role_id")
    bot_role = guild.get_role(role_id) if role_id else None

    if bot_role:
        tip = (
            f"You need the **{bot_role.name}** role to use bot commands.\n"
            "Please ask the **server owner** to grant you this role."
        )
    else:
        tip = (
            "You don't have permission to use bot commands.\n"
            "Please ask the **server owner** to assign a bot-role using `/set-botrole`."
        )

    embed = discord.Embed(
        title="🔒 Access Denied",
        description=tip,
        color=0xED4245,
    )

    if hasattr(ctx, "respond"):
        if getattr(ctx, "response", None) and ctx.response.is_done():
            return await ctx.followup.send(embed=embed, ephemeral=True)
        return await ctx.respond(embed=embed, ephemeral=True)
    return await ctx.reply(embed=embed)


def requires_tier(tier: str = "staff"):
    """Command check decorator that verifies permission tier."""
    async def predicate(ctx: ContextType) -> bool:
        allowed = await has_tier_permission(ctx, tier=tier)
        if not allowed:
            raise commands.CheckFailure(f"User lacks required tier '{tier}' permission.")
        return True
    return commands.check(predicate)
