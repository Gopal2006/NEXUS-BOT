# 🎛️ Nexus Bot — Web Control Center & Dashboard Manual

The **Nexus Web Control Dashboard** is an enterprise-grade, real-time command & control web interface built specifically for Nexus Discord Bot. It features glassmorphism styling, a curated Discord-dark aesthetic, live WebSocket log streaming, and an interactive real-time Discord embed simulator.

---

## 🚀 How to Launch the Webpage

### Option 1: Automatic Launch with the Bot (Recommended)
When you start the bot, the control dashboard starts automatically in the same event loop on port `5000`:
```bash
python bot.py
```
*Console output:*
```
🚀 Nexus Control Dashboard running at: http://localhost:5000
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser!

### Option 2: Standalone Dashboard Runner
You can also run the web dashboard independently (even if the bot is currently stopped) to configure SQLite databases, manage authorized non-prefix users, and view past giveaways/tickets:
```bash
python run_dashboard.py
```

### Custom Dashboard Port
You can customize the port via the `.env` file or environment variables:
```env
DASHBOARD_PORT=8080
# or for cloud deployments (Render, Railway, Fly.io):
PORT=8080
```

---

## 🌟 Feature Breakdown

### 1. 📊 Real-Time Telemetry & Insights
- **Live Connection Status:** Real-time indicator (🟢 Online / 🔴 Offline) with gateway heartbeat ping in milliseconds.
- **KPI Metrics:** Connected server count, total cached users, active giveaways, open support tickets, and total warning cases.
- **Quick Presence Switcher:** Set bot status (`Online`, `Idle`, `Do Not Disturb`, `Invisible`) and custom activity (`Playing`, `Watching`, `Listening`, `Streaming`, `Competing`).
- **Server Overview Grid:** Visual cards for every joined server with icons, member counts, and 1-click configuration shortcuts.

### 2. ⚙️ Server Configuration Studio
- **Bot Manager Role (`bot_role_id`):** Restrict bot management to a designated staff role.
- **Ticket Support Role (`ticket_role_id`):** Designate who can view and answer tickets.
- **Audit Log Channel Mappings:**
  - 🔒 Moderation Action Logs (`mod_log_ch`)
  - 🔒 Server Events Logs (`server_log_ch`)
  - 🔒 Activity & Ticket Logs (`activity_log_ch`)
  - 🔒 Prefix & Non-Prefix Execution Logs (`cmd_log_ch`)
- **🪄 Auto-Setup Audit Logs:** 1-click button that creates the `📁 NEXUS LOGS` category and private channels directly in Discord.
- **Welcome & Farewell System:** Channel pickers and custom text editors with click-to-insert placeholder pills (`{mention}`, `{name}`, `{guild}`) with live dynamic preview.

### 3. 🛡️ Complete Moderation Suite
- **Member Disciplinary Actions:**
  - ⚠️ **Warn Member:** Records warning case to database and logs to audit channel.
  - ⏳ **Timeout / Mute:** Flexible durations (`60s`, `5m`, `10m`, `1h`, `1d`, `1w`) with reason requirement.
  - 🔊 **Remove Timeout:** Restores voice and chat permissions immediately.
  - 🚪 **Kick Member:** Kicks user, sends DM notice, and generates mod log.
  - 🔨 **Ban Member:** Bans user with pruning (0 to 7 days) and DM notice.
  - 🔓 **Unban User:** Revokes bans by numerical Discord user ID.
- **Channel Operations:**
  - 🔒 **Channel Lockdown / Unlock:** 1-click toggle for channel `@everyone` send permissions.
  - ⏱️ **Rate Limit (Slowmode):** Interactive slider from 0s (Off) up to 5 minutes.
  - 🗑️ **Bulk Message Purge:** Bulk deletes 1 to 100 recent messages from any channel.
- **Active Warnings Table:** Search and view all server warning records with case numbers, timestamps, and "Clear Warns" action.

### 4. 📢 Announcements Studio & Live Discord Simulator
- **Live Discord Message Simulator:** Right-hand panel updates in real-time as you type, rendering:
  - Exact Discord message card with bot avatar and `APP` badge.
  - Colored embed border with 8 curated preset swatches (Blurple, Green, Gold, Red, Purple, Cyan, Fuchsia, Dark).
  - Embed title, description, thumbnail preview, and large banner image preview.
  - Clickable Discord action button preview (`Label | URL`).
  - Ping badges (`@everyone` / `@here`).
- **Publish Button:** Dispatches the announcement directly to the target Discord channel.

### 5. ✉️ Direct Messaging (DM) Dispatcher
- **Target Modes:** Send to an **Individual Member** or **Broadcast to an Entire Role**.
- Custom subject, markdown message body, embed color, and link action button.
- Anti-rate-limit dispatching with progress counts (`Delivered: X, Failed: Y`).

### 6. 🎉 Giveaways Manager
- **Launch Giveaway:** Channel picker, prize name, duration (`10m`, `2h`, `1d`, etc.), winners count (1-20), and required role restrictions.
- **Active Giveaways Monitor:** View time remaining, prizes, channel, and force-end or reroll giveaways directly from the web.

### 7. 🗳️ Interactive Polls Studio
- Create multi-choice polls (2 to 10 options) with native clickable Discord UI buttons.
- Quick templates: "Yes / No", "Agree / Disagree".
- Configurable duration in minutes.

### 8. 🎫 Support Tickets Hub
- **Deploy Intake Panel:** Send official support panel with custom title, instructions, and interactive `Open Ticket` button into any channel.
- **Live Tickets Table:** View open tickets with user IDs, channel IDs, and 1-click "Close & Delete" button.

### 9. 👑 Non-Prefix Access Manager
- Authorize trusted staff or developers to run commands without the `n!` prefix.
- Manage authorized users with date added and 1-click revocation.

### 10. 📜 Live Console & Activity Terminal
- Real-time streaming WebSocket logs directly from the running bot instance.
- Filter by level (`ALL`, `INFO`, `WARNING`, `ERROR`).
- Search bar to filter messages in real-time.
- Auto-scroll lock toggle, clear screen, and instant error inspection.

### 11. 🛡️ Secret Admin Panel & Live Operator Tracking (Strict Access)
- **Strict Role-Based Access Control (RBAC):**
  - **Owner (`owner`):** Full control over the dashboard and bot. Can authorize new administrators and operators, toggle access, revoke active sessions, and inspect all audit logs.
  - **Administrator (`admin`):** Granted access to the Admin Panel. Can manage operators and view live sessions and security logs.
  - **Operator (`operator`):** Can access bot configuration, moderation, giveaways, polls, and tickets. The **Admin Panel button is strictly hidden** and API endpoints return `403 Forbidden`.
  - **Unauthenticated Visitors:** Completely blocked by the glassmorphic authentication gate. Zero buttons or data are exposed without a valid session.
- **Strict Visual Boundary:** The Admin Panel button is hidden (`display: none`) and only made visible by client code after cryptographically validating the session token with the server.
- **Live User Tracker (Active Sessions):** Real-time visibility into who is currently using the website, their IP address, browser/device info, and last activity timestamp, with a 1-click **Revoke Session** button.
- **Immutable Security Audit Trail:** Every single action executed via the dashboard (warn, kick, ban, purge, config update, announcement, giveaway, etc.) is recorded into the SQLite database with the operator's Discord ID, username, target guild, details, and client IP address.

---

## 🔒 Security Architecture & Login Credentials

### Default Owner Account
When the dashboard initializes, it automatically provisions the Primary Bot Owner account:
- **Discord User ID:** `1201050377911554061`
- **Default Passcode:** `nexus-owner-2026` *(Can be customized via `DASHBOARD_PASSCODE` in `.env`)*

### Adding Other Admins or Operators
1. Sign in to the dashboard at `http://localhost:5000` using your Owner ID and passcode.
2. Click the **Admin Panel** tab in the sidebar (only visible to Admins/Owner).
3. Click **+ Authorize Operator / Admin**.
4. Enter the Discord User ID, display name, select role (`Operator` or `Administrator`), and assign a secure passcode.
5. Give the passcode to your staff member. Once they sign in, all their actions will be tracked and audited under their name!

