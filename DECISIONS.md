# DECISIONS.md — Architecture & Implementation Decisions

This document records architectural, security, and compatibility decisions made during the Nexus Bot upgrade.

---

## 1. Permission System & Bot-Role Rule
- **Decision:** Dashboard and management commands strictly adhere to the existing Nexus security principle: Guild Owner, Global Bot Owners (`OWNER_IDS`), or holders of the configured `bot_role_id` have management access. Server Administrators who lack the bot role are blocked.
- **Rationale:** Preserves the core security invariant of Nexus designed by the server owners.

## 2. Framework & Library Choice
- **Decision:** Pycord 2.8+ is exclusively used for all bot code. Discord.py-only APIs (`app_commands`, `hybrid_command`, `tree.sync`) are strictly disallowed.
- **Rationale:** The entire codebase was built on Pycord with custom interaction dispatchers.

## 3. Database Architecture & Migrations
- **Decision:** All database changes are strictly additive migrations tracked in `db/migrations/` with a `schema_migrations` table. Existing table columns and user data in `nexus.db` will never be deleted or renamed. `PRAGMA journal_mode=WAL` will be enforced for high-concurrency read/write between Discord gateway events and FastAPI endpoints.
- **Rationale:** Zero data loss guarantee for existing production installations.

## 4. Single Port Handling on Cloud Hosts (Render)
- **Decision:** When `API_ENABLED=true` (default), the unified FastAPI server listens on `PORT` (or `API_PORT`), serving `/health` at root for cloud health-checks, alongside all `/api/v1` routes. The legacy aiohttp server is only launched if `API_ENABLED=false`.
- **Rationale:** Prevents port conflict errors on platforms like Render where only a single external port is allocated per container.

## 5. Owner ID Centralization
- **Decision:** The hardcoded `GLOBAL_OWNER_ID = 1201050377911554061` found duplicated in 8 files is replaced by `OWNER_IDS` loaded from environment variables (comma-separated list of IDs), with a fallback to `[1201050377911554061]` if unspecified in `.env`.
- **Rationale:** Protects security and enables multiple developers/owners without breaking existing owner privileges.

## 6. Dashboard Authentication Architecture
- **Decision:** Two-layer security for the Dashboard API:
  1. `X-API-Key` header matching server-side `DASHBOARD_API_KEY`.
  2. `X-User-Id` identifying the authenticated Discord user, verified against the bot's live guild cache. Next.js Route Handlers act as a secure backend-for-frontend proxy, never exposing `DASHBOARD_API_KEY` to the browser client.
- **Rationale:** Prevents client token leakage and strictly enforces server-side permission checks.

## 7. Zero Music Features
- **Decision:** Zero audio playback, voice streaming, yt-dlp, Lavalink, or Wavelink dependencies. Voice capabilities are strictly limited to Join-To-Create channel lifecycle management.
- **Rationale:** Explicit requirement in the project specification.

## 8. Dashboard Implementation & Real-time Live Cache Sync
- **Decision:** Built on Next.js 14 App Router with TypeScript and Tailwind CSS. The web frontend communicates exclusively through server-side Route Handlers (`/api/backend/[...path]`), preventing the API key from leaking to the browser. Every mutation writes directly to `nexus.db`, records an entry in `dashboard_audit`, and automatically invalidates the bot's in-memory `guild_config` cache for instant, zero-restart synchronization with the Discord bot.
- **Rationale:** Provides high responsiveness, enterprise-grade auditability, and immediate runtime effect without needing bot reboots.

