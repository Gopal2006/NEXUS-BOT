"""
Unit tests for FastAPI Dashboard Backend authentication, rate limiting, and endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from api.app import app
from core.config import DASHBOARD_API_KEY

client = TestClient(app)


def test_public_health_endpoints():
    """Verify that health check and root endpoints respond without authentication."""
    res_root = client.get("/")
    assert res_root.status_code == 200
    data_root = res_root.json()
    assert "status" in data_root

    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] in ("healthy", "starting")

    res_stats = client.get("/api/v1/stats")
    assert res_stats.status_code == 200
    data_stats = res_stats.json()
    assert "total_cogs" in data_stats


def test_api_auth_missing_key():
    """Verify that requests missing X-API-Key are rejected with 401."""
    res = client.get("/api/v1/me/guilds")
    assert res.status_code == 401
    assert "Missing X-API-Key" in res.json()["detail"]


def test_api_auth_invalid_key():
    """Verify that requests with incorrect X-API-Key are rejected with 401."""
    res = client.get(
        "/api/v1/me/guilds",
        headers={"X-API-Key": "wrong_key_12345"},
    )
    assert res.status_code == 401
    assert "Invalid X-API-Key" in res.json()["detail"]


def test_api_auth_missing_user_id():
    """Verify that requests missing X-User-Id are rejected with 401."""
    res = client.get(
        "/api/v1/me/guilds",
        headers={"X-API-Key": DASHBOARD_API_KEY},
    )
    assert res.status_code == 401
    assert "Missing X-User-Id" in res.json()["detail"]


def test_api_auth_valid_credentials():
    """Verify that valid X-API-Key and X-User-Id successfully authenticate."""
    res = client.get(
        "/api/v1/me/guilds",
        headers={
            "X-API-Key": DASHBOARD_API_KEY,
            "X-User-Id": "123456789012345678",
        },
    )
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_api_unauthorized_guild_access():
    """Verify that querying a non-existent or inaccessible guild returns 404 or 403."""
    res = client.get(
        "/api/v1/guilds/999999999999999999/settings",
        headers={
            "X-API-Key": DASHBOARD_API_KEY,
            "X-User-Id": "123456789012345678",
        },
    )
    assert res.status_code in (403, 404)


def test_api_unauthorized_announce_and_dm():
    """Verify that announcement and DM endpoints require valid guild management access."""
    res_ann = client.post(
        "/api/v1/guilds/999999999999999999/announce",
        headers={
            "X-API-Key": DASHBOARD_API_KEY,
            "X-User-Id": "123456789012345678",
        },
        json={
            "channel_id": 123456,
            "content": "Test announcement",
        },
    )
    assert res_ann.status_code in (403, 404)

    res_dm = client.post(
        "/api/v1/guilds/999999999999999999/dm",
        headers={
            "X-API-Key": DASHBOARD_API_KEY,
            "X-User-Id": "123456789012345678",
        },
        json={
            "target_type": "user",
            "target_id": 123456,
            "content": "Test DM",
        },
    )
    assert res_dm.status_code in (403, 404)


def test_api_ticket_role_and_lockdown_security():
    """Verify ticket-role, lockdown, and welcome endpoints enforce access control."""
    headers = {
        "X-API-Key": DASHBOARD_API_KEY,
        "X-User-Id": "123456789012345678",
    }
    # Ticket role assignment check
    res_tr = client.post(
        "/api/v1/guilds/999999999999999999/settings/ticket-role",
        headers=headers,
        json={"role_id": 123456},
    )
    assert res_tr.status_code in (403, 404)

    # Emergency lockdown check
    res_ld = client.post(
        "/api/v1/guilds/999999999999999999/settings/lockdown",
        headers=headers,
        json={"scope": "all", "reason": "Test emergency lockdown"},
    )
    assert res_ld.status_code in (403, 404)

    # Welcome settings GET & PUT check
    res_w_get = client.get(
        "/api/v1/guilds/999999999999999999/settings/welcome",
        headers=headers,
    )
    assert res_w_get.status_code in (403, 404)

    res_w_put = client.put(
        "/api/v1/guilds/999999999999999999/settings/welcome",
        headers=headers,
        json={"welcome_msg": "Welcome to {guild}!"},
    )
    assert res_w_put.status_code in (403, 404)

