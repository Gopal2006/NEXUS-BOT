"""
Unified FastAPI Application for Nexus Bot Dashboard Backend.
Serves cloud health checks on Render's single PORT and handles all dashboard API requests.
"""

import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.config import BRAND_NAME, CORS_ORIGINS
from api.ratelimit import rate_limit_dependency
from api.routes import meta, guilds, settings, security, features

log = logging.getLogger("Nexus.API")

app = FastAPI(
    title=f"{BRAND_NAME} Dashboard API",
    description="High-performance backend API serving the Nexus Next.js Web Dashboard",
    version="2.0.0",
)

# ── CORS Middleware ───────────────────────────────────────────────────────────
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if CORS_ORIGINS:
    for orig in CORS_ORIGINS:
        clean = str(orig).strip()
        if clean and clean not in origins:
            origins.append(clean)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount Subrouters ──────────────────────────────────────────────────────────
# Root & Health check (no rate limit for cloud orchestrators)
app.include_router(meta.router)

# Authenticated API v1 routes with rate limiting
app.include_router(guilds.router, dependencies=[Depends(rate_limit_dependency)])
app.include_router(settings.router, dependencies=[Depends(rate_limit_dependency)])
app.include_router(security.router, dependencies=[Depends(rate_limit_dependency)])
app.include_router(features.router, dependencies=[Depends(rate_limit_dependency)])


async def run_api_server(host: str = "0.0.0.0", port: int = 8000):
    """Launches Uvicorn server concurrently on the existing asyncio event loop."""
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    log.info(f"FastAPI Dashboard Backend listening on http://{host}:{port} ✓")
    await server.serve()
