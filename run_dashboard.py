"""
Nexus Web Control Dashboard — Standalone Launcher
Run this script to launch the web control dashboard at http://localhost:5000
"""

import os
import sys
from pathlib import Path
from aiohttp import web
from dotenv import load_dotenv

# Ensure utf-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

load_dotenv()

from dashboard_server import create_app

def main():
    port = int(os.getenv("PORT") or os.getenv("DASHBOARD_PORT") or 5000)
    print("=" * 60)
    print("  [NEXUS BOT] Command & Control Web Dashboard")
    print(f"  Access URL: http://localhost:{port}")
    print("  Database:   nexus.db")
    print("=" * 60)

    app = create_app()
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
