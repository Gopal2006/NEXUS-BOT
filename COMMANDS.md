# 📖 Nexus Bot — Complete Commands & Usage Manual

Welcome to the comprehensive command manual for **Nexus Discord Bot**. This guide explains every feature, command syntax, permission level, and practical example.

---

## 📑 Table of Contents
1. [Permission Architecture](#1-permission-architecture)
2. [First-Time Server Setup](#2-first-time-server-setup)
3. [Admin & Configuration Commands](#3-admin--configuration-commands)
4. [Moderation System (Slash, Prefix & Non-Prefix)](#4-moderation-system)
5. [Announcements System](#5-announcements-system)
6. [Direct Messaging (DM) System](#6-direct-messaging-dm-system)
7. [Giveaways System](#7-giveaways-system)
8. [Polls System](#8-polls-system)
9. [Support Ticket System](#9-support-ticket-system)
10. [Audit & Command Logging System](#10-audit--command-logging-system)
11. [FAQ: What is `nexus.db`?](#11-faq-what-is-nexusdb)

---

## 1. Permission Architecture

Nexus uses a strict, role-isolated permission model to protect your server:

```
┌──────────────────────▼───────────────────────┐
│                 SERVER OWNER                 │ (Can configure bot-role)
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│            BOT-ROLE MANAGERS                 │ (Granted via /set-botrole)
└──────────────────────┬───────────────────────┘
```

> 🔒 **Critical Security Rule:** Regular server **Administrators** WITHOUT the configured bot-role **CANNOT** use bot management commands. The server owner must explicitly assign a bot role using `/set-botrole`.

---

## 2. First-Time Server Setup

Follow these steps to set up Nexus in a new Discord server:

1. **Assign Staff Role:**
   ```
   /set-botrole role:@Staff
   ```
2. **Auto-Create Audit Log Channels:**
   ```
   /setupbot
   ```
   *Creates `📁 NEXUS LOGS` with `🔒・mod-logs`, `🔒・server-logs`, and `🔒・activity-logs`.*
3. **Configure Welcome & Leave Channels (Optional):**
   ```
   /set-welcome channel:#welcome message:Welcome {mention} to **{guild}**! 🎉
   /set-leave channel:#goodbye message:**{name}** has left the server. Goodbye! 👋
   ```
4. **Deploy Ticket System (Optional):**
   ```
   /ticket set-role role:@SupportStaff
   /ticket setup channel:#open-a-ticket
   ```

---

## 3. Admin & Configuration Commands

| Command | Type | Description | Required Permission |
|---|---|---|---|
| `/setupbot` | Slash | Automatically creates private audit log channels and links them | Server Owner / Bot-Role |
| `/set-botrole <role>` | Slash | Designates the management role that can run Nexus commands | **Server Owner Only** |
| `/remove-botrole` | Slash | Removes bot-role restriction (restricts bot back to Server Owner) | **Server Owner Only** |
| `/set-welcome <channel> [message]` | Slash | Sets welcome channel and customizable join message | Server Owner / Bot-Role |
| `/set-leave <channel> [message]` | Slash | Sets leave channel and customizable farewell message | Server Owner / Bot-Role |
| `/set-log <channel>` | Slash | Sets the moderation action log channel manually | Server Owner / Bot-Role |
| `/set-cmdlog <channel>` | Slash | Sets the dedicated prefix/non-prefix command execution log channel | Server Owner / Bot-Role |
| `/config` | Slash | Displays full server settings, assigned roles, and channels | Server Owner / Bot-Role |
| `/serverstats` | Slash | Real-time server statistics (members, bots, channels, roles, bot uptime) | Server Owner / Bot-Role |

### Welcome/Leave Placeholders:
- `{mention}` — Mentions the member (`@user`)
- `{name}` — Member's username (`username`)
- `{guild}` — The name of the server

---

## 4. Moderation System

Moderation commands are available via **Slash Commands (`/`)**, **Prefix (`n!`)**, and **Non-Prefix** (for authorized non-prefix users).

> 🛡️ **Reason Requirement:** To ensure high accountability, a reason is **strictly required** for kick, ban, and warn actions.

| Slash Command | Prefix Command | Non-Prefix Command | Parameters & Description |
|---|---|---|---|
| `/kick` | `n!kick` | `kick` | `<@member> <reason>` — Kicks member, sends DM notice with reason, and logs action |
| `/ban` | `n!ban` | `ban` | `<@member> <reason> [delete_days: 0-7]` — Bans member and prunes messages |
| `/unban` | — | — | `<user_id> [reason]` — Unbans user by numerical Discord ID |
| `/mute` | `n!mute` | `mute` | `<@member> [duration: 10m] [reason]` — Puts member in timeout (min: `10s`, e.g. `30m`, `2h`, `1d`) |
| `/unmute` | `n!unmute` | `unmute` | `<@member> [reason]` — Removes timeout from a member |
| `/warn` | `n!warn` | `warn` | `<@member> <reason>` — Logs an official warning case to the database |
| `/warnings` | `n!warnings` | `warnings` | `<@member>` — Displays active warnings with case numbers, timestamps, and mod names |
| `/clearwarns` | — | — | `<@member>` — Clears all logged warnings for a member |
| `/purge` | `n!purge` | `purge` | `[amount: 1-100]` — Bulk deletes channel messages |
| `/lock` | `n!lock` | `lock` | `[#channel] [reason]` — Prevents `@everyone` from sending messages in the channel |
| `/unlock` | `n!unlock` | `unlock` | `[#channel]` — Restores channel permissions to default |
| `/slowmode` | `n!slowmode` | `slowmode` | `<seconds> [#channel]` — Sets rate limit delay (`0` to disable) |

### Duration Format Guide:
- `30s` = 30 seconds
- `10m` = 10 minutes
- `2h` = 2 hours
- `1d` = 1 day
- `1d12h` = 1 day 12 hours

---

## 5. Announcements System

Deploy professional server announcements with interactive popup modals.

### Usage:
```
/announce channel:#announcements [type: Embed / Plain Text] [ping: @everyone / @here / None]
```

### Modal Fields:
- **Title / Heading (Optional):** Supports bold/markdown. Leave blank for image-only posts.
- **Announcement Content (Optional):** Full message body. Leave blank for photo-only announcements.
- **Color / Theme (Optional):** `gold`, `red`, `green`, `blue`, `purple`, or hex `#5865F2`.
- **Banner / Image URL (Optional):** Web image URL or uploaded attachment.
- **Action Button (Optional):** Adds a clickable URL button (e.g. `Visit Website | https://example.com`).

> 💡 **Image Display:** Images are uploaded as native Discord file attachments, eliminating unsightly link preview pills.

---

## 6. Direct Messaging (DM) System

Send official server notices directly to user DMs with custom color themes and buttons.

### Commands:
- `/dm-user member:@User` (Alias: `/dm member:@User`)
  *Opens popup modal to message an individual member.*
- `/dm-role role:@Role`
  *Opens popup modal to broadcast to every member holding a specific role.*

### Modal Features:
- **Subject / Title (Optional)**
- **Message Content (Required)**
- **Embed Color / Theme (Optional)**
- **Banner / Image URL (Optional)**
- **Action Button (Optional):** `Label | URL` (e.g. `Join Voice | https://discord.gg/...`)

> 📊 **Audit & Delivery Stats:** Automatically reports delivery count (`sent` vs `failed/closed DMs`) and archives the message with full image in `🔒・activity-logs`.

---

## 7. Giveaways System

Host automated giveaways with countdown timers and multi-role requirements.

### Commands:
- `/giveaway start channel:#giveaways duration:2d prize:Nitro winners:1 [role:Role Requirements]`
- `/giveaway end message_id:1234567890`
- `/giveaway reroll message_id:1234567890 [winners:1]`
- `/giveaway list`

### 🎯 Multi-Role Requirements & Ineligible Member Notification:
You can require multiple roles in a single string input:
```
/giveaway start channel:#giveaways duration:24h prize:VIP Pass role:@Subscriber, @Booster, @VIP
```
- **Single-Time DM Warning:** If an ineligible member reacts to enter, the bot sends them **one** private DM explaining they lack the required role.
- **Silent Auto-Removal:** If the member attempts to react again to the same giveaway, the reaction is silently removed without spamming their DMs.

---

## 8. Polls System

Create clean, interactive voting cards with live button clicks.

### Commands:
- `/poll channel:#polls [role:@Voters]`
  *Opens modal popup asking for Question and Options 1 to 5.*
- `/endpoll message_id:1234567890`
  *Closes the poll early and tallies the final results.*

### Features:
- **One Vote Per User:** Members can change their vote, but cannot vote multiple times.
- **Role Restriction:** Restrict voting eligibility to members with a specific role.

---

## 9. Support Ticket System

Full-featured private support ticket channels with transcript tracking.

### Commands:
- `/ticket setup channel:#tickets`
  *Sends the official ticket creation panel with an interactive `📩 Open Ticket` button.*
- `/ticket set-role role:@SupportStaff`
  *Designates the staff role that has access to view and respond to tickets.*
- `/ticket close [reason]`
  *Closes the ticket channel and generates an activity log entry.*
- `/ticket add member:@User`
  *Adds an additional member into the ticket.*
- `/ticket remove member:@User`
  *Removes a member from the ticket.*

---

## 10. Audit & Command Logging System

Nexus provides comprehensive, multi-channel audit logging:

| Channel | Config Key | Recorded Events |
|---|---|---|
| `🔒・mod-logs` | `mod_log_ch` | Kicks, Bans, Timeouts, Warnings (includes `⚡ No Prefix`, `🏷️ Prefix`, or `📱 Slash Command`) |
| `🔒・server-logs` | `server_log_ch` | Channel Locks, Unlocks, Slowmode adjustments, Message Purges |
| `🔒・activity-logs` | `activity_log_ch` | Staff DMs, Ticket creations/closures, Giveaway winners & ends |
| `⌨️ Command Logs` | `cmd_log_ch` | Every prefix (`n!`) and non-prefix command executed across the server |

### Customizing Log Channels:
```
/set-log channel:#my-mod-logs
/set-cmdlog channel:#my-command-logs
```

---

## 11. FAQ: What is `nexus.db`?

### What is `nexus.db`?
`nexus.db` is an SQLite database file that Nexus automatically creates on your local machine when `python bot.py` is started.

### What does it store?
1. **Server Configurations (`guild_config`):** Assigned bot role, ticket role, welcome/leave channels, custom messages, and log channel IDs.
2. **Non-Prefix Users (`non_prefix_users`):** User IDs granted prefix-free command access.
3. **Giveaways (`giveaways` & `giveaway_ineligible_dms`):** Active giveaways, end timestamps, message IDs, prize details, required role IDs, and ineligible DM tracking.
4. **Member Warnings (`warns`):** Moderator warnings, timestamps, and case histories.
5. **Support Tickets (`tickets`):** Active ticket channels and creator IDs.
6. **Mutes (`mutes`):** Member timeouts for the auto-unmute background task.

### Should `nexus.db` be committed or pushed to Git?
**NO.** `nexus.db` should **never** be pushed to Git or public repositories because:
- It contains private server IDs, user IDs, and local testing configurations.
- When you or someone else downloads the bot and runs `python bot.py`, the bot automatically initializes a clean, fresh `nexus.db` database automatically.
- Nexus includes `nexus.db` in [.gitignore](.gitignore) to ensure it stays private on your local machine.

### Can I delete `nexus.db`?
Yes! If you ever want to completely wipe all local test data and start 100% fresh, simply delete `nexus.db`. When you next run `python bot.py`, a brand new database will be initialized automatically.
