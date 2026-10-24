# 📖 Nexus Discord Bot — Streamlined Command Manual

Welcome to the streamlined command manual for **Nexus Discord Bot**. This manual documents the curated, high-performance feature set resulting from server testing and feedback.

---

## 📑 Table of Contents
1. [Permission Tier Architecture](#1-permission-tier-architecture)
2. [First-Time Server Setup](#2-first-time-server-setup)
3. [Admin & Setup](#3-admin--setup)
4. [Moderation & Security](#4-moderation--security)
5. [Server Management & Roles](#5-server-management--roles)
6. [Engagement & Social](#6-engagement--social)
7. [Mini-Games](#7-mini-games)
8. [Announcements & Direct Messaging](#8-announcements--direct-messaging)
9. [Giveaways & Polls](#9-giveaways--polls)
10. [Support Tickets](#10-support-tickets)
11. [Utility & Diagnostics](#11-utility--diagnostics)
12. [Global Bot Owner Commands](#12-global-bot-owner-commands)

---

## 1. Permission Tier Architecture

Nexus operates on a strict 4-tier security hierarchy. Regular server Administrators **without the bot-role** are intentionally blocked from administrative and moderation operations to maintain server owner control and prevent unauthorized staff escalation.

| Tier | Access Requirements | Modules Covered |
|---|---|---|
| `public` | Everyone in the server | Rank, Leaderboard, AFK, Games (/tictactoe, /rps, /guess), Serverinfo, Userinfo, Ticket Creation, Poll Voting |
| `staff` | Server Owner, Bot Owners, Non-Prefix allowlist, or **holders of the configured Bot-Role** | Help, Moderation suite, Announcements, Staff DMs, Giveaways, Poll Creation, Autorole, Reaction Roles, Leveling Config |
| `owner` | **Server Owner Only** (and Bot Owners) | `/set-botrole`, `/remove-botrole`, `/lockdown`, `/unlockdown`, Ticket Close authority |
| `bot_owner` | Listed in `OWNER_IDS` only | Diagnostic Telemetry (`/ping`, `/stats`, `/uptime`), Slash Command Syncing (`n!sync`), Non-Prefix User Management (`n!addnp`, `n!removenp`, `n!nplist`) |

---

## 2. First-Time Server Setup

Follow this rapid 4-step guide to configure Nexus in a new server:

1. **Designate the Management Bot-Role:**
   ```
   /set-botrole role:@Staff
   ```
   *(If a Bot-Role is already set, run `/remove-botrole` first before assigning a new one).*

2. **Auto-Generate All 4 Audit Channels:**
   ```
   /setupbot
   ```
   *Creates the private `📁 NEXUS LOGS` category with `🔒・mod-logs`, `🔒・server-logs`, `🔒・activity-logs`, and `🔒・cmd-logs` and automatically binds them in the database.*

3. **Configure Welcome & Farewell Greetings:**
   ```
   /set-welcome channel:#welcome message:Welcome {mention} to **{guild}**! 🎉
   /set-leave channel:#farewell message:**{name}** has departed. 👋
   ```

4. **Deploy the Support Ticket System:**
   ```
   /ticket set-role role:@SupportStaff
   /ticket setup channel:#open-a-ticket
   ```

---

## 3. Admin & Setup

| Command | Tier | Invocation | Description |
|---|---|---|---|
| `/setupbot` | `staff` | Slash | Automatically provisions `📁 NEXUS LOGS` with private `mod-logs`, `server-logs`, `activity-logs`, and `cmd-logs`. |
| `/set-botrole <role>` | `owner` | Slash | Configures the management role. If a role already exists, prompts to run `/remove-botrole` first. |
| `/remove-botrole` | `owner` | Slash | Removes the bot-role restriction, restoring exclusive control to the Server Owner. |
| `/set-welcome <channel> [msg]` | `staff` | Slash | Sets welcome channel and template `{mention}`, `{name}`, `{guild}`. |
| `/set-leave <channel> [msg]` | `staff` | Slash | Sets farewell channel and template. |
| `/set-log <channel>` | `staff` | Slash | Manually sets or redirects moderation audit log channel. |
| `/set-cmdlog <channel>` | `staff` | Slash | Manually sets command execution audit log channel. |
| `/config` | `staff` | Slash | Sleek, minimal, professional embed displaying all configured roles, channels, and pipelines. |

---

## 4. Moderation & Security

All disciplinary actions create persistent **Case IDs** and log to `mod-logs`. Role hierarchy is strictly enforced (Nexus cannot act on equal/higher roles; staff cannot act on owners or higher staff).

| Command | Tier | Syntax & Aliases | Requirements & Details |
|---|---|---|---|
| `/kick` | `staff` | `/kick <member> <reason>`<br>`n!kick <@member> <reason>` | **Mandatory reason.** DMs target and logs Case ID. |
| `/ban` | `staff` | `/ban <member> <reason> [delete_days]`<br>`n!ban <@member> <reason>` | **Mandatory reason.** Optional 0-7 day message deletion. DMs target. |
| `/unban` | `staff` | `/unban <user_id> [reason]`<br>`n!unban <user_id> [reason]` | Unbans user using their 18-19 digit Discord ID. |
| `/softban` | `staff` | `/softban <member> <reason>`<br>`n!softban <@member> <reason>` | **Mandatory reason.** Bans and immediately unbans to wipe 24h of messages. |
| `/mute` | `staff` | `/mute <member> <duration> <reason>`<br>`n!mute <@member> <duration> <reason>` | **Mandatory reason.** Timeout from 10s up to 28d (e.g. `10m`, `2h`, `1d`). |
| `/unmute` | `staff` | `/unmute <member> [reason]`<br>`n!unmute <@member> [reason]` | Lifts timeout early. |
| `/warn` | `staff` | `/warn <member> <reason>`<br>`n!warn <@member> <reason>` | Issues logged warning to database with DM notification. |
| `/warnings` | `staff` | `/warnings <member>`<br>`n!warnings <@member>` | Displays chronological warning history with case numbers and reasons. |
| `/clearwarns` | `staff` | `/clearwarns <member>` | Clears all warning history for target user. |
| `/purge` | `staff` | `/purge <amount> [member]`<br>`n!purge <amount>` | Bulk deletes 1-100 messages in current channel with optional user filter. |
| `/lock` | `staff` | `/lock [#channel] [reason]`<br>`n!lock` | Revokes `send_messages` from `@everyone` in channel. |
| `/unlock` | `staff` | `/unlock [#channel]`<br>`n!unlock` | Restores normal `send_messages` to `@everyone`. |
| `/lockdown` | `owner` | `/lockdown [scope] [reason]`<br>`n!lockdown [scope]` | **Emergency Server Lockdown:** Revokes messaging across ALL text channels. |
| `/unlockdown` | `owner` | `/unlockdown [scope]`<br>`n!unlockdown [scope]` | Lifts emergency lockdown across all channels. |
| `/hide` | `staff` | `/hide [#channel]`<br>`n!hide` | Hides channel from `@everyone`. |
| `/unhide` | `staff` | `/unhide [#channel]`<br>`n!unhide` | Restores channel visibility to `@everyone`. |
| `/slowmode` | `staff` | `/slowmode <seconds> [#channel]`<br>`n!slowmode <seconds>` | Sets channel chat cooldown (0-21600s). |
| `/nick` | `staff` | `/nick <member> [nickname]`<br>`n!nick <@member> [nickname]` | Modifies or resets member server nickname. Works with prefix/no-prefix. |
| `/role add` | `staff` | `/role add <member> <role>`<br>`n!role add <@member> <@role>` | Assigns role adhering to role hierarchy. Works with prefix/no-prefix. |
| `/role remove` | `staff` | `/role remove <member> <role>`<br>`n!role remove <@member> <@role>` | Revokes role adhering to role hierarchy. Works with prefix/no-prefix. |
| `/modlogs` | `staff` | `/modlogs <member>` | Displays complete immutable disciplinary history for user. |

---

## 5. Server Management & Roles

| Command | Tier | Invocation | Description |
|---|---|---|---|
| `/autorole set-human <role>` | `staff` | Slash / `n!autorole set <role>` | Automatically assigns role to new human members on joining. |
| `/autorole view` | `staff` | Slash / `n!autorole` | Displays current human autorole configuration. |
| `/autorole clear` | `staff` | Slash / `n!autorole clear` | Disables member autorole. |
| `/reactionrole add` | `staff` | Slash | Attaches a persistent interactive button to any message for self-role assignment. |
| `/reactionrole remove` | `staff` | Slash | Detaches self-role button from target message. |

---

## 6. Engagement & Social

| Command | Tier | Invocation | Description |
|---|---|---|---|
| `/rank [member]` | `public` | Slash / `n!rank` | Displays member level, XP, rank card, and progress towards next level. |
| `/leaderboard [page]` | `public` | Slash / `n!leaderboard` | Server top 10 most active members by XP with trophy badges. |
| `/leveling toggle <state>` | `staff` | Slash | Master toggle for chat XP tracking. |
| `/leveling rates` | `staff` | Slash | Configures min/max XP awarded per message and cooldown. |
| `/leveling rewards` | `staff` | Slash | Automatically assigns Discord roles when members hit milestone levels. |
| `/afk [reason]` | `public` | Slash / `n!afk [reason]` | Sets AFK status. Alerts anyone who pings you and clears on your next message. |
| `/autoresponder add` | `staff` | Slash | Creates keyword-triggered automated bot reply (exact or contains). |
| `/autoresponder list` | `staff` | Slash | Displays all custom autoresponder triggers. |

---

## 7. Mini-Games

| Command | Tier | Invocation | Description |
|---|---|---|---|
| `/tictactoe <opponent>` | `public` | Slash / `n!tictactoe <@opponent>` | Interactive 3x3 button Tic-Tac-Toe. Player turns and unauthorized clicks are strictly enforced. |
| `/rps [opponent]` | `public` | Slash / `n!rps [@opponent]` | Rock-Paper-Scissors against the bot or 2-player match with hidden secret selections. |
| `/guess` | `public` | Slash / `n!guess` | Number guessing game (1-100). **Edits the same single message on every guess** with higher/lower hints. |

---

## 8. Announcements & Direct Messaging

| Command | Tier | Invocation | Description |
|---|---|---|---|
| `/announce` | `staff` | Slash | Interactive modal announcement builder: Title, Description, Color hex, native image attachment, URL button, and optional @everyone/@here ping. |
| `/dm-user <user> <message>` | `staff` | Slash / `/dm` | Sends official server notification direct message to a user with delivery logged in activity logs. |
| `/dm-role <role>` | `staff` | Slash | Broadcasts a formatted DM to all members of a role with progress updates and rate-limit throttling. |

---

## 9. Giveaways & Polls

| Command | Tier | Invocation | Description |
|---|---|---|---|
| `/gstart <duration> <winners> <prize> [roles]` | `staff` | Slash | Launches giveaway with multi-role entry requirements. Survives bot reboots. |
| `/gend <message_id>` | `staff` | Slash | Immediately concludes an active giveaway and picks winners. |
| `/greroll <message_id>` | `staff` | Slash | Rerolls new winners from eligible participants. |
| `/glist` | `staff` | Slash | Lists all active giveaways in the server. |
| `/poll` | `staff` | Slash | Modal poll creator (1-5 options, button voting, single vote per user, optional role restriction). |
| `/endpoll <message_id>` | `staff` | Slash | Concludes poll and posts final percentage breakdown. |

---

## 10. Support Tickets

| Command | Tier | Invocation | Description |
|---|---|---|---|
| `/ticket setup <channel>` | `staff` | Slash | Deploys interactive '📩 Open Ticket' panel into target channel. |
| `/ticket set-role <role>` | `staff` | Slash | Designates support staff role automatically granted access to new tickets. |
| `/ticket close` | `staff` / `owner` | Slash / `n!ticket close` | **Staff and Server Owner only.** Closes ticket, compiles full `.txt` transcript, DMs copy to user, and archives to activity logs. |
| `/ticket add <member>` | `staff` | Slash / `n!ticket add <@member>` | Grants member access to private ticket channel. |
| `/ticket remove <member>` | `staff` | Slash / `n!ticket remove <@member>` | Revokes member access from ticket channel. |

---

## 11. Utility & Diagnostics

| Command | Tier | Invocation | Description |
|---|---|---|---|
| `/help [category]` | `staff` | Slash / `n!help` | **Staff role only.** Interactive categorized dropdown manual of all bot features and syntax. |
| `/userinfo [member]` | `public` | Slash / `n!userinfo` | Deep profile inspection: ID, join date, account creation date, badges, permissions, and roles. |
| `/serverinfo` | `public` | Slash / `n!serverinfo` | Professional, comprehensive server breakdown: owner, creation date, boost tier, demographics, and security. |
| `/ping` | `bot_owner` | Slash / `n!ping` | **Bot Owner Only.** Displays gateway WebSocket latency and REST API roundtrip time. |
| `/stats` | `bot_owner` | Slash / `n!stats` | **Bot Owner Only.** Displays cluster reach, total servers, audience reach, environment, and uptime. |
| `/uptime` | `bot_owner` | Slash / `n!uptime` | **Bot Owner Only.** Exact uptime elapsed since bot container started. |

---

## 12. Global Bot Owner Commands

| Command | Tier | Syntax | Description |
|---|---|---|---|
| `n!sync` | `bot_owner` | `n!sync [guild\|force]` | Synchronizes application slash commands with Discord API with automatic rate-limit backoff. |
| `n!addnp` | `bot_owner` | `n!addnp <user_id>` | Grants a user non-prefix execution rights across all servers. |
| `n!removenp` | `bot_owner` | `n!removenp <user_id>` | Revokes non-prefix execution privileges from a user. |
| `n!nplist` | `bot_owner` | `n!nplist` | Lists all users currently authorized on the global non-prefix allowlist. |