"""
tests/test_users/test_user_router.py — Integration tests for user endpoints.

OOP concepts demonstrated:
- ``UserClientHelper`` encapsulates authentication and user-request helpers,
  removing duplicated HTTP boilerplate and making each test read clearly.
- Each test function has a single responsibility — one assertion, one path.
"""

import pytest
from httpx import AsyncClient


# ── Test helper class (encapsulation) ─────────────────────────────────────────

class UserClientHelper:
    """Wraps HTTP flows needed across multiple user-endpoint tests.

    Encapsulates registration, login, and authenticated GET so each test
    can express its intent without repeating request-building code.
    """

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def register_and_login(
        self,
        email: str = "auth@example.com",
        username: str = "authuser",
        password: str = "Secure@123",
    ) -> str:
        """Register a user (if not already registered) and return the access token."""
        await self._client.post(
            "/api/v1/auth/register",
            json={"email": email, "username": username, "password": password},
        )
        response = await self._client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        return response.json()["access_token"]

    async def create_user(self, email: str, username: str, password: str = "Secure@123"):
        return await self._client.post(
            "/api/v1/users",
            json={"email": email, "username": username, "password": password},
        )

    async def list_users(self, token: str):
        return await self._client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
        )


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    helper = UserClientHelper(client)
    response = await helper.create_user(
        email="newuser@example.com", username="newuser"
    )
    assert response.status_code == 201
    assert response.json()["data"]["email"] == "newuser@example.com"


@pytest.mark.asyncio
async def test_list_users_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/users")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_users_authenticated(client: AsyncClient):
    helper = UserClientHelper(client)
    token = await helper.register_and_login()
    response = await helper.list_users(token)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
