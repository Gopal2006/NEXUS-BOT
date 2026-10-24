-- 001_baseline.sql
-- Baseline schema reproducing existing nexus.db structure idempotently

CREATE TABLE IF NOT EXISTS guild_config (
    guild_id        INTEGER PRIMARY KEY,
    bot_role_id     INTEGER DEFAULT NULL,
    ticket_role_id  INTEGER DEFAULT NULL,
    welcome_ch      INTEGER DEFAULT NULL,
    leave_ch        INTEGER DEFAULT NULL,
    member_log_ch   INTEGER DEFAULT NULL,
    welcome_msg     TEXT    DEFAULT 'Welcome {mention} to **{guild}**! 🎉',
    leave_msg       TEXT    DEFAULT '**{name}** has left the server. Goodbye! 👋',
    log_ch          INTEGER DEFAULT NULL,
    mod_log_ch      INTEGER DEFAULT NULL,
    server_log_ch   INTEGER DEFAULT NULL,
    activity_log_ch INTEGER DEFAULT NULL,
    cmd_log_ch      INTEGER DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS non_prefix_users (
    user_id   INTEGER PRIMARY KEY,
    added_by  INTEGER NOT NULL,
    added_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS giveaways (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id          INTEGER NOT NULL,
    channel_id        INTEGER NOT NULL,
    message_id        INTEGER NOT NULL,
    host_id           INTEGER NOT NULL,
    prize             TEXT    NOT NULL,
    winners           INTEGER NOT NULL DEFAULT 1,
    ends_at           REAL    NOT NULL,
    ended             INTEGER NOT NULL DEFAULT 0,
    required_role_id  INTEGER DEFAULT NULL,
    required_role_ids TEXT    DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS giveaway_ineligible_dms (
    giveaway_id INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    notified_at REAL NOT NULL,
    PRIMARY KEY (giveaway_id, user_id)
);

CREATE TABLE IF NOT EXISTS warns (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id  INTEGER NOT NULL,
    user_id   INTEGER NOT NULL,
    mod_id    INTEGER NOT NULL,
    reason    TEXT,
    timestamp REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS tickets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    status     TEXT NOT NULL DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS mutes (
    guild_id INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    ends_at  REAL,
    PRIMARY KEY (guild_id, user_id)
);
