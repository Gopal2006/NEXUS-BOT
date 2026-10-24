-- 006_dashboard.sql
-- Dashboard audit log table to record configuration edits made via the web dashboard

CREATE TABLE IF NOT EXISTS dashboard_audit (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    action      TEXT NOT NULL,
    details     TEXT,
    timestamp   REAL NOT NULL
);
