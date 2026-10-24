-- 005_engagement.sql
-- Engagement tables: leveling, birthdays, afk, autoresponder, sticky messages, counting

CREATE TABLE IF NOT EXISTS levels (
    guild_id        INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    xp              INTEGER DEFAULT 0,
    level           INTEGER DEFAULT 0,
    last_xp         REAL DEFAULT 0,
    messages        INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS level_settings (
    guild_id            INTEGER PRIMARY KEY,
    enabled             INTEGER DEFAULT 1,
    min_xp              INTEGER DEFAULT 15,
    max_xp              INTEGER DEFAULT 25,
    cooldown_seconds    INTEGER DEFAULT 60,
    channel_id          INTEGER,
    levelup_message     TEXT DEFAULT 'Congratulations {user}! You leveled up to **Level {level}**! 🎉',
    role_rewards_json   TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS birthdays (
    guild_id        INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    month           INTEGER NOT NULL,
    day             INTEGER NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS birthday_settings (
    guild_id        INTEGER PRIMARY KEY,
    channel_id      INTEGER,
    role_id         INTEGER,
    message         TEXT DEFAULT '🎉 Happy Birthday {user}! 🎂 Hope you have an amazing day!'
);

CREATE TABLE IF NOT EXISTS afk (
    guild_id        INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    reason          TEXT DEFAULT 'AFK',
    timestamp       REAL NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS autoresponders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id        INTEGER NOT NULL,
    trigger         TEXT NOT NULL,
    response        TEXT NOT NULL,
    match_type      TEXT DEFAULT 'exact', -- 'exact', 'contains', 'wildcard'
    UNIQUE (guild_id, trigger)
);

CREATE TABLE IF NOT EXISTS sticky_messages (
    channel_id      INTEGER PRIMARY KEY,
    guild_id        INTEGER NOT NULL,
    message         TEXT NOT NULL,
    last_message_id INTEGER
);

CREATE TABLE IF NOT EXISTS counting (
    channel_id      INTEGER PRIMARY KEY,
    guild_id        INTEGER NOT NULL,
    current_number  INTEGER DEFAULT 0,
    last_user_id    INTEGER
);
