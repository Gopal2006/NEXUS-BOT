-- 004_management.sql
-- Management tables: autorole, reaction_roles, jtc, invites, verification, welcome_settings, and persistent polls

CREATE TABLE IF NOT EXISTS autorole_settings (
    guild_id        INTEGER PRIMARY KEY,
    human_role_id   INTEGER,
    bot_role_id     INTEGER
);

CREATE TABLE IF NOT EXISTS reaction_roles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id        INTEGER NOT NULL,
    channel_id      INTEGER NOT NULL,
    message_id      INTEGER NOT NULL,
    role_id         INTEGER NOT NULL,
    emoji           TEXT,
    label           TEXT,
    style           TEXT DEFAULT 'primary',
    UNIQUE (message_id, role_id)
);

CREATE TABLE IF NOT EXISTS verification_settings (
    guild_id        INTEGER PRIMARY KEY,
    role_id         INTEGER NOT NULL,
    channel_id      INTEGER,
    message_id      INTEGER
);

CREATE TABLE IF NOT EXISTS jtc_settings (
    guild_id        INTEGER PRIMARY KEY,
    channel_id      INTEGER NOT NULL,
    category_id     INTEGER,
    user_limit      INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS jtc_channels (
    channel_id      INTEGER PRIMARY KEY,
    guild_id        INTEGER NOT NULL,
    owner_id        INTEGER NOT NULL,
    created_at      REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS invites (
    guild_id        INTEGER NOT NULL,
    code            TEXT NOT NULL,
    inviter_id      INTEGER,
    uses            INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, code)
);

CREATE TABLE IF NOT EXISTS welcome_settings (
    guild_id        INTEGER PRIMARY KEY,
    dm_enabled      INTEGER DEFAULT 0,
    dm_message      TEXT,
    role_id         INTEGER
);

CREATE TABLE IF NOT EXISTS polls (
    message_id      INTEGER PRIMARY KEY,
    channel_id      INTEGER NOT NULL,
    guild_id        INTEGER NOT NULL,
    question        TEXT NOT NULL,
    options_json    TEXT NOT NULL,
    votes_json      TEXT NOT NULL,
    allowed_role_id INTEGER,
    created_at      REAL NOT NULL,
    ended           INTEGER DEFAULT 0
);
