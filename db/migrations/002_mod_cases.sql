-- 002_mod_cases.sql
-- Additive migration for moderation case numbers and jail system

CREATE TABLE IF NOT EXISTS mod_cases (
    case_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id         INTEGER NOT NULL,
    action           TEXT NOT NULL,
    user_id          INTEGER NOT NULL,
    user_name        TEXT NOT NULL,
    mod_id           INTEGER NOT NULL,
    mod_name         TEXT NOT NULL,
    reason           TEXT,
    duration_seconds INTEGER DEFAULT NULL,
    timestamp        REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS jail_records (
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    role_ids   TEXT NOT NULL,
    jailed_at  REAL NOT NULL,
    jailed_by  INTEGER NOT NULL,
    reason     TEXT,
    PRIMARY KEY (guild_id, user_id)
);
