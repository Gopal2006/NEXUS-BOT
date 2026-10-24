"""
Pydantic v2 models for API request validation and structured responses.
"""

from typing import Optional, Any, Union
from pydantic import BaseModel, Field


class GuildConfigUpdate(BaseModel):
    bot_role_id: Optional[Union[int, str]] = None
    ticket_role_id: Optional[Union[int, str]] = None
    welcome_ch: Optional[Union[int, str]] = None
    leave_ch: Optional[Union[int, str]] = None
    welcome_msg: Optional[str] = None
    leave_msg: Optional[str] = None
    log_ch: Optional[Union[int, str]] = None
    mod_log_ch: Optional[Union[int, str]] = None
    server_log_ch: Optional[Union[int, str]] = None
    activity_log_ch: Optional[Union[int, str]] = None
    cmd_log_ch: Optional[Union[int, str]] = None


class AntinukeUpdate(BaseModel):
    enabled: Optional[int] = Field(None, ge=0, le=1)
    punishment: Optional[str] = Field(None, pattern="^(ban|kick|strip_roles)$")
    ban_limit: Optional[int] = Field(None, ge=1, le=100)
    kick_limit: Optional[int] = Field(None, ge=1, le=100)
    channel_limit: Optional[int] = Field(None, ge=1, le=100)
    role_limit: Optional[int] = Field(None, ge=1, le=100)
    webhook_limit: Optional[int] = Field(None, ge=1, le=100)
    bot_add_limit: Optional[int] = Field(None, ge=1, le=100)
    window_seconds: Optional[int] = Field(None, ge=5, le=3600)
    anti_dangerous_roles: Optional[int] = Field(None, ge=0, le=1)


class LockdownRequest(BaseModel):
    scope: str = Field("all", pattern="^(all|current)$")
    reason: str = "Emergency lockdown triggered via Dashboard"


class WhitelistCreateRequest(BaseModel):
    target_id: Union[int, str]
    target_type: str = Field(..., pattern="^(user|role)$")
    module: str = Field("all", pattern="^(all|antinuke|automod)$")


class AutomodUpdate(BaseModel):
    enabled: Optional[int] = Field(None, ge=0, le=1)
    action: Optional[str] = Field(None, pattern="^(delete|warn|timeout)$")
    timeout_duration: Optional[int] = Field(None, ge=10, le=86400)
    anti_spam: Optional[int] = Field(None, ge=0, le=1)
    spam_threshold: Optional[int] = Field(None, ge=1, le=100)
    anti_caps: Optional[int] = Field(None, ge=0, le=1)
    caps_percentage: Optional[int] = Field(None, ge=10, le=100)
    anti_links: Optional[int] = Field(None, ge=0, le=1)
    anti_invites: Optional[int] = Field(None, ge=0, le=1)
    anti_mass_mentions: Optional[int] = Field(None, ge=0, le=1)
    mention_limit: Optional[int] = Field(None, ge=1, le=100)
    anti_emoji_spam: Optional[int] = Field(None, ge=0, le=1)
    emoji_limit: Optional[int] = Field(None, ge=1, le=100)
    banned_words: Optional[str] = None


class AutoroleUpdate(BaseModel):
    human_role_id: Optional[Union[int, str]] = None
    bot_role_id: Optional[Union[int, str]] = None


class LevelingUpdate(BaseModel):
    enabled: Optional[int] = Field(None, ge=0, le=1)
    min_xp: Optional[int] = Field(None, ge=1, le=100)
    max_xp: Optional[int] = Field(None, ge=1, le=500)
    cooldown_seconds: Optional[int] = Field(None, ge=5, le=3600)
    channel_id: Optional[Union[int, str]] = None
    levelup_message: Optional[str] = None
    role_rewards: Optional[dict[str, Union[int, str]]] = None


class AutoresponderCreateRequest(BaseModel):
    trigger: str = Field(..., min_length=1, max_length=100)
    response: str = Field(..., min_length=1, max_length=2000)
    match_type: str = Field("exact", pattern="^(exact|contains)$")


class BirthdaySettingsUpdate(BaseModel):
    channel_id: Optional[Union[int, str]] = None
    role_id: Optional[Union[int, str]] = None
    message: Optional[str] = None


class AuditLogRecord(BaseModel):
    action: str
    details: Optional[str] = None


class BotRoleUpdateRequest(BaseModel):
    role_id: Optional[Union[int, str]] = None


class TicketRoleUpdateRequest(BaseModel):
    role_id: Optional[Union[int, str]] = None


class WelcomeSettingsUpdate(BaseModel):
    welcome_ch: Optional[Union[int, str]] = None
    leave_ch: Optional[Union[int, str]] = None
    welcome_msg: Optional[str] = None
    leave_msg: Optional[str] = None
    dm_enabled: Optional[int] = Field(None, ge=0, le=1)
    dm_message: Optional[str] = None
    role_id: Optional[Union[int, str]] = None
    welcome_image_url: Optional[str] = Field(None, max_length=500)
    leave_image_url: Optional[str] = Field(None, max_length=500)
    welcome_color: Optional[str] = Field("#5865F2", max_length=50)
    welcome_format: Optional[str] = Field("embed", pattern="^(embed|text)$")
    leave_format: Optional[str] = Field("embed", pattern="^(embed|text)$")


class AnnouncementCreateRequest(BaseModel):
    channel_id: Union[int, str]
    as_embed: bool = True
    title: Optional[str] = Field(None, max_length=256)
    content: Optional[str] = Field("", max_length=4000)
    color: Optional[str] = Field(None, max_length=50)
    banner_url: Optional[str] = Field(None, max_length=25000000)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    ping: Optional[str] = Field(None, max_length=50)
    button_label: Optional[str] = Field(None, max_length=80)
    button_url: Optional[str] = Field(None, max_length=500)


class DirectMessageRequest(BaseModel):
    target_type: str = Field(..., pattern="^(user|role)$")
    target_id: Union[int, str]
    title: Optional[str] = Field(None, max_length=256)
    content: str = Field(..., min_length=1, max_length=4000)
    color: Optional[str] = Field(None, max_length=50)
    banner_url: Optional[str] = Field(None, max_length=500)
    button_label: Optional[str] = Field(None, max_length=80)
    button_url: Optional[str] = Field(None, max_length=500)


class PollCreateRequest(BaseModel):
    channel_id: Union[int, str]
    question: str = Field(..., min_length=1, max_length=256)
    options: list[str] = Field(..., min_length=2, max_length=10)
    duration_minutes: Optional[int] = Field(60, ge=1, le=10080)
    role_id: Optional[Union[int, str]] = None


class GiveawayCreateRequest(BaseModel):
    channel_id: Union[int, str]
    prize: str = Field(..., min_length=1, max_length=256)
    duration_minutes: int = Field(60, ge=1, le=10080)
    winners: int = Field(1, ge=1, le=20)
    required_role_id: Optional[Union[int, str]] = None


class TicketSetupRequest(BaseModel):
    channel_id: Union[int, str]
    title: Optional[str] = "📩 Support Ticket Panel"
    description: Optional[str] = "Click the button below to open a private ticket with our staff team."
    button_label: Optional[str] = "Create Ticket"


class ModerationActionRequest(BaseModel):
    action: str = Field(..., pattern="^(kick|ban|mute|warn|lock|unlock)$")
    target_id: Union[int, str]
    reason: str = Field("Action executed via Web Dashboard", min_length=1, max_length=512)
    duration_minutes: Optional[int] = Field(None, ge=1, le=43200)
