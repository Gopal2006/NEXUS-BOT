# NEXUS Bot: verified product audit

Audit date: 2026-10-25. This document records what is implemented in the checked-out source. A feature mentioned only in older prose but not corroborated by implementation is marked as documentation-only or not found. File paths are repository-relative.

## 1. Identity, stack, and brand

| Fact | Verified finding | Evidence |
|---|---|---|
| Name | Configurable `BRAND_NAME`, default “Nexus”; repository/product docs use “Nexus Bot” / “NEXUS”. | `core/config.py`, `README.md` |
| Description | Bot instance describes itself as “Nexus — All-Purpose Discord Bot”. | `core/bot.py` |
| Version | FastAPI application reports version `2.0.0`; Next.js package reports `2.0.0`. No bot package version field found. | `api/app.py`, `dashboard/package.json` |
| Language / library | Python 3; Pycord (requirements specify `py-cord>=2.6.0`; decisions document 2.8+). Frontend uses Next.js App Router, React, TypeScript. | `requirements.txt`, `DECISIONS.md`, `dashboard/package.json` |
| Database | SQLite via aiosqlite, with numbered SQL migrations. | `db/database.py`, `db/migrations/*.sql` |
| Existing visual identity | Discord embed palette includes blurple `#5865F2`, green `#57F287`, red `#ED4245`, gold `#FEE75C`, plus other colors. Bot responses use emoji and concise Discord embed styling. | `core/ui.py`, `core/events.py`, `cogs/*.py` |
| Logo/avatar/artwork | No logo, favicon, or image asset found in the repository search. Bot avatar is fetched from Discord at runtime where used; a checked-in brand mark is not found. | Repository asset search; `cogs/utility.py` |
| Tone | Friendly and operational, with short setup steps, emoji, and direct permission/security messages. | `core/events.py`, `core/permissions.py`, `cogs/help.py` |

## 2. Commands

The tables below inventory the declared slash and prefix commands and groups in active cogs, with the documented permission tier and the concrete argument names visible in source. Slash option requiredness/defaults are reflected where clear from function signatures and option decorators; command-specific cooldown decorators were not found. Where a slash/prefix spelling differs, both are listed. The app has no user/message context-menu command declaration found.

Tier key: **public** = any server member; **staff** = server owner, configured Bot-Role holders, bot owners, and the non-prefix allowlist as checked in the permission helper; **owner** = guild owner or bot owner; **bot_owner** = configured global bot owner. Some commands perform additional checks described below. Evidence for each group is shown in its table.

### Admin and setup — `cogs/admin.py`

| Command | Options / arguments | Tier | What it does |
|---|---|---|---|
| `/set-botrole` | required role | owner | Assigns the role that grants staff-level Nexus management. |
| `/remove-botrole` | none | owner | Removes the configured Bot-Role. |
| `/set-ticketrole` | required role | owner | Sets the ticket support role. |
| `/remove-ticketrole` | none | owner | Removes the ticket support role. |
| `/set-welcome` | required channel; optional message | staff | Sets a welcome channel/template. |
| `/set-leave` | required channel; optional message | staff | Sets a member-departure channel/template. |
| `/set-log` | required channel | staff | Sets the moderation log channel. |
| `/set-cmdlog` | required channel | staff | Sets the prefix/no-prefix command audit channel. |
| `/config` | none | staff | Displays configured server roles and channels. |
| `/setupbot` | none | staff | Creates a private NEXUS LOGS category and four log channels, then saves their IDs. |
| `/set-status` | status, activity type, activity text | staff | Changes bot presence/activity. |

### Moderation and channel control — `cogs/moderation.py`

| Command | Options / arguments | Tier | What it does |
|---|---|---|---|
| `/kick`, `n!kick` | member; slash reason required (prefix reason is accepted after member) | staff | Kicks a member and records a moderation case. |
| `/ban`, `n!ban` | member, reason; slash optional delete-days | staff | Bans a member; slash option can delete recent message history; records a case. |
| `/softban`, `n!softban` | member, reason | staff | Bans then immediately unbans to remove recent messages; records a case. |
| `/unban`, `n!unban` | user ID; optional reason | staff | Removes a user ban. |
| `/mute`, `n!mute` (alias `timeout`) | member, duration, optional reason | staff | Times a member out; timeout expiration is persisted and restored by the bot. |
| `/unmute`, `n!unmute` (alias `untimeout`) | member; optional reason | staff | Removes a member timeout. |
| `/warn`, `n!warn` | member, reason | staff | Stores a warning and reports it to the user. |
| `/warnings`, `n!warnings` (aliases `warns`, `modlogs`) | member | staff | Displays stored warning history. |
| `/clearwarns` | member | staff | Deletes stored warnings for a member. Prefix counterpart not found. |
| `/modlogs` | member | staff | Displays moderation case history. Prefix spelling is an alias of `n!warnings`. |
| `/lockdown`, `n!lockdown` | optional scope/reason | owner | Applies a server-wide or scoped messaging lockdown. |
| `/unlockdown`, `n!unlockdown` | optional scope | owner | Lifts the lockdown. |
| `/hide`, `n!hide` | optional channel | staff | Hides a channel from @everyone. |
| `/unhide`, `n!unhide` | optional channel | staff | Restores @everyone channel visibility. |
| `/nick`, `n!nick` (prefix alias `nickname`) | member; optional nickname | staff | Changes or clears a nickname. |
| `/role add`, `n!role add` | member, role | staff | Assigns a role, subject to role hierarchy. |
| `/role remove`, `n!role remove` | member, role | staff | Removes a role, subject to role hierarchy. |
| `/purge`, `n!purge` | amount; slash optional member filter | staff | Deletes recent messages in the current channel. |
| `/slowmode`, `n!slowmode` | seconds; optional channel | staff | Sets channel message cooldown. |
| `/lock`, `n!lock` | optional channel/reason | staff | Disables @everyone message sending in a channel. |
| `/unlock`, `n!unlock` | optional channel | staff | Restores channel sending permissions. |

### Member management — `cogs/autorole.py`, `cogs/reaction_roles.py`

| Command | Options / arguments | Tier | What it does |
|---|---|---|---|
| `/autorole set-human` | role | staff | Sets a role to assign automatically to new human members. |
| `/autorole view` | none | staff | Shows autorole configuration. |
| `/autorole clear` | none | staff | Clears autorole configuration. |
| `n!autorole` | none | staff | Prefix group entry/help for autorole. |
| `n!autorole set` | role | staff | Prefix autorole setup. |
| `n!autorole clear` | none | staff | Clears prefix autorole setup. |
| `/reactionrole panel` | title, description, up to five role slots, channel | staff | Creates a button panel through which members can self-assign configured roles. |
| `n!reactionrole` (alias `rr`) | role; optional label | staff | Prefix reaction-role helper. |

### Engagement and social — `cogs/leveling.py`, `cogs/afk.py`, `cogs/autoresponder.py`

| Command | Options / arguments | Tier | What it does |
|---|---|---|---|
| `/rank`, `n!rank` | optional member | public | Shows a member’s level, XP, and progress. |
| `/leaderboard`, `n!leaderboard` (prefix aliases `lb`, `top`) | optional page | public | Shows the server XP leaderboard. |
| `/leveling toggle` | status | staff | Enables or disables XP tracking. |
| `/leveling reward` | action, level, role | staff | Adds or removes a milestone role reward. |
| `/leveling settings` | none | staff | Displays leveling configuration. |
| `/afk`, `n!afk` | optional reason (default “AFK”) | public | Sets AFK status. |
| `/autoresponder add` | trigger, response, match type | staff | Adds an exact/contains/wildcard trigger response (actual supported values should be taken from the option declaration). |
| `/autoresponder remove` | trigger | staff | Removes an autoresponder. |
| `/autoresponder list` | none | staff | Lists autoresponders. |
| `n!autoresponder` (alias `ar`) | none | staff | Prefix group entry/help. |
| `n!autoresponder add` | free-text content | staff | Adds a prefix autoresponder. |
| `n!autoresponder remove` (aliases `del`, `rm`) | trigger | staff | Removes a prefix autoresponder. |

### Games — `cogs/games.py`

| Command | Options / arguments | Tier | What it does |
|---|---|---|---|
| `/tictactoe`, `n!tictactoe` (prefix alias `ttt`) | required opponent | public | Starts a turn-based 3×3 game with button interaction. |
| `/rps`, `n!rps` | optional opponent | public | Plays Rock-Paper-Scissors against the bot or another member. |
| `/guess`, `n!guess` (prefix alias `numberguess`) | none | public | Starts a number-guessing game from 1 to 100. |

### Giveaways — `cogs/giveaway.py`

Slash commands are in the `/giveaway` group. Each listed action also uses the group’s staff permission check.

| Command | Options / arguments | Tier | What it does |
|---|---|---|---|
| `/giveaway start` | channel; optional role; modal collects giveaway details | staff | Starts a giveaway with persistent entry state and optional role eligibility. |
| `/giveaway end` | message ID | staff | Ends an active giveaway. |
| `/giveaway reroll` | message ID, winner count | staff | Selects replacement winner(s). |
| `/giveaway list` | none | staff | Lists active giveaways in this server. |

### Polls — `cogs/polls.py`

| Command | Options / arguments | Tier | What it does |
|---|---|---|---|
| `/poll` | optional channel and role; modal collects question/options | staff | Creates a button poll with optional role restriction. |
| `/endpoll` | message ID | staff | Closes a poll and reports results. |

### Tickets — `cogs/tickets.py`

| Command | Options / arguments | Tier | What it does |
|---|---|---|---|
| `/ticket setup` | channel; optional title, description, color | staff | Posts an interactive ticket-opening panel. |
| `/ticket set-role` | role | guild owner only in implementation | Sets the support-staff role. |
| `/ticket remove-role` | none | guild owner only in implementation | Removes the support-staff role. |
| `/ticket close` | none | staff (Bot-Role or Ticket-Role), server owner, or bot owner | Closes an active ticket and produces a transcript. |
| `/ticket add` | member | ticket staff / applicable permission checks | Grants a member access to the current ticket. |
| `/ticket remove` | member | ticket staff / applicable permission checks | Removes a member’s access to the current ticket. |
| `n!ticket` | none | staff-gated group | Prefix group entry/help. |
| `n!ticket close` | none | staff (Bot-Role or Ticket-Role), server owner, or bot owner | Prefix ticket closure. |
| `n!ticket add` | member | implementation check | Adds member to ticket. |
| `n!ticket remove` | member | implementation check | Removes member from ticket. |

### Announcements and direct messages — `cogs/announcements.py`, `cogs/dm.py`

| Command | Options / arguments | Tier | What it does |
|---|---|---|---|
| `/announce` | channel; optional embed/ping/image/thumbnail options; interactive modal | staff | Composes and publishes a text or embed announcement. |
| `/dm-user`, `/dm` | member; modal collects content | staff | Sends a direct message to one member and logs delivery outcome. |
| `/dm-role` | role; modal collects content | staff | Sends a direct message to members with a role, with progress/rate handling. |

### Utility — `cogs/help.py`, `cogs/utility.py`

| Command | Options / arguments | Tier | What it does |
|---|---|---|---|
| `/help`, `n!help` | optional category | staff | Shows categorized feature/command guidance. |
| `/ping`, `n!ping` | none | bot_owner | Reports gateway and API response latency. |
| `/uptime`, `n!uptime` | none | bot_owner | Reports time since the process started. |
| `/stats`, `n!stats` (prefix aliases `botinfo`, `about`) | none | bot_owner | Reports process/bot runtime metrics. |
| `/userinfo`, `n!userinfo` (prefix aliases `whois`, `ui`) | optional member | public | Displays profile/account/server membership information. |
| `/serverinfo`, `n!serverinfo` (prefix aliases `server`, `si`) | none | public | Displays information about the current server. |

### Global bot-owner prefix commands — `core/events.py`

| Command | Arguments | Tier | What it does |
|---|---|---|---|
| `n!addnp` (alias `npadd`) | user ID | bot_owner | Adds a global non-prefix command allowlist entry. |
| `n!removenp` (alias `npremove`) | user ID | bot_owner | Removes that allowlist entry. |
| `n!nplist` (alias `checknp`) | none | bot_owner | Lists allowlisted IDs. |
| `n!np` | none | bot_owner | Prefix group entry/help. |
| `n!np add` | user ID | bot_owner | Adds an allowlist entry. |
| `n!np remove` | user ID | bot_owner | Removes an allowlist entry. |
| `n!np list` | none | bot_owner | Lists allowlisted IDs. |
| `n!sync` | optional mode (guild/force handling in source) | bot_owner | Synchronizes slash command definitions with Discord. |
| `n!invite` | none | no tier decorator found | Returns an invite link generated from the active bot ID. |

### Hero commands with source-grounded examples

These are proposed landing-page examples, not real server records. Names and response shape are based on implementations.

1. **`/setupbot`** — Run in a server after granting Nexus channel/role management rights. It creates the NEXUS LOGS category and mod, server, activity, and command-log channels, then stores their IDs. Example response: “NEXUS LOGS configured” with the four channel mentions. Evidence: `cogs/admin.py`.
2. **`/ban member:@User reason:Repeated spam`** — A staff member submits a reason; the bot checks role hierarchy, attempts a DM, applies the ban, and creates a moderation case. Example response: a confirmation with member, reason, and case reference. Evidence: `cogs/moderation.py`, `db/repos/mod_cases.py`.
3. **`/ticket setup channel:#support`** — Posts a button panel; a member opens a private ticket; staff can manage access and close it. Closing generates a transcript. Evidence: `cogs/tickets.py`.
4. **`/rank member:@Member`** — Displays the target member’s level/XP and rank progress from saved XP. Evidence: `cogs/leveling.py`.
5. **`/rps opponent:@Friend`** — Starts a two-player interaction with hidden choices until the result is resolved. Evidence: `cogs/games.py`.
6. **`/poll`** — Opens a creation modal; participants vote with buttons; optional role restrictions can limit eligible voters. Evidence: `cogs/polls.py`.
7. **`/announce channel:#news`** — Opens the announcement composer and can publish an embed with color and media options. Evidence: `cogs/announcements.py`.
8. **`/serverinfo`** — Shows server metadata available through Discord, including owner, creation date, boost level and member information. Evidence: `cogs/utility.py`.

### Cooldowns, application commands, and undocumented gaps

- No command cooldown decorator was found in the active cogs; do not claim per-command cooldowns. The XP message award has its own configurable per-user cooldown. Evidence: `cogs/*.py`, `cogs/leveling.py`.
- Slash/prefix signatures can differ; for example, not every slash action has a prefix counterpart. The table preserves that distinction. Evidence: active cog decorators.
- Prefix is `n!` for normal users. Bot owners and authorized non-prefix users also use an empty prefix. Evidence: `core/bot.py`.
- Slash command registration has resilient 429 handling and retry/sync behavior. Evidence: `core/bot.py`.
- No context-menu command (Discord user/message command) declaration was found. Evidence: active `cogs/*.py`.

## 3. Automatic behavior

| Behavior | Verified description | Evidence |
|---|---|---|
| Startup/presence/sync | Initializes SQLite migrations and cogs, sets bot presence, then syncs application command definitions. | `main.py`, `core/events.py`, `core/bot.py` |
| Guild join onboarding | Sends setup guidance and an invite re-authorization link where a sendable channel exists. | `core/events.py` |
| Welcome/leave | Sends configured templated messages on member join/leave; welcome extras can add role/DM behavior. | `core/events.py`, `db/repos/management.py`, `cogs/admin.py` |
| Autorole | Assigns configured human member role on join. | `cogs/autorole.py` |
| Audit logging | Logs configured message edit/delete, channel/role changes, voice changes, and selected member changes to configured channels. Command completion logger can include command message content. | `cogs/logging_events.py`, `core/events.py` |
| AFK | Detects mentions to AFK members and clears a member’s AFK status when they speak. | `cogs/afk.py` |
| Leveling | Tracks message activity, awards configurable XP after cooldown, persists XP/levels, and can announce level-ups/award rewards. | `cogs/leveling.py`, `db/migrations/005_engagement.sql` |
| Autoresponder | Responds to configured matching message triggers. | `cogs/autoresponder.py` |
| Giveaway | Persists running giveaways; reaction entry, completion and reroll logic are present. | `cogs/giveaway.py`, `db/migrations/001_baseline.sql` |
| Polls / reaction roles | Button interactions and poll vote state are persisted. | `cogs/polls.py`, `cogs/reaction_roles.py`, `db/migrations/004_management.sql` |
| Timeout recovery | Background task restores/expires persisted mute/timeout records. | `cogs/moderation.py`, `db/migrations/001_baseline.sql` |
| Dashboard/API | Python API serves guild, settings, security and feature routes; it can run beside the bot. | `main.py`, `api/app.py` |
| Not found as active feature | No active command/listener implementation found for birthdays, verification, sticky messages, counting, invite tracking, or join-to-create voice channels despite schema/comments for some of these. No scheduled birthday/cron runner found. | `db/migrations/004_management.sql`, `db/migrations/005_engagement.sql`, active `cogs/*.py` |

## 4. Configuration and dashboard

Per-guild settings include the Bot-Role, ticket role, welcome/leave channels and text, and several audit log channels. Other feature settings cover autoroles, leveling, reaction roles, ticket/poll/giveaway state, and autoresponders. Evidence: `db/migrations/001_baseline.sql`, `db/migrations/003_security.sql`–`006_dashboard.sql`, `cogs/admin.py`.

The Next.js dashboard uses Discord OAuth scopes `identify guilds`, presents a server picker, and restricts management to authorized servers. Its routes/pages include:

- Server picker and per-server overview.
- General/server configuration, welcome, moderation, audit log, tickets, polls, giveaways, leveling, autorole, reaction roles, announcements, direct messages, autoresponder, and admin.
- Admin has global allowlist/cluster management functions.

Evidence: `dashboard/src/app/**/page.tsx`, `dashboard/src/lib/auth.ts`, `dashboard/src/middleware.ts`, `api/routes/*.py`.

There is also a separate aiohttp control center in `web/index.html` and `web/commands.html`, served by `run_dashboard.py` / `dashboard_server.py`; it is distinct from the Next.js dashboard. Language/localization support beyond English is not found. Server-defined custom embeds are supported for announcement/ticket/DM flows; general custom commands and configurable command prefixes are not found (the prefix is fixed to `n!` plus authorized no-prefix users). Themes are not a bot configuration setting.

## 5. Integrations

- Discord Gateway, interactions, embeds, and REST through Pycord; Discord OAuth2 for the Next.js dashboard. Evidence: `requirements.txt`, `core/bot.py`, `dashboard/src/lib/auth.ts`.
- FastAPI/Uvicorn JSON API for the dashboard and aiohttp server for the standalone control center. Evidence: `api/app.py`, `dashboard_server.py`, `run_dashboard.py`.
- SQLite local storage. Evidence: `db/database.py`, `db/migrations/*.sql`.
- Announcement image/media handling uses aiohttp to retrieve remote image content. Evidence: `cogs/announcements.py`.
- Spotify, YouTube, Twitch, OpenAI, GitHub, payment services, webhooks, and other third-party product integrations: not found in active source.
- Public API: FastAPI endpoints exist for health/meta, guilds, settings, security, and features; mutating/management endpoints require API-key and guild authorization checks. Evidence: `api/app.py`, `api/auth.py`, `api/routes/*.py`.
- Dashboard OAuth provider requests `identify guilds`; bot invite uses `bot applications.commands`. Evidence: `dashboard/src/lib/auth.ts`, `core/events.py`.

## 6. Permissions, intents, trust, and reliability

### OAuth / bot permissions

The generated bot invite requests permission integer **1374792445014** and scopes `bot applications.commands`. This is the audited permission bitfield for the bot's implemented moderation, role/channel, messaging, and interaction features; it excludes Administrator. Server owners should still review the authorization screen, feature use, and bot role hierarchy. Evidence: `core/config.py`, `core/events.py`, and the permission checks in `cogs/` and `api/`.

Dashboard OAuth requests `identify guilds`; it uses Discord identity and guild list to select authorized servers. Evidence: `dashboard/src/lib/auth.ts`, `api/auth.py`.

### Gateway intents

- Guilds: explicitly enabled (and part of default intents); used for guild/server operations.
- Members: privileged intent enabled; member join/leave and member-aware actions require it.
- Message Content: privileged intent enabled; prefix commands, AFK/autoresponder, XP and message audit behavior depend on message data.
- Presence: optional and disabled unless `ENABLE_PRESENCE_INTENT=true`.
Evidence: `core/bot.py`, `core/config.py`, `core/events.py`, `cogs/leveling.py`, `cogs/autoresponder.py`.

### Data and retention

SQLite can contain guild IDs/configuration; Discord user/member IDs and moderation actor/target names; warning/case reasons and timestamps; timeout state; ticket channel/user/status metadata; giveaway hosts/prizes/eligibility and ineligible-notification user IDs (no participant list is persisted in the baseline schema); poll questions/options/votes; XP, level, message counts and timestamps; AFK reasons; autoresponder triggers/responses; dashboard configuration audit user/action/details/timestamps; and non-prefix allowlist IDs. Evidence: `db/migrations/001_baseline.sql`–`006_dashboard.sql`.

Command audit embeds can include the full prefix command message content (truncated to 500 characters). Dashboard standalone session/audit tables store IP address and user-agent and include expiries; this is in the aiohttp dashboard, not the FastAPI audit schema. Evidence: `core/events.py`, `dashboard_server.py`.

A general data retention period, automated cleanup schedule, user data export/deletion procedure, and end-user opt-out handling were not found. Some command-driven deletions exist (for example clear warnings, remove AFK/autoresponder/allowlist entries), but no general personal-data deletion command or policy was found. Evidence: `db/repos/*.py`, `cogs/*.py`.

### Resilience / scale

Command sync contains retry/rate-limit handling; API has a rate limiter; no sharding configuration or multi-process cluster implementation was found. Owner stats report current runtime values but are not a verified public stats endpoint. Evidence: `core/bot.py`, `api/ratelimit.py`, `cogs/utility.py`.

## 7. Monetization

No premium gating, subscription, payment, SKU, or entitlement logic was found in active source. The word “premium” appears in server boost metadata reporting, not a Nexus paid plan. It is reasonable to describe the current code as having no paid tiers, but “fully free” should be confirmed by the operator before making a public promise. Evidence: source search across `core/`, `cogs/`, `api/`, `db/`, and `dashboard/`.

## 8. Links and assets

- Invite: the landing page has a configured OAuth invite for the production bot ID, using the scoped permission integer 1374792445014 and `bot applications.commands` scopes. Runtime-generated links use the active bot ID. Evidence: `landing/src/config.ts`, `core/config.py`, `core/events.py`.
- Support server: `SUPPORT_SERVER` defaults to `https://discord.gg/PLACEHOLDER`; actual public invite not found. Evidence: `core/config.py`.
- GitHub repository, documentation site, top.gg listing, public status page, contact email: not found.
- Existing logo, favicon, screenshots: not found in repository assets. The project includes a web command encyclopedia, which is an internal/local page, not published docs. Evidence: `web/commands.html`, repository asset search.

## 9. Live stats hooks

The private owner-only `/stats` reports live bot/server metrics. The standalone dashboard reports runtime/server data from the connected bot when available. The FastAPI metadata/health API exists, but no unauthenticated public endpoint intended for landing-page server/user/command totals was found. Therefore public stats should be omitted or explicitly marked placeholders until an operator supplies a safe, verifiable source. Evidence: `cogs/utility.py`, `dashboard_server.py`, `api/routes/meta.py`.

## Landing feature areas

This curated map is used to generate landing/src/data/features.json. Descriptions and representative command chips are based on the active feature sections above.

| Feature area | Verified benefit / behavior | Command chip | Icon key | Evidence |
|---|---|---|---|---|
| Moderation & case history | Moderation actions create case history with member, moderator, reason, and timestamp. | `/ban` | shield | `cogs/moderation.py`, `db/repos/mod_cases.py` |
| Tickets with transcripts | Members open private support channels; closing creates a text transcript. | `/ticket setup` | ticket | `cogs/tickets.py` |
| Leveling & rewards | Message activity earns configurable XP, levels, and milestone role rewards. | `/rank` | chart | `cogs/leveling.py` |
| Giveaways & polls | Run persisted giveaways and interactive polls with optional role eligibility. | `/giveaway start` | vote | `cogs/giveaway.py`, `cogs/polls.py` |
| Autorole & reaction roles | Assign a role on join or let members choose from configured button panels. | `/autorole set-human` | users | `cogs/autorole.py`, `cogs/reaction_roles.py` |
| Audit logging | Route moderation, server, activity, and command events to configured channels. | `/setupbot` | list | `cogs/logging_events.py`, `core/events.py` |
| Announcements & DMs | Compose server announcements or send staff-directed member and role messages. | `/announce` | send | `cogs/announcements.py`, `cogs/dm.py` |
| Autoresponders | Reply to configured message triggers using supported matching rules. | `/autoresponder add` | reply | `cogs/autoresponder.py` |
| Games | Start button-based Tic-Tac-Toe, Rock-Paper-Scissors, and number guessing. | `/tictactoe` | game | `cogs/games.py` |

## Gaps / needs human input

1. Verify the audited invite permission bitfield (1374792445014) against the production bot's enabled features and role hierarchy before publishing the invite.
2. Real support-server URL (current value is a placeholder).
3. Approved logo/avatar, favicon, and any brand assets.
4. Public live server/member/command counts or explicit decision to omit stats.
5. Public contact email, GitHub repository URL, docs URL, top.gg listing, and status page (if any).
6. Human-reviewed Privacy Policy and Terms; source audit did not find comprehensive retention/deletion/opt-out practices. Dashboard stores IP/user-agent data.
7. Confirm paid-plan positioning: no payment code is present, but operator should approve any “free” promise.
8. Confirm whether schema-only features (birthdays, verification, sticky messages, counting, invite tracking, join-to-create channels) are intended to be advertised; active implementations were not found.
9. Review the public permission guidance against the production bot configuration.
10. Confirm final product name styling (“Nexus” vs “NEXUS BOT”) and whether prior visual assets exist outside this repository.
11. Configure Vercel routing so the landing page serves `/` and the dashboard is reachable at `/dashboard`; the currently observed deployment serves the dashboard at `/`.
