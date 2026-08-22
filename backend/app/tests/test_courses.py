"""Course endpoint tests — Phase 6A.

Covers the five thin handlers on ``/api/v1/courses`` plus their
service-level guarantees:

  #1  List empty for a fresh user → 200, items == []
  #2  Create a course → 201, response body matches payload
  #3  Create with a duplicate name (same owner) → 409
  #4  Create with whitespace-only name → 422
  #5  Create with extra fields → 422 (extra="forbid")
  #6  List after creating two courses → both present
  #7  Get a course owned by the caller → 200, body matches
  #8  Get a course owned by a different user → 404
  #9  Get a non-existent UUID → 404
  #10 PATCH a course (name + code + description) → 200, fields updated
  #11 PATCH keeping the same name → 200, no 409
  #12 PATCH renaming to a colliding name → 409
  #13 PATCH with extra fields → 422
  #14 DELETE a course → 204
  #15 DELETE another user's course → 404
  #16 No auth header → 401 on list / get / post
  #17 Persistence: after delete, repo.get_by_id returns None
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from httpx import AsyncClient
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession


# ---------- helpers (mirrors test_documents.py) ----------


async def _register_and_login(
    client: AsyncClient,
    *,
    email: str,
    password: str = "S3cur3P@ss!",
    full_name: str = "Test User",
) -> str:
    """Register a fresh account and return a bearer token."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert reg.status_code == 201, reg.text
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _auth(token: str) -> dict[str, Any]:
    return {"headers": {"Authorization": f"Bearer {token}"}}


def _payload(
    *,
    name: str = "Signals & Systems",
    code: str | None = "ECE 201",
    description: str | None = "An intro to continuous- and discrete-time signals.",
) -> dict[str, Any]:
    """Return a minimal valid course payload."""
    out: dict[str, Any] = {"name": name}
    if code is not None:
        out["code"] = code
    if description is not None:
        out["description"] = description
    return out


# ---------- tests ----------


class TestListAndCreate:
    """Scenarios #1–#3: listing and create-validation paths."""

    async def test_list_empty_for_fresh_user(self, client: AsyncClient) -> None:
        """#1 — A user with no courses receives an empty list."""
        token = await _register_and_login(client, email="list1@example.com")
        resp = await client.get("/api/v1/courses", **_auth(token))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body == {"items": []}

    async def test_create_course_returns_201(self, client: AsyncClient) -> None:
        """#2 — Creating a valid course returns 201 with the course body."""
        token = await _register_and_login(client, email="create2@example.com")
        resp = await client.post(
            "/api/v1/courses",
            json=_payload(name="Linear Algebra"),
            **_auth(token),
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["name"] == "Linear Algebra"
        assert body["code"] == "ECE 201"
        assert body["description"].startswith("An intro")
        UUID(body["id"])  # parseable
        UUID(body["owner_id"])  # parseable
        assert "created_at" in body
        assert "updated_at" in body

    async def test_create_with_optional_fields(self, client: AsyncClient) -> None:
        """Create without code/description stores them as null."""
        token = await _register_and_login(client, email="opt@example.com")
        resp = await client.post(
            "/api/v1/courses",
            json={"name": "Bare Course"},
            **_auth(token),
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["name"] == "Bare Course"
        assert body["code"] is None
        assert body["description"] is None

    async def test_duplicate_name_returns_409(self, client: AsyncClient) -> None:
        """#3 — Same owner cannot create two courses with the same name."""
        token = await _register_and_login(client, email="dup@example.com")
        first = await client.post(
            "/api/v1/courses",
            json=_payload(name="Same Name"),
            **_auth(token),
        )
        assert first.status_code == 201, first.text

        second = await client.post(
            "/api/v1/courses",
            json=_payload(name="Same Name"),
            **_auth(token),
        )
        assert second.status_code == 409, second.text
        # Public message must name the offending course.
        assert "Same Name" in second.json()["detail"]

    async def test_duplicate_name_different_owner_allowed(
        self, client: AsyncClient
    ) -> None:
        """#3b — Two different users CAN each have a course of the same name."""
        token_a = await _register_and_login(client, email="userA@example.com")
        token_b = await _register_and_login(client, email="userB@example.com")

        r_a = await client.post(
            "/api/v1/courses",
            json=_payload(name="Shared Name"),
            **_auth(token_a),
        )
        r_b = await client.post(
            "/api/v1/courses",
            json=_payload(name="Shared Name"),
            **_auth(token_b),
        )
        assert r_a.status_code == 201, r_a.text
        assert r_b.status_code == 201, r_b.text
        assert r_a.json()["owner_id"] != r_b.json()["owner_id"]


class TestCreateValidation:
    """Scenarios #4–#5: Pydantic-level validation on POST."""

    async def test_whitespace_name_returns_422(self, client: AsyncClient) -> None:
        """#4 — A whitespace-only name is rejected by the field validator."""
        token = await _register_and_login(client, email="ws@example.com")
        resp = await client.post(
            "/api/v1/courses",
            json={"name": "   "},
            **_auth(token),
        )
        assert resp.status_code == 422, resp.text

    async def test_empty_name_returns_422(self, client: AsyncClient) -> None:
        """min_length=1 catches an empty string before the validator runs."""
        token = await _register_and_login(client, email="empty@example.com")
        resp = await client.post(
            "/api/v1/courses",
            json={"name": ""},
            **_auth(token),
        )
        assert resp.status_code == 422, resp.text

    async def test_extra_fields_rejected(self, client: AsyncClient) -> None:
        """#5 — extra="forbid" rejects unknown fields, including owner_id."""
        token = await _register_and_login(client, email="extra@example.com")
        resp = await client.post(
            "/api/v1/courses",
            json={
                "name": "Sneaky",
                # `owner_id` is forbidden — must come from the bearer token.
                "owner_id": "00000000-0000-0000-0000-000000000000",
                "rogue": "nope",
            },
            **_auth(token),
        )
        assert resp.status_code == 422, resp.text


class TestListAfterCreate:
    """Scenario #6 — listing reflects newly-created courses."""

    async def test_list_includes_created_courses(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, email="lister@example.com")
        for n in ("Course A", "Course B"):
            r = await client.post(
                "/api/v1/courses",
                json={"name": n},
                **_auth(token),
            )
            assert r.status_code == 201, r.text

        resp = await client.get("/api/v1/courses", **_auth(token))
        assert resp.status_code == 200, resp.text
        names = {c["name"] for c in resp.json()["items"]}
        assert names == {"Course A", "Course B"}


class TestGet:
    """Scenarios #7–#9: ownership-scoped single-course fetch."""

    async def test_get_own_course(self, client: AsyncClient) -> None:
        """#7 — GET on a course the caller owns returns 200 + body."""
        token = await _register_and_login(client, email="get7@example.com")
        create = await client.post(
            "/api/v1/courses",
            json=_payload(name="My Course"),
            **_auth(token),
        )
        course_id = create.json()["id"]

        resp = await client.get(f"/api/v1/courses/{course_id}", **_auth(token))
        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == course_id
        assert resp.json()["name"] == "My Course"

    async def test_get_another_users_course_returns_404(
        self, client: AsyncClient
    ) -> None:
        """#8 — Owner boundary: a foreign course id returns 404 (not 403)."""
        token_a = await _register_and_login(client, email="owner8@example.com")
        token_b = await _register_and_login(client, email="thief8@example.com")

        create = await client.post(
            "/api/v1/courses",
            json=_payload(name="Private"),
            **_auth(token_a),
        )
        course_id = create.json()["id"]

        resp = await client.get(f"/api/v1/courses/{course_id}", **_auth(token_b))
        assert resp.status_code == 404, resp.text

    async def test_get_nonexistent_returns_404(self, client: AsyncClient) -> None:
        """#9 — A random UUID that does not exist returns 404."""
        token = await _register_and_login(client, email="get9@example.com")
        bogus = "00000000-0000-0000-0000-000000000000"
        resp = await client.get(f"/api/v1/courses/{bogus}", **_auth(token))
        assert resp.status_code == 404, resp.text


class TestPatch:
    """Scenarios #10–#13: partial update + collision + extra=forbid."""

    async def test_patch_updates_fields(self, client: AsyncClient) -> None:
        """#10 — PATCH with name + code + description updates all three."""
        token = await _register_and_login(client, email="patch10@example.com")
        create = await client.post(
            "/api/v1/courses",
            json=_payload(name="Old Name", code="OLD 101"),
            **_auth(token),
        )
        course_id = create.json()["id"]

        resp = await client.patch(
            f"/api/v1/courses/{course_id}",
            json={"name": "New Name", "code": "NEW 202", "description": "Updated."},
            **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["name"] == "New Name"
        assert body["code"] == "NEW 202"
        assert body["description"] == "Updated."

    async def test_patch_keep_same_name_ok(self, client: AsyncClient) -> None:
        """#11 — PATCHing the same name back to itself is NOT a collision."""
        token = await _register_and_login(client, email="patch11@example.com")
        create = await client.post(
            "/api/v1/courses",
            json=_payload(name="Stable Name"),
            **_auth(token),
        )
        course_id = create.json()["id"]

        resp = await client.patch(
            f"/api/v1/courses/{course_id}",
            json={"name": "Stable Name"},
            **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["name"] == "Stable Name"

    async def test_patch_collision_returns_409(self, client: AsyncClient) -> None:
        """#12 — Renaming into another of the owner's courses → 409."""
        token = await _register_and_login(client, email="patch12@example.com")
        await client.post(
            "/api/v1/courses",
            json={"name": "First"},
            **_auth(token),
        )
        second = await client.post(
            "/api/v1/courses",
            json={"name": "Second"},
            **_auth(token),
        )
        second_id = second.json()["id"]

        resp = await client.patch(
            f"/api/v1/courses/{second_id}",
            json={"name": "First"},
            **_auth(token),
        )
        assert resp.status_code == 409, resp.text
        assert "First" in resp.json()["detail"]

    async def test_patch_extra_field_rejected(self, client: AsyncClient) -> None:
        """#13 — extra="forbid" on the update schema rejects rogue fields."""
        token = await _register_and_login(client, email="patch13@example.com")
        create = await client.post(
            "/api/v1/courses",
            json={"name": "PatchMe"},
            **_auth(token),
        )
        course_id = create.json()["id"]

        resp = await client.patch(
            f"/api/v1/courses/{course_id}",
            json={"name": "PatchMe", "owner_id": "00000000-0000-0000-0000-000000000000"},
            **_auth(token),
        )
        assert resp.status_code == 422, resp.text

    async def test_patch_unknown_course_returns_404(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, email="patch14@example.com")
        bogus = "00000000-0000-0000-0000-000000000000"
        resp = await client.patch(
            f"/api/v1/courses/{bogus}",
            json={"name": "Anything"},
            **_auth(token),
        )
        assert resp.status_code == 404, resp.text


class TestDelete:
    """Scenarios #14–#17: delete + ownership + persistence."""

    async def test_delete_own_course(self, client: AsyncClient) -> None:
        """#14 — DELETE on a course the caller owns returns 204."""
        token = await _register_and_login(client, email="del14@example.com")
        create = await client.post(
            "/api/v1/courses",
            json={"name": "Doomed"},
            **_auth(token),
        )
        course_id = create.json()["id"]

        resp = await client.delete(
            f"/api/v1/courses/{course_id}", **_auth(token)
        )
        assert resp.status_code == 204, resp.text

    async def test_delete_another_users_course_returns_404(
        self, client: AsyncClient
    ) -> None:
        """#15 — Cross-user delete returns 404."""
        token_a = await _register_and_login(client, email="owner15@example.com")
        token_b = await _register_and_login(client, email="thief15@example.com")

        create = await client.post(
            "/api/v1/courses",
            json={"name": "Not Yours"},
            **_auth(token_a),
        )
        course_id = create.json()["id"]

        resp = await client.delete(
            f"/api/v1/courses/{course_id}", **_auth(token_b)
        )
        assert resp.status_code == 404, resp.text

    async def test_delete_nonexistent_returns_404(
        self, client: AsyncClient
    ) -> None:
        token = await _register_and_login(client, email="del16@example.com")
        bogus = "00000000-0000-0000-0000-000000000000"
        resp = await client.delete(f"/api/v1/courses/{bogus}", **_auth(token))
        assert resp.status_code == 404, resp.text

    async def test_db_row_removed_after_delete(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """#17 — After DELETE, a fresh repo lookup returns None."""
        from app.db.repositories.course_repository import CourseRepository

        token = await _register_and_login(client, email="db17@example.com")
        create = await client.post(
            "/api/v1/courses",
            json={"name": "Vanish"},
            **_auth(token),
        )
        course_id = UUID(create.json()["id"])

        resp = await client.delete(
            f"/api/v1/courses/{course_id}", **_auth(token)
        )
        assert resp.status_code == 204

        repo = CourseRepository(db_session)
        # Different identity map on db_session vs. the request's session,
        # so this is a real read against the engine.
        result = await repo.get_by_id(course_id)
        assert result is None


class TestAuthGuard:
    """Scenario #16 — endpoints reject missing auth with 401."""

    async def test_list_without_auth_returns_401(
        self, client: AsyncClient
    ) -> None:
        resp = await client.get("/api/v1/courses")
        assert resp.status_code == 401

    async def test_create_without_auth_returns_401(
        self, client: AsyncClient
    ) -> None:
        resp = await client.post(
            "/api/v1/courses", json={"name": "anon"}
        )
        assert resp.status_code == 401

    async def test_get_without_auth_returns_401(
        self, client: AsyncClient
    ) -> None:
        resp = await client.get("/api/v1/courses/00000000-0000-0000-0000-000000000000")
        # Auth guard fires first → 401; UUID parse can't even reach the route.
        assert resp.status_code == 401

    async def test_delete_without_auth_returns_401(
        self, client: AsyncClient
    ) -> None:
        resp = await client.delete(
            "/api/v1/courses/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 401
