"""
tests/test_auth/test_auth_router.py — Integration tests for auth endpoints.

Tests go through the full HTTP stack: router → service → repo → DB.

OOP concepts demonstrated:
- The ``AuthClientHelper`` class encapsulates common auth test operations,
  removing duplication across test functions (the DRY principle applied via
  a helper class).
- Each test function has a single responsibility — testing one behaviour.
"""

import pytest
from httpx import AsyncClient


# ── Test helper class (encapsulation of shared auth operations) ───────────────

class AuthClientHelper:
    """Wraps common authentication flows used across multiple test functions.

    Encapsulates the HTTP payloads and endpoint paths so tests can read like
    plain English without repeating request-building boilerplate.
    """

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def register(
        self,
        email: str,
        username: str,
        password: str = "Secure@123",
        full_name: str | None = None,
    ):
        payload = {"email": email, "username": username, "password": password}
        if full_name:
            payload["full_name"] = full_name
        return await self._client.post("/api/v1/auth/register", json=payload)

    async def login(self, email: str, password: str = "Secure@123"):
        return await self._client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    helper = AuthClientHelper(client)
    response = await helper.register(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    helper = AuthClientHelper(client)
    await helper.register(email="dup@example.com", username="user1")

    # Second registration with the same email but different username
    response = await helper.register(email="dup@example.com", username="user2")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    helper = AuthClientHelper(client)
    await helper.register(email="login@example.com", username="loginuser")

    response = await helper.login(email="login@example.com")
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    helper = AuthClientHelper(client)
    await helper.register(email="wrong@example.com", username="wronguser")

    response = await helper.login(email="wrong@example.com", password="WrongPassword@1")
    assert response.status_code == 401
