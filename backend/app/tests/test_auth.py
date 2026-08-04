"""Authentication endpoint tests — 15 scenarios from the Phase 1 Step 3 spec.

pytest.ini sets ``asyncio_mode = auto`` so no ``@pytest.mark.asyncio`` needed.

Cross-session visibility note
------------------------------
The ``client`` fixture and ``sessionmaker_`` both point at the same
in-memory SQLite engine (StaticPool), but each opens its own connection.
To ensure mutations from the test helper session are visible to the next
HTTP call through the client, any direct-DB test must:

  1. Commit through its session before issuing the HTTP request.
  2. Open a *fresh* session for the read-back (after the request),
     not reuse the one it committed with — SQLAlchemy's identity map
     caches the pre-update snapshot until the session is refreshed.
"""
from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

# pyrefly: ignore [missing-import]
from httpx import AsyncClient
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.core.security import create_access_token
from app.db.repositories.user_repository import UserRepository

if TYPE_CHECKING:
    pass  # all runtime imports are already above


# ---------------------------------------------------------------------------
# Scenario 1: Register valid
# ---------------------------------------------------------------------------

async def test_register_valid(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "s1@example.com", "full_name": "Scenario One", "password": "securepassword123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "s1@example.com"
    assert data["full_name"] == "Scenario One"
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data


# ---------------------------------------------------------------------------
# Scenario 2: Register duplicate email
# ---------------------------------------------------------------------------

async def test_register_duplicate_email(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "full_name": "Dup User", "password": "securepassword123"},
    )
    resp2 = await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "full_name": "Another Name", "password": "securepassword123"},
    )
    assert resp2.status_code == 400
    assert resp2.json()["detail"] == "Email already registered"


# ---------------------------------------------------------------------------
# Scenario 3: Register invalid email
# ---------------------------------------------------------------------------

async def test_register_invalid_email(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "full_name": "Invalid", "password": "securepassword123"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Scenario 4: Register weak password
# ---------------------------------------------------------------------------

async def test_register_weak_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "full_name": "Weak", "password": "short"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Scenario 5: Login valid
# ---------------------------------------------------------------------------

async def test_login_valid(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "s5@example.com", "full_name": "Login User", "password": "securepassword123"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "s5@example.com", "password": "securepassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


# ---------------------------------------------------------------------------
# Scenario 6: Login wrong password
# ---------------------------------------------------------------------------

async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "s6@example.com", "full_name": "Wrong Pass", "password": "securepassword123"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "s6@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


# ---------------------------------------------------------------------------
# Scenario 7: Login unknown email — same body as #6 (no enumeration)
# ---------------------------------------------------------------------------

async def test_login_unknown_email(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "securepassword123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


# ---------------------------------------------------------------------------
# Scenario 8: Login inactive user
# ---------------------------------------------------------------------------

async def test_login_inactive_user(
    client: AsyncClient,
    sessionmaker_: async_sessionmaker[AsyncSession],
) -> None:
    # Register via client (commits automatically when the request finishes)
    await client.post(
        "/api/v1/auth/register",
        json={"email": "s8@example.com", "full_name": "Inactive User", "password": "securepassword123"},
    )

    # Deactivate the user directly via a fresh DB session and commit.
    async with sessionmaker_() as session:
        repo = UserRepository(session)
        user = await repo.get_by_email("s8@example.com")
        assert user is not None
        await repo.set_active(user, is_active=False)
        await session.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "s8@example.com", "password": "securepassword123"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Inactive account"


# ---------------------------------------------------------------------------
# Scenario 9: /me valid token
# ---------------------------------------------------------------------------

async def test_me_valid_token(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "s9@example.com", "full_name": "Me User", "password": "securepassword123"},
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "s9@example.com", "password": "securepassword123"},
    )
    token = login_resp.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "s9@example.com"
    assert data["full_name"] == "Me User"


# ---------------------------------------------------------------------------
# Scenario 10: /me expired token
# ---------------------------------------------------------------------------

async def test_me_expired_token(client: AsyncClient) -> None:
    token = create_access_token(
        subject="00000000-0000-0000-0000-000000000001",
        expires_delta=timedelta(seconds=-1),
    )
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


# ---------------------------------------------------------------------------
# Scenario 11: /me malformed token
# ---------------------------------------------------------------------------

async def test_me_malformed_token(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


# ---------------------------------------------------------------------------
# Scenario 12: /me missing token
# ---------------------------------------------------------------------------

async def test_me_missing_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


# ---------------------------------------------------------------------------
# Scenario 13: /me inactive user
# ---------------------------------------------------------------------------

async def test_me_inactive_user(
    client: AsyncClient,
    sessionmaker_: async_sessionmaker[AsyncSession],
) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "s13@example.com", "full_name": "Me Inactive", "password": "securepassword123"},
    )

    # Read user id, deactivate, and commit — all in one session.
    user_id = None
    async with sessionmaker_() as session:
        repo = UserRepository(session)
        user = await repo.get_by_email("s13@example.com")
        assert user is not None
        user_id = user.id
        await repo.set_active(user, is_active=False)
        await session.commit()

    assert user_id is not None
    token = create_access_token(subject=user_id)

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Inactive account"


# ---------------------------------------------------------------------------
# Scenario 14: Re-register same email (idempotency check)
# ---------------------------------------------------------------------------

async def test_re_register_same_email(client: AsyncClient) -> None:
    payload = {"email": "s14@example.com", "full_name": "Rereg User", "password": "securepassword123"}
    resp1 = await client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 400
    assert resp2.json()["detail"] == "Email already registered"


# ---------------------------------------------------------------------------
# Scenario 15: Password is hashed, not stored in plaintext
# ---------------------------------------------------------------------------

async def test_password_is_hashed(
    client: AsyncClient,
    sessionmaker_: async_sessionmaker[AsyncSession],
) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "s15@example.com", "full_name": "Hashed User", "password": "securepassword123"},
    )

    hashed: str | None = None
    async with sessionmaker_() as session:
        repo = UserRepository(session)
        user = await repo.get_by_email("s15@example.com")
        assert user is not None
        hashed = user.hashed_password

    assert hashed is not None
    assert hashed != "securepassword123"
    assert hashed.startswith("$2b$")
