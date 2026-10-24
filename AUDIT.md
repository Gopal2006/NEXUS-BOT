# AUDIT.md — Nexus Bot Deep Codebase Audit

**Date:** 2026-10-23  
**Auditor:** Antigravity IDE Agent  
**Repository:** `adityabugalia063/NEXUS-BOT`  
**Framework:** Python 3.14 / Py-cord 2.8.1 (Not discord.py)

---

## 1. Executive Summary

A comprehensive line-by-line audit of `bot.py` (~1,045 lines) and all 7 existing cogs (`admin.py`, `announcements.py`, `dm.py`, `giveaway.py`, `moderation.py`, `polls.py`, `tickets.py`) was performed prior to any code modification.

The existing codebase is structurally operational with Pycord 2.8.1, but exhibits significant code duplication, hardcoded credentials/IDs, an all-or-nothing permission lock preventing public command usage, lack of persistent poll storage, and independent per-call SQLite connections that can bottleneck performance.

All existing features, slash commands, prefix commands, non-prefix execution, and custom resilient slash interaction dispatching have been mapped and will be preserved intact.

---

## 2. Inventory of Registered Commands

### 2.1 Slash Commands (`/`)

| Cog / Source | Command | Parameters | Description | Permission Tier |
|---|---|---|---|---|
| `cogs.admin` | `/set-botrole` | `role: Role` | Set staff bot-role | Server Owner / Bot Owner |
| `cogs.admin` | `/remove-botrole` | — | Remove staff bot-role restriction | Server Owner / Bot Owner |
| `cogs.admin` | `/set-welcome` | `channel: TextChannel, [message: str]` | Configure welcome channel & template | Staff |
| `cogs.admin` | `/set-leave` | `channel: TextChannel, [message: str]` | Configure farewell channel & template | Staff |
| `cogs.admin` | `/set-log` | `channel: TextChannel` | Set moderation log channel | Staff |
| `cogs.admin` | `/set-cmdlog` | `channel: TextChannel` | Set command execution log channel | Staff |
| `cogs.admin` | `/config` | — | View current server configuration | Staff |
| `cogs.admin` | `/serverstats` | — | View server & bot telemetry statistics | Staff |
| `cogs.admin` | `/setupbot` | — | Auto-create `📁 NEXUS LOGS` category & 3 channels | Staff |
| `cogs.admin` | `/set-status` | `[status, activity_type, activity_text]` | Change bot presence | Bot Owner |
| `cogs.announcements` | `/announce` | `[channel, embed, ping, image, thumbnail]` | Interactive announcement builder modal | Staff |
| `cogs.dm` | `/dm-user` | `member: Member` | Interactive single-user DM modal | Staff |
| `cogs.dm` | `/dm` | `member: Member` | Alias for `/dm-user` | Staff |
| `cogs.dm` | `/dm-role` | `role: Role` | Interactive role-broadcast DM modal | Staff |
| `cogs.giveaway` | `/giveaway start` | `[channel, role]` | Interactive giveaway creation modal | Staff |
| `cogs.giveaway` | `/giveaway end` | `message_id: str` | Force-end giveaway by message ID | Staff |
| `cogs.giveaway` | `/giveaway reroll` | `message_id: str, [winners: int]` | Reroll giveaway winner(s) | Staff |
| `cogs.giveaway` | `/giveaway list` | — | List active giveaways in the server | Staff |
| `cogs.moderation` | `/kick` | `member: Member, [reason: str]` | Kick member (mandatory reason for non-owner) | Staff |
| `cogs.moderation` | `/ban` | `member: Member, [reason: str, delete_days: int]` | Ban member & prune messages | Staff |
| `cogs.moderation` | `/unban` | `user_id: str, [reason: str]` | Unban user by ID | Staff |
| `cogs.moderation` | `/mute` | `member: Member, duration: str, [reason: str]` | Timeout member (duration parser `30s/10m/2h/1d`) | Staff |
| `cogs.moderation` | `/unmute` | `member: Member, [reason: str]` | Remove timeout | Staff |
| `cogs.moderation` | `/warn` | `member: Member, [reason: str]` | Issue warning & log to database | Staff |
| `cogs.moderation` | `/warnings` | `member: Member` | View warning history for member | Staff |
| `cogs.moderation` | `/clearwarns` | `member: Member` | Clear all warnings for member | Staff |
| `cogs.moderation` | `/purge` | `amount: int, [member: Member]` | Bulk delete messages | Staff |
| `cogs.moderation` | `/slowmode` | `seconds: int, [channel: TextChannel]` | Set channel slowmode | Staff |
| `cogs.moderation` | `/lock` | `[channel: TextChannel, reason: str]` | Lock channel for `@everyone` | Staff |
| `cogs.moderation` | `/unlock` | `[channel: TextChannel]` | Restore channel send permissions | Staff |
| `cogs.polls` | `/poll` | `[channel: TextChannel, role: Role]` | Interactive button poll modal | Staff |
| `cogs.polls` | `/endpoll` | `message_id: str` | Conclude poll and tally results | Staff |
| `cogs.tickets` | `/ticket setup` | `channel: TextChannel, [title, description, color]` | Post ticket launcher panel | Staff |
| `cogs.tickets` | `/ticket set-role` | `role: Role` | Set support staff ticket role | Staff |
| `cogs.tickets` | `/ticket close` | — | Close current ticket channel | Staff |
| `cogs.tickets` | `/ticket add` | `member: Member` | Add member to ticket channel | Staff |
| `cogs.tickets` | `/ticket remove` | `member: Member` | Remove member from ticket channel | Staff |

### 2.2 Text Prefix (`n!`, `N!`) and Non-Prefix Commands

| Cog / Source | Command Name | Aliases | Parameters | Description |
|---|---|---|---|---|
| `bot.py` | `addnp` | `npadd` | `<target>` | Grant non-prefix access (Bot Owner only) |
| `bot.py` | `removenp` | `npremove` | `<target>` | Revoke non-prefix access (Bot Owner only) |
| `bot.py` | `nplist` | `checknp` | — | List non-prefix users (Bot Owner only) |
| `bot.py` | `np` (group) | `add`, `remove`, `list` | `<target>` | Non-prefix user management |
| `bot.py` | `sync` | — | `[guild \| force]` | Slash command sync controller (Bot Owner only) |
| `bot.py` | `invite` | — | — | Official bot invite URL with slash command scopes |
| `cogs.moderation` | `kick` | — | `<member> [reason]` | Kick member (mandatory reason) |
| `cogs.moderation` | `ban` | — | `<member> [reason]` | Ban member |
| `cogs.moderation` | `purge` | — | `[amount]` | Bulk delete messages |
| `cogs.moderation` | `mute` | `timeout` | `<member> [duration] [reason]` | Timeout member |
| `cogs.moderation` | `unmute` | `untimeout` | `<member> [reason]` | Remove timeout |
| `cogs.moderation` | `warn` | — | `<member> <reason>` | Warn member |
| `cogs.moderation` | `warnings` | `warns` | `<member>` | View warning cases |
| `cogs.moderation` | `lock` | — | `[#channel] [reason]` | Lock channel |
| `cogs.moderation` | `unlock` | — | `[#channel]` | Unlock channel |
| `cogs.moderation` | `slowmode` | — | `<seconds> [#channel]` | Set slowmode delay |

---

## 3. Database Schema & Cog-by-Cog Usage

The current SQLite database is stored at `nexus.db` and accessed via `aiosqlite`.

### 3.1 Existing Tables

1. `guild_config`:
   - Columns: `guild_id` (PK), `bot_role_id`, `ticket_role_id`, `welcome_ch`, `leave_ch`, `member_log_ch`, `welcome_msg`, `leave_msg`, `log_ch`, `mod_log_ch`, `server_log_ch`, `activity_log_ch`, `cmd_log_ch`.
2. `non_prefix_users`:
   - Columns: `user_id` (PK), `added_by`, `added_at`.
3. `giveaways`:
   - Columns: `id` (PK auto), `guild_id`, `channel_id`, `message_id`, `host_id`, `prize`, `winners`, `ends_at`, `ended`, `required_role_id`, `required_role_ids`.
4. `giveaway_ineligible_dms`:
   - Columns: `giveaway_id`, `user_id`, `notified_at` (PK: `giveaway_id, user_id`).
5. `warns`:
   - Columns: `id` (PK auto), `guild_id`, `user_id`, `mod_id`, `reason`, `timestamp`.
6. `tickets`:
   - Columns: `id` (PK auto), `guild_id`, `channel_id`, `user_id`, `status`.
7. `mutes`:
   - Columns: `guild_id`, `user_id`, `ends_at` (PK: `guild_id, user_id`).

### 3.2 Database Usage per Cog

| Module / Cog | Tables Read | Tables Written | Key Operations |
|---|---|---|---|
| `bot.py` | All tables | `guild_config`, `non_prefix_users` | `init_db()`, schema migrations, `load_non_prefix_users()`, `addnp`/`removenp` |
| `cogs/admin.py` | `guild_config` | `guild_config` | Update `bot_role_id`, `welcome_ch`, `leave_ch`, `log_ch`, `cmd_log_ch`, etc. |
| `cogs/announcements.py`| `guild_config` | None | Read `bot_role_id`, `activity_log_ch`, `mod_log_ch`, `log_ch` |
| `cogs/dm.py` | `guild_config` | None | Read `bot_role_id`, `activity_log_ch` |
| `cogs/giveaway.py` | `giveaways`, `giveaway_ineligible_dms`, `guild_config` | `giveaways`, `giveaway_ineligible_dms` | Insert giveaway, update `ended=1`, insert ineligible notification record |
| `cogs/moderation.py` | `guild_config`, `warns`, `mutes` | `warns`, `mutes` | Insert warn, count warns, clear warns, insert/delete mute |
| `cogs/polls.py` | `guild_config` | None (In-Memory!) | Reads `bot_role_id`. Poll votes and state are purely in-memory (`self.votes`) |
| `cogs/tickets.py` | `tickets`, `guild_config` | `tickets`, `guild_config` | Insert ticket (`status='open'`), update ticket (`status='closed'`), set `ticket_role_id` |

---

## 4. Discrepancies Between Upgrade Spec & Real Code

1. **Hardcoded Owner ID Spread Across Multiple Files:**
   - The spec identified `GLOBAL_OWNER_ID = 1201050377911554061` in `bot.py`.
   - **Audit finding:** The exact same hardcoded variable is duplicated inside `cogs/admin.py`, `cogs/announcements.py`, `cogs/dm.py`, `cogs/giveaway.py`, `cogs/moderation.py`, `cogs/polls.py`, and `cogs/tickets.py`. All must be replaced by centralized `core/config.py` checking `OWNER_IDS`.
2. **Hardcoded Fallback Client ID:**
   - Lines 811 and 841 of `bot.py` contain `"1560655249276936192"`. Will be replaced by dynamic `bot.user.id`.
3. **Poll Persistence Missing in Existing Code:**
   - In `cogs/polls.py`, votes are stored in a python dict (`self.votes`). On bot restart, button callbacks lose their state and votes are cleared. A new `polls` table will be introduced to persist votes across restarts.
4. **Duplicate DB Access Helpers:**
   - `get_config()` and `set_config()` are re-defined in almost every cog with separate database connections instead of utilizing a shared connection or repository pattern.
5. **Onboarding Message Mismatch:**
   - In `bot.py` (`on_guild_join`), the message refers to `/setup-logs` (which does not exist; the command is `/setupbot`) and `/help` (missing cog).
6. **Ticket Support Role Permission Check:**
   - In `cogs/tickets.py`, `can_close_ticket` and `is_bot_admin` check `ticket_role_id` as well as `bot_role_id`. This nuance must be preserved in the permission system.

---

## 5. Potential Risks & Mitigation Strategy

1. **Event Loop State for Persistent Views:**
   - Pycord 2.8+ requires views added with `timeout=None` to have a running event loop when `bot.add_view()` is called. In `main.py`, views must be registered either inside an async startup hook or after the event loop starts.
2. **FastAPI & Uvicorn Co-existence:**
   - Uvicorn must be started using `uvicorn.Server(config).serve()` inside an `asyncio.create_task` or unified `asyncio.gather` on the same asyncio event loop as `bot.start()`.
3. **Single Port Cloud Deployments (e.g., Render):**
   - Render exposes only one `$PORT`. When `API_ENABLED=true`, FastAPI must handle both `/health` and `/api/v1` on `$PORT`. The legacy aiohttp server should be disabled to prevent port collisions.
4. **SQLite Concurrency with Web Dashboard:**
   - Concurrent writes from Discord commands and Dashboard API endpoints can trigger `sqlite3.OperationalError: database is locked`. We will enable WAL mode (`PRAGMA journal_mode=WAL`) and use a serialized async lock / repository pattern.
5. **Preserving Resilient Slash Interaction Dispatcher:**
   - `NexusBot.process_application_commands` solves Pycord's 429 rate-limiting interaction loss. This method in `bot.py` is battle-tested and will be cleanly moved to `core/bot.py`.
