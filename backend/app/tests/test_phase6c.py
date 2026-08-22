"""Phase 6C — Document Type and Metadata tests.

Covers the end-to-end behaviour introduced by Phase 6C:

Document type
  #1  Create document with valid document type
  #2  Create document without document type (defaults to OTHER)
  #3  Invalid document type rejected at the wire (422)
  #4  Document response returns document_type

Metadata
  #5  Create with valid metadata
  #6  Read metadata via GET
  #7  Update metadata (PATCH)
  #8  Explicit metadata null behaviour (PATCH document_metadata=None clears it)
  #9  Omitted metadata during PATCH preserves existing value
  #10 Invalid metadata rejected (422)
  #11 Extra metadata fields rejected if schema is strict (422)
  #12 Tags validation: empty dropped, duplicates deduped, length capped

Filtering
  #13 Filter documents by document_type
  #14 No filter preserves existing behaviour
  #15 Combine course_id + document_type
  #16 Cross-user filtering remains isolated

Ownership / auth
  #17 User cannot modify another user's document metadata (404)
  #18 User cannot modify another user's document type (404)
  #19 Existing Course ownership rules remain enforced

Backward compatibility
  #20 Existing document creation without new fields still works
  #21 Legacy rows with NULL/default values remain retrievable
  #22 Existing Phase 6B course assignment still works

Authentication
  #23 Unauthenticated requests remain rejected (401)
"""
from __future__ import annotations

import io
from typing import Any
from uuid import UUID, uuid4

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from httpx import AsyncClient
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession


# ---------- file payloads (mirror test_documents.py) ----------

_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"xref\n0 2\n0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"trailer\n<< /Size 2 /Root 1 0 R >>\n"
    b"startxref\n9\n%%EOF"
)


# ---------- helpers ----------


async def _register_and_login(
    client: AsyncClient,
    *,
    email: str,
    password: str = "S3cur3P@ss!",
    full_name: str = "Test User",
) -> str:
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


async def _upload_pdf(
    client: AsyncClient,
    token: str,
    *,
    filename: str = "notes.pdf",
    document_type: str | None = None,
    document_metadata: str | None = None,
) -> UUID:
    """Upload a minimal PDF, optionally with document_type and document_metadata.

    ``document_metadata`` is a JSON-encoded string (the wire shape).
    """
    data: dict[str, Any] = {}
    if document_type is not None:
        data["document_type"] = document_type
    if document_metadata is not None:
        data["document_metadata"] = document_metadata

    resp = await client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                filename,
                io.BytesIO(_PDF_BYTES),
                "application/pdf",
            ),
        },
        data=data,
        **_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return UUID(resp.json()["id"])


async def _create_course(
    client: AsyncClient,
    token: str,
    *,
    name: str,
) -> UUID:
    resp = await client.post(
        "/api/v1/courses",
        json={"name": name},
        **_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return UUID(resp.json()["id"])


# ============================================================
#  Document type
# ============================================================


class TestDocumentType:
    """Scenarios #1–#4: document_type wire contract."""

    async def test_create_with_valid_document_type(self, client: AsyncClient) -> None:
        """#1 — Upload with document_type=lecture_notes persists it."""
        token = await _register_and_login(client, email="dt1@example.com")
        doc_id = await _upload_pdf(
            client, token, document_type="lecture_notes"
        )
        resp = await client.get(
            f"/api/v1/documents/{doc_id}", **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["document_type"] == "lecture_notes"

    async def test_create_without_document_type_defaults_to_other(
        self, client: AsyncClient
    ) -> None:
        """#2 — Omitting document_type yields OTHER (the deliberate default)."""
        token = await _register_and_login(client, email="dt2@example.com")
        doc_id = await _upload_pdf(client, token)
        resp = await client.get(
            f"/api/v1/documents/{doc_id}", **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["document_type"] == "other"

    async def test_invalid_document_type_rejected(self, client: AsyncClient) -> None:
        """#3 — A typo / unknown enum value is rejected at the wire (422)."""
        token = await _register_and_login(client, email="dt3@example.com")
        resp = await client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "bad.pdf",
                    io.BytesIO(_PDF_BYTES),
                    "application/pdf",
                ),
            },
            data={"document_type": "random_typo"},
            **_auth(token),
        )
        assert resp.status_code == 422, resp.text

    async def test_response_includes_document_type(self, client: AsyncClient) -> None:
        """#4 — DocumentResponse.model_validate exposes document_type."""
        token = await _register_and_login(client, email="dt4@example.com")
        doc_id = await _upload_pdf(
            client, token, document_type="textbook"
        )
        resp = await client.get(
            f"/api/v1/documents/{doc_id}", **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert "document_type" in resp.json()
        assert resp.json()["document_type"] == "textbook"


# ============================================================
#  Metadata
# ============================================================


class TestMetadata:
    """Scenarios #5–#12: metadata wire contract and validation."""

    async def test_create_with_valid_metadata(self, client: AsyncClient) -> None:
        """#5 — Upload with metadata persists it."""
        token = await _register_and_login(client, email="m5@example.com")
        doc_id = await _upload_pdf(
            client,
            token,
            document_metadata=(
                '{"author":"Dr. Smith","subject":"Signals",'
                '"semester":"Fall","academic_year":"2025",'
                '"tags":["midterm","chapter-3"]}'
            ),
        )
        resp = await client.get(
            f"/api/v1/documents/{doc_id}", **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        md = resp.json()["document_metadata"]
        assert md["author"] == "Dr. Smith"
        assert md["subject"] == "Signals"
        assert md["semester"] == "Fall"
        assert md["academic_year"] == "2025"
        assert md["tags"] == ["midterm", "chapter-3"]

    async def test_read_metadata(self, client: AsyncClient) -> None:
        """#6 — GET returns the metadata that was set on create."""
        token = await _register_and_login(client, email="m6@example.com")
        doc_id = await _upload_pdf(
            client,
            token,
            document_metadata='{"author":"Anon","tags":["x"]}',
        )
        resp = await client.get(
            f"/api/v1/documents/{doc_id}", **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["document_metadata"]["author"] == "Anon"
        assert resp.json()["document_metadata"]["tags"] == ["x"]

    async def test_update_metadata(self, client: AsyncClient) -> None:
        """#7 — PATCH document_metadata=<new> replaces the field."""
        token = await _register_and_login(client, email="m7@example.com")
        doc_id = await _upload_pdf(
            client,
            token,
            document_metadata='{"author":"Original"}',
        )
        resp = await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"document_metadata": {"author": "Updated"}},
            **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["document_metadata"]["author"] == "Updated"

    async def test_explicit_null_clears_metadata(self, client: AsyncClient) -> None:
        """#8 — PATCH document_metadata=None clears it (omit-vs-null semantics)."""
        token = await _register_and_login(client, email="m8@example.com")
        doc_id = await _upload_pdf(
            client,
            token,
            document_metadata='{"author":"ToClear"}',
        )
        resp = await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"document_metadata": None},
            **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["document_metadata"] is None

    async def test_omitted_metadata_preserves_existing_value(
        self, client: AsyncClient
    ) -> None:
        """#9 — PATCH without document_metadata leaves it untouched."""
        token = await _register_and_login(client, email="m9@example.com")
        doc_id = await _upload_pdf(
            client,
            token,
            document_metadata='{"author":"KeepMe","tags":["important"]}',
        )
        # PATCH an unrelated field
        resp = await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"document_type": "textbook"},
            **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        md = resp.json()["document_metadata"]
        assert md["author"] == "KeepMe"
        assert md["tags"] == ["important"]

    async def test_invalid_metadata_rejected(self, client: AsyncClient) -> None:
        """#10 — Malformed JSON in document_metadata returns 422."""
        token = await _register_and_login(client, email="m10@example.com")
        resp = await client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "broken.pdf",
                    io.BytesIO(_PDF_BYTES),
                    "application/pdf",
                ),
            },
            data={"document_metadata": "{not-json}"},
            **_auth(token),
        )
        assert resp.status_code == 422, resp.text

    async def test_extra_metadata_field_rejected(self, client: AsyncClient) -> None:
        """#11 — Unknown metadata fields are rejected by extra='forbid'."""
        token = await _register_and_login(client, email="m11@example.com")
        resp = await client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "extrafield.pdf",
                    io.BytesIO(_PDF_BYTES),
                    "application/pdf",
                ),
            },
            data={"document_metadata": '{"author":"x","rogue":"y"}'},
            **_auth(token),
        )
        assert resp.status_code == 422, resp.text

    async def test_tags_normalised(self, client: AsyncClient) -> None:
        """#12 — Tags: empties dropped, duplicates deduped (case-insensitive)."""
        token = await _register_and_login(client, email="m12@example.com")
        doc_id = await _upload_pdf(
            client,
            token,
            document_metadata=(
                '{"tags":["  A  ","a","B","","b",'
                '"   ","c","C","c"]}'
            ),
        )
        resp = await client.get(
            f"/api/v1/documents/{doc_id}", **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        tags = resp.json()["document_metadata"]["tags"]
        # Empty tags dropped, duplicates collapsed (case-insensitive),
        # order preserved by first occurrence.
        assert tags == ["A", "B", "c"]


# ============================================================
#  Filtering
# ============================================================


class TestFiltering:
    """Scenarios #13–#16: document_type filter on GET /documents."""

    async def test_filter_by_document_type(self, client: AsyncClient) -> None:
        """#13 — ?document_type=<member> returns only matching docs."""
        token = await _register_and_login(client, email="f13@example.com")
        lecture = await _upload_pdf(
            client, token, filename="lec.pdf", document_type="lecture_notes"
        )
        text = await _upload_pdf(
            client, token, filename="txt.pdf", document_type="textbook"
        )
        # Another lecture_notes to confirm we get more than one
        lecture2 = await _upload_pdf(
            client, token, filename="lec2.pdf", document_type="lecture_notes"
        )

        resp = await client.get(
            "/api/v1/documents?document_type=lecture_notes",
            **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        ids = {UUID(item["id"]) for item in resp.json()}
        assert lecture in ids
        assert lecture2 in ids
        assert text not in ids

    async def test_no_filter_returns_all(self, client: AsyncClient) -> None:
        """#14 — No document_type filter preserves legacy behaviour."""
        token = await _register_and_login(client, email="f14@example.com")
        await _upload_pdf(
            client, token, filename="a.pdf", document_type="lecture_notes"
        )
        await _upload_pdf(
            client, token, filename="b.pdf", document_type="textbook"
        )
        await _upload_pdf(client, token, filename="c.pdf")  # OTHER

        resp = await client.get("/api/v1/documents", **_auth(token))
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) == 3

    async def test_combine_course_id_and_document_type(
        self, client: AsyncClient
    ) -> None:
        """#15 — ?course_id=...&document_type=... returns intersection."""
        token = await _register_and_login(client, email="f15@example.com")
        course_id = await _create_course(client, token, name="Combine")

        # Three docs; two lectures and one textbook; assign them all
        lec_a = await _upload_pdf(
            client, token, filename="la.pdf", document_type="lecture_notes"
        )
        lec_b = await _upload_pdf(
            client, token, filename="lb.pdf", document_type="lecture_notes"
        )
        text = await _upload_pdf(
            client, token, filename="t.pdf", document_type="textbook"
        )
        loose = await _upload_pdf(
            client, token, filename="x.pdf", document_type="lecture_notes"
        )

        for doc_id in (lec_a, lec_b, text):
            r = await client.patch(
                f"/api/v1/documents/{doc_id}",
                json={"course_id": str(course_id)},
                **_auth(token),
            )
            assert r.status_code == 200, r.text

        resp = await client.get(
            f"/api/v1/documents?course_id={course_id}"
            f"&document_type=lecture_notes",
            **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        ids = {UUID(item["id"]) for item in resp.json()}
        assert ids == {lec_a, lec_b}
        assert text not in ids
        assert loose not in ids

    async def test_cross_user_filter_does_not_leak(self, client: AsyncClient) -> None:
        """#16 — User B's ?document_type=... never sees User A's docs."""
        token_a = await _register_and_login(client, email="fxa16@example.com")
        token_b = await _register_and_login(client, email="fxb16@example.com")

        await _upload_pdf(
            client, token_a, filename="a.pdf", document_type="lecture_notes"
        )
        await _upload_pdf(
            client, token_b, filename="b.pdf", document_type="lecture_notes"
        )

        resp = await client.get(
            "/api/v1/documents?document_type=lecture_notes",
            **_auth(token_b),
        )
        assert resp.status_code == 200, resp.text
        # Only User B's single lecture_notes
        assert len(resp.json()) == 1


# ============================================================
#  Ownership / cross-user
# ============================================================


class TestOwnership:
    """Scenarios #17–#19: cross-user mutation and Course rules."""

    async def test_cannot_modify_another_users_metadata(
        self, client: AsyncClient
    ) -> None:
        """#17 — User B PATCHing User A's metadata returns 404."""
        token_a = await _register_and_login(client, email="o17a@example.com")
        token_b = await _register_and_login(client, email="o17b@example.com")

        doc_id = await _upload_pdf(
            client, token_a,
            document_metadata='{"author":"Owner A"}',
        )

        resp = await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"document_metadata": {"author": "Hijack"}},
            **_auth(token_b),
        )
        assert resp.status_code == 404, resp.text

        # Confirm the metadata is unchanged
        check = await client.get(
            f"/api/v1/documents/{doc_id}", **_auth(token_a),
        )
        assert check.json()["document_metadata"]["author"] == "Owner A"

    async def test_cannot_modify_another_users_document_type(
        self, client: AsyncClient
    ) -> None:
        """#18 — User B PATCHing User A's document_type returns 404."""
        token_a = await _register_and_login(client, email="o18a@example.com")
        token_b = await _register_and_login(client, email="o18b@example.com")

        doc_id = await _upload_pdf(
            client, token_a, document_type="lecture_notes"
        )

        resp = await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"document_type": "textbook"},
            **_auth(token_b),
        )
        assert resp.status_code == 404, resp.text

        check = await client.get(
            f"/api/v1/documents/{doc_id}", **_auth(token_a),
        )
        assert check.json()["document_type"] == "lecture_notes"

    async def test_course_ownership_rule_still_enforced(
        self, client: AsyncClient
    ) -> None:
        """#19 — Phase 6B course ownership guard is unchanged."""
        token_a = await _register_and_login(client, email="o19a@example.com")
        token_b = await _register_and_login(client, email="o19b@example.com")

        course_a = await _create_course(client, token_a, name="A-Owned")
        doc_id = await _upload_pdf(client, token_b)

        resp = await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={
                "course_id": str(course_a),
                "document_type": "lecture_notes",
            },
            **_auth(token_b),
        )
        assert resp.status_code == 404, resp.text


# ============================================================
#  Backward compatibility
# ============================================================


class TestBackwardCompat:
    """Scenarios #20–#22: pre-Phase-6C behaviour remains valid."""

    async def test_existing_create_without_new_fields(
        self, client: AsyncClient
    ) -> None:
        """#20 — A plain upload (no new fields) still works."""
        token = await _register_and_login(client, email="b20@example.com")
        resp = await client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "plain.pdf",
                    io.BytesIO(_PDF_BYTES),
                    "application/pdf",
                ),
            },
            **_auth(token),
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["document_type"] == "other"
        assert body["document_metadata"] is None
        assert body["course_id"] is None

    async def test_legacy_row_with_nulls_retrievable(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """#21 — A row with document_type=NULL and metadata=NULL reads back fine."""
        token = await _register_and_login(client, email="b21@example.com")
        from sqlalchemy import select

        from app.db.models.user import User

        result = await db_session.execute(
            select(User).where(User.email == "b21@example.com"),
        )
        user = result.scalar_one()
        db_session.expunge(user)

        from app.db.models.document import Document

        legacy = Document(
            owner_id=user.id,
            filename="legacy.pdf",
            original_filename="legacy.pdf",
            file_type="pdf",
            file_size=128,
            storage_path="legacy/legacy.pdf",
            upload_status="ready",
            course_id=None,
            document_type=None,  # pre-Phase-6C rows
            document_metadata=None,
        )
        db_session.add(legacy)
        await db_session.commit()
        await db_session.refresh(legacy)

        # Read it back through the API
        resp = await client.get(
            f"/api/v1/documents/{legacy.id}", **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["document_type"] is None
        assert resp.json()["document_metadata"] is None

    async def test_phase6b_course_assignment_still_works(
        self, client: AsyncClient
    ) -> None:
        """#22 — Phase 6B course_id assignment still works alongside new fields."""
        token = await _register_and_login(client, email="b22@example.com")
        course_id = await _create_course(client, token, name="Coexist")
        doc_id = await _upload_pdf(client, token, document_type="lecture_notes")

        resp = await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"course_id": str(course_id)},
            **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["course_id"] == str(course_id)
        # New fields survive the course-only PATCH (omit-vs-null)
        assert body["document_type"] == "lecture_notes"


# ============================================================
#  Authentication
# ============================================================


class TestAuthGuards:
    """Scenario #23 — unauthenticated requests are still 401."""

    async def test_upload_without_auth_returns_401(
        self, client: AsyncClient
    ) -> None:
        resp = await client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "noauth.pdf",
                    io.BytesIO(_PDF_BYTES),
                    "application/pdf",
                ),
            },
            data={"document_type": "lecture_notes"},
        )
        assert resp.status_code == 401, resp.text

    async def test_list_with_document_type_without_auth_returns_401(
        self, client: AsyncClient
    ) -> None:
        resp = await client.get(
            "/api/v1/documents?document_type=lecture_notes"
        )
        assert resp.status_code == 401, resp.text

    async def test_patch_document_type_without_auth_returns_401(
        self, client: AsyncClient
    ) -> None:
        token = await _register_and_login(client, email="auth23@example.com")
        doc_id = await _upload_pdf(client, token)

        resp = await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"document_type": "textbook"},
        )
        assert resp.status_code == 401, resp.text
