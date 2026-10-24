-- 003_security.sql
-- Antinuke, Whitelist, and Automod tables

CREATE TABLE IF NOT EXISTS antinuke_settings (
    guild_id              INTEGER PRIMARY KEY,
    enabled               INTEGER DEFAULT 0,
    punishment            TEXT DEFAULT 'ban',
    ban_limit             INTEGER DEFAULT 3,
    kick_limit            INTEGER DEFAULT 3,
    channel_limit         INTEGER DEFAULT 3,
    role_limit            INTEGER DEFAULT 3,
    webhook_limit         INTEGER DEFAULT 3,
    bot_add_limit         INTEGER DEFAULT 1,
    prune_limit           INTEGER DEFAULT 1,
    window_seconds        INTEGER DEFAULT 60,
    anti_dangerous_roles  INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS whitelist (
    guild_id              INTEGER NOT NULL,
    target_id             INTEGER NOT NULL,
    target_type           TEXT NOT NULL, -- 'user' or 'role'
    module                TEXT NOT NULL DEFAULT 'all', -- 'all', 'antinuke', 'automod'
    added_by              INTEGER,
    added_at              REAL,
    PRIMARY KEY (guild_id, target_id, module)
);

CREATE TABLE IF NOT EXISTS automod_settings (
    guild_id               INTEGER PRIMARY KEY,
    enabled                INTEGER DEFAULT 0,
    anti_spam              INTEGER DEFAULT 1,
    spam_threshold         INTEGER DEFAULT 5,
    spam_window            INTEGER DEFAULT 5,
    anti_caps              INTEGER DEFAULT 0,
    caps_percentage        INTEGER DEFAULT 70,
    caps_min_length        INTEGER DEFAULT 10,
    anti_links             INTEGER DEFAULT 0,
    anti_invites           INTEGER DEFAULT 1,
    anti_mass_mentions     INTEGER DEFAULT 1,
    mention_limit          INTEGER DEFAULT 5,
    anti_emoji_spam        INTEGER DEFAULT 0,
    emoji_limit            INTEGER DEFAULT 6,
    banned_words           TEXT DEFAULT '',
    action                 TEXT DEFAULT 'delete', -- 'delete', 'warn', 'timeout'
    timeout_duration       INTEGER DEFAULT 300,
    ignored_channels       TEXT DEFAULT '',
    ignored_roles          TEXT DEFAULT ''
);
