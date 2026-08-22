"""Phase 6B — Course ↔ Document / ChatSession integration tests.

Covers the end-to-end behaviour introduced by Phase 6B:

Document ↔ Course
  #1  Create a document without a course (backward compatible)
  #2  Assign a document to one of the caller's courses (PATCH)
  #3  Change a document's course
  #4  Remove a document from a course (course_id=null)
  #5  Assign a document to another user's course → 404
  #6  Filter documents by course_id (GET /documents?course_id=...)
  #7  Cross-user course_id filter does NOT leak foreign docs
  #8  Existing document behaviour (no course) remains valid

ChatSession ↔ Course
  #9  Create a session without a course (backward compatible)
  #10 Create a session attached to one of the caller's courses
  #11 Change a session's course (PATCH)
  #12 Remove a session from a course (course_id=null)
  #13 Assign a session to another user's course → 404
  #14 Filter sessions by course_id (GET /chat/sessions?course_id=...)
  #15 Cross-user course_id filter does NOT leak foreign sessions
  #16 Existing chat behaviour (no course) remains valid

Database / migration
  #17 Migration upgrade succeeds; documents / chat_sessions carry course_id
  #18 Existing rows remain valid with course_id=NULL

Auth
  #19 Unauthenticated document course operations rejected → 401
  #20 Unauthenticated chat course operations rejected → 401
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
    b"xref\n0 2\n0000000000 65535 f \n0000000009 00000 n \n"
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


async def _upload_pdf(
    client: AsyncClient,
    token: str,
    *,
    filename: str = "notes.pdf",
) -> UUID:
    resp = await client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                filename,
                io.BytesIO(_PDF_BYTES),
                "application/pdf",
            ),
        },
        **_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return UUID(resp.json()["id"])


# ============================================================
#  Document ↔ Course
# ============================================================


class TestDocumentCourse:
    """Scenarios #1–#8: document course assignment and filtering."""

    async def test_create_document_without_course(self, client: AsyncClient) -> None:
        """#1 — Documents without a course_id are still accepted."""
        token = await _register_and_login(client, email="doc_no_course@example.com")
        doc_id = await _upload_pdf(client, token)

        resp = await client.get(
            f"/api/v1/documents/{doc_id}", **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["course_id"] is None

    async def test_assign_document_to_own_course(self, client: AsyncClient) -> None:
        """#2 — PATCH course_id=<own> attaches the document."""
        token = await _register_and_login(
            client, email="doc_assign_own@example.com"
        )
        course_id = await _create_course(client, token, name="Signals")
        doc_id = await _upload_pdf(client, token)

        resp = await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"course_id": str(course_id)},
            **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["course_id"] == str(course_id)

    async def test_change_document_course(self, client: AsyncClient) -> None:
        """#3 — PATCHing a new course_id moves the document."""
        token = await _register_and_login(
            client, email="doc_change_course@example.com"
        )
        course_a = await _create_course(client, token, name="A")
        course_b = await _create_course(client, token, name="B")
        doc_id = await _upload_pdf(client, token)

        # Assign to A
        r1 = await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"course_id": str(course_a)},
            **_auth(token),
        )
        assert r1.status_code == 200, r1.text
        assert r1.json()["course_id"] == str(course_a)

        # Reassign to B
        r2 = await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"course_id": str(course_b)},
            **_auth(token),
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["course_id"] == str(course_b)

    async def test_remove_document_from_course(self, client: AsyncClient) -> None:
        """#4 — course_id=null unlinks the document."""
        token = await _register_and_login(
            client, email="doc_remove_course@example.com"
        )
        course_id = await _create_course(client, token, name="Temp")
        doc_id = await _upload_pdf(client, token)

        # Attach
        r1 = await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"course_id": str(course_id)},
            **_auth(token),
        )
        assert r1.status_code == 200, r1.text

        # Detach
        r2 = await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"course_id": None},
            **_auth(token),
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["course_id"] is None

    async def test_assign_document_to_another_users_course_rejected(
        self, client: AsyncClient
    ) -> None:
        """#5 — Cross-user course assignment is rejected with 404."""
        token_a = await _register_and_login(
            client, email="doc_a_other_course@example.com"
        )
        token_b = await _register_and_login(
            client, email="doc_b_other_course@example.com"
        )

        # User A creates a course
        course_a = await _create_course(client, token_a, name="A's Course")
        # User B uploads a document
        doc_id = await _upload_pdf(client, token_b)

        # User B tries to attach their document to User A's course → 404
        resp = await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"course_id": str(course_a)},
            **_auth(token_b),
        )
        assert resp.status_code == 404, resp.text

        # And the document must still be uncoursed
        check = await client.get(
            f"/api/v1/documents/{doc_id}", **_auth(token_b),
        )
        assert check.status_code == 200, check.text
        assert check.json()["course_id"] is None

    async def test_course_filtered_document_list(self, client: AsyncClient) -> None:
        """#6 — ?course_id= filters to that course's documents only."""
        token = await _register_and_login(
            client, email="doc_course_filter@example.com"
        )
        course_id = await _create_course(client, token, name="Filter")

        # Two docs attached, one not
        attached_a = await _upload_pdf(client, token, filename="a.pdf")
        attached_b = await _upload_pdf(client, token, filename="b.pdf")
        loose = await _upload_pdf(client, token, filename="c.pdf")

        for doc_id in (attached_a, attached_b):
            r = await client.patch(
                f"/api/v1/documents/{doc_id}",
                json={"course_id": str(course_id)},
                **_auth(token),
            )
            assert r.status_code == 200, r.text

        resp = await client.get(
            f"/api/v1/documents?course_id={course_id}", **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        returned = {UUID(item["id"]) for item in body}
        assert returned == {attached_a, attached_b}
        assert loose not in returned

    async def test_course_filter_does_not_leak_other_users_data(
        self, client: AsyncClient
    ) -> None:
        """#7 — A foreign course_id returns 404, never the owner's docs."""
        token_a = await _register_and_login(
            client, email="doc_leak_a@example.com"
        )
        token_b = await _register_and_login(
            client, email="doc_leak_b@example.com"
        )

        # User A creates a course and uploads docs
        course_a = await _create_course(client, token_a, name="Private")
        doc_a = await _upload_pdf(client, token_a, filename="a.pdf")
        await client.patch(
            f"/api/v1/documents/{doc_a}",
            json={"course_id": str(course_a)},
            **_auth(token_a),
        )

        # User B asks for documents under user A's course → 404
        resp = await client.get(
            f"/api/v1/documents?course_id={course_a}", **_auth(token_b),
        )
        assert resp.status_code == 404, resp.text

        # And user B's own list does not include the foreign doc
        own = await client.get(
            "/api/v1/documents", **_auth(token_b),
        )
        assert own.status_code == 200, own.text
        own_ids = {UUID(item["id"]) for item in own.json()}
        assert doc_a not in own_ids

    async def test_existing_document_behavior_remains_valid(
        self, client: AsyncClient
    ) -> None:
        """#8 — PATCH with no course_id leaves existing link untouched."""
        token = await _register_and_login(
            client, email="doc_untouched@example.com"
        )
        course_id = await _create_course(client, token, name="Stable")
        doc_id = await _upload_pdf(client, token)
        await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"course_id": str(course_id)},
            **_auth(token),
        )

        # PATCH an unrelated field with course_id omitted → course stays.
        # ``DocumentUpdate`` only allows course_id / file_type / upload_status,
        # so we patch ``file_type`` to a value that re-detects to "pdf".
        resp = await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"file_type": "pdf"},
            **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["course_id"] == str(course_id)


# ============================================================
#  ChatSession ↔ Course
# ============================================================


class TestChatSessionCourse:
    """Scenarios #9–#16: chat session course assignment and filtering."""

    async def test_create_session_without_course(self, client: AsyncClient) -> None:
        """#9 — Sessions without course_id are still accepted."""
        token = await _register_and_login(
            client, email="sess_no_course@example.com"
        )
        resp = await client.post(
            "/api/v1/chat/sessions",
            json={"title": "No course"},
            **_auth(token),
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["course_id"] is None

    async def test_create_session_with_own_course(self, client: AsyncClient) -> None:
        """#10 — POST with course_id=<own> attaches the session."""
        token = await _register_and_login(
            client, email="sess_with_course@example.com"
        )
        course_id = await _create_course(client, token, name="Course S")

        resp = await client.post(
            "/api/v1/chat/sessions",
            json={"title": "Attached", "course_id": str(course_id)},
            **_auth(token),
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["course_id"] == str(course_id)

    async def test_change_session_course(self, client: AsyncClient) -> None:
        """#11 — PATCH a new course_id moves the session."""
        token = await _register_and_login(
            client, email="sess_change_course@example.com"
        )
        course_a = await _create_course(client, token, name="CA")
        course_b = await _create_course(client, token, name="CB")

        # Create attached to A
        create = await client.post(
            "/api/v1/chat/sessions",
            json={"title": "C", "course_id": str(course_a)},
            **_auth(token),
        )
        assert create.status_code == 201, create.text
        session_id = create.json()["id"]

        # Reassign to B
        r = await client.patch(
            f"/api/v1/chat/sessions/{session_id}",
            json={"course_id": str(course_b)},
            **_auth(token),
        )
        assert r.status_code == 200, r.text
        assert r.json()["course_id"] == str(course_b)

    async def test_remove_session_from_course(self, client: AsyncClient) -> None:
        """#12 — PATCH course_id=null unlinks the session."""
        token = await _register_and_login(
            client, email="sess_remove_course@example.com"
        )
        course_id = await _create_course(client, token, name="ToUnlink")
        create = await client.post(
            "/api/v1/chat/sessions",
            json={"title": "Linked", "course_id": str(course_id)},
            **_auth(token),
        )
        assert create.status_code == 201, create.text
        session_id = create.json()["id"]

        r = await client.patch(
            f"/api/v1/chat/sessions/{session_id}",
            json={"course_id": None},
            **_auth(token),
        )
        assert r.status_code == 200, r.text
        assert r.json()["course_id"] is None

    async def test_assign_session_to_another_users_course_rejected(
        self, client: AsyncClient
    ) -> None:
        """#13 — Cross-user session course assignment is rejected with 404."""
        token_a = await _register_and_login(
            client, email="sess_a_other_course@example.com"
        )
        token_b = await _register_and_login(
            client, email="sess_b_other_course@example.com"
        )
        course_a = await _create_course(client, token_a, name="A's Course")

        # User B creates a session, then tries to attach to A's course
        create = await client.post(
            "/api/v1/chat/sessions",
            json={"title": "B's Session"},
            **_auth(token_b),
        )
        assert create.status_code == 201, create.text
        session_id = create.json()["id"]

        resp = await client.patch(
            f"/api/v1/chat/sessions/{session_id}",
            json={"course_id": str(course_a)},
            **_auth(token_b),
        )
        assert resp.status_code == 404, resp.text

        # Session must still be uncoursed
        check = await client.get(
            f"/api/v1/chat/sessions/{session_id}", **_auth(token_b),
        )
        assert check.status_code == 200, check.text
        assert check.json()["course_id"] is None

    async def test_course_filtered_session_list(self, client: AsyncClient) -> None:
        """#14 — ?course_id= filters to that course's sessions only."""
        token = await _register_and_login(
            client, email="sess_course_filter@example.com"
        )
        course_id = await _create_course(client, token, name="SFilter")

        # Two attached, one not
        attached_a = await client.post(
            "/api/v1/chat/sessions",
            json={"title": "A", "course_id": str(course_id)},
            **_auth(token),
        )
        assert attached_a.status_code == 201, attached_a.text
        attached_b = await client.post(
            "/api/v1/chat/sessions",
            json={"title": "B", "course_id": str(course_id)},
            **_auth(token),
        )
        assert attached_b.status_code == 201, attached_b.text
        loose = await client.post(
            "/api/v1/chat/sessions", json={"title": "C"}, **_auth(token),
        )
        assert loose.status_code == 201, loose.text

        resp = await client.get(
            f"/api/v1/chat/sessions?course_id={course_id}", **_auth(token),
        )
        assert resp.status_code == 200, resp.text
        returned = {item["id"] for item in resp.json()}
        assert returned == {attached_a.json()["id"], attached_b.json()["id"]}
        assert loose.json()["id"] not in returned

    async def test_course_filter_does_not_leak_other_users_sessions(
        self, client: AsyncClient
    ) -> None:
        """#15 — A foreign course_id returns 404, never the owner's sessions."""
        token_a = await _register_and_login(
            client, email="sess_leak_a@example.com"
        )
        token_b = await _register_and_login(
            client, email="sess_leak_b@example.com"
        )

        course_a = await _create_course(client, token_a, name="PrivateS")
        create = await client.post(
            "/api/v1/chat/sessions",
            json={"title": "A's", "course_id": str(course_a)},
            **_auth(token_a),
        )
        assert create.status_code == 201, create.text
        session_a_id = create.json()["id"]

        # User B asks for sessions under user A's course → 404
        resp = await client.get(
            f"/api/v1/chat/sessions?course_id={course_a}", **_auth(token_b),
        )
        assert resp.status_code == 404, resp.text

        # And user B's own list does not include the foreign session
        own = await client.get(
            "/api/v1/chat/sessions", **_auth(token_b),
        )
        assert own.status_code == 200, own.text
        own_ids = {item["id"] for item in own.json()}
        assert session_a_id not in own_ids

    async def test_existing_chat_behavior_remains_valid(
        self, client: AsyncClient
    ) -> None:
        """#16 — PATCH without course_id leaves the link untouched."""
        token = await _register_and_login(
            client, email="sess_untouched@example.com"
        )
        course_id = await _create_course(client, token, name="StableS")
        create = await client.post(
            "/api/v1/chat/sessions",
            json={"title": "Linked", "course_id": str(course_id)},
            **_auth(token),
        )
        assert create.status_code == 201, create.text
        session_id = create.json()["id"]

        r = await client.patch(
            f"/api/v1/chat/sessions/{session_id}",
            json={"title": "Renamed"},
            **_auth(token),
        )
        assert r.status_code == 200, r.text
        assert r.json()["title"] == "Renamed"
        assert r.json()["course_id"] == str(course_id)


# ============================================================
#  Database / migration
# ============================================================


class TestMigrationAndDatabase:
    """Scenarios #17–#18: schema and existing-row compatibility."""

    async def test_documents_table_has_course_id_column(
        self,
        engine,
    ) -> None:
        """#17 — After schema creation, documents.course_id is a nullable column."""
        from sqlalchemy import inspect

        async with engine.connect() as conn:
            cols = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_columns("documents"),
            )
        col_names = {c["name"] for c in cols}
        assert "course_id" in col_names
        # Nullable.
        course_id_col = next(c for c in cols if c["name"] == "course_id")
        assert course_id_col["nullable"] is True

    async def test_chat_sessions_table_has_course_id_column(
        self,
        engine,
    ) -> None:
        """#17b — chat_sessions.course_id is a nullable column too."""
        from sqlalchemy import inspect

        async with engine.connect() as conn:
            cols = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_columns("chat_sessions"),
            )
        col_names = {c["name"] for c in cols}
        assert "course_id" in col_names
        col = next(c for c in cols if c["name"] == "course_id")
        assert col["nullable"] is True

    async def test_existing_rows_compatible_with_null_course_id(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """#18 — Pre-Phase-6B documents / sessions (course_id=NULL) work fine."""
        from app.db.models.chat import ChatSession
        from app.db.models.document import Document
        from app.db.models.user import User

        token = await _register_and_login(
            client, email="legacy_rows@example.com"
        )

        # Look up the user we just created.
        from sqlalchemy import select

        result = await db_session.execute(
            select(User).where(User.email == "legacy_rows@example.com"),
        )
        user = result.scalar_one()
        # Detach — we won't be writing through this ORM instance, just
        # checking that the rows are still readable.
        db_session.expunge(user)

        # Pre-Phase-6B-style documents: course_id=NULL. The model allows it.
        doc = Document(
            owner_id=user.id,
            filename="legacy.pdf",
            original_filename="legacy.pdf",
            file_type="pdf",
            file_size=128,
            storage_path="legacy/legacy.pdf",
            upload_status="ready",
            course_id=None,
        )
        db_session.add(doc)
        sess = ChatSession(
            user_id=user.id,
            title="Legacy session",
            course_id=None,
        )
        db_session.add(sess)
        await db_session.commit()

        # Read them back to make sure NULL is a valid value on disk.
        reread_doc = await db_session.get(Document, doc.id)
        reread_sess = await db_session.get(ChatSession, sess.id)
        assert reread_doc is not None
        assert reread_doc.course_id is None
        assert reread_sess is not None
        assert reread_sess.course_id is None


# ============================================================
#  Auth
# ============================================================


class TestAuthGuards:
    """Scenarios #19–#20: unauthenticated requests are rejected."""

    async def test_unauthenticated_document_course_patch_rejected(
        self, client: AsyncClient
    ) -> None:
        token = await _register_and_login(
            client, email="doc_auth_guard@example.com"
        )
        doc_id = await _upload_pdf(client, token)
        course_id = await _create_course(client, token, name="AuthGuard")

        # No auth header
        resp = await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"course_id": str(course_id)},
        )
        assert resp.status_code == 401, resp.text

    async def test_unauthenticated_chat_course_create_rejected(
        self, client: AsyncClient
    ) -> None:
        token = await _register_and_login(
            client, email="chat_auth_guard@example.com"
        )
        course_id = await _create_course(client, token, name="ChatAuthGuard")

        resp = await client.post(
            "/api/v1/chat/sessions",
            json={"title": "NoAuth", "course_id": str(course_id)},
        )
        assert resp.status_code == 401, resp.text


# ============================================================
#  Cross-user course filtering (additional security check)
# ============================================================


class TestCrossUserFiltering:
    """A foreign course id must NEVER return another user's resources."""

    async def test_another_users_course_id_is_404_for_docs(
        self, client: AsyncClient
    ) -> None:
        token_a = await _register_and_login(
            client, email="xf_a_doc@example.com"
        )
        token_b = await _register_and_login(
            client, email="xf_b_doc@example.com"
        )
        course_a = await _create_course(client, token_a, name="X-A")

        # User B lists documents using User A's course id
        resp = await client.get(
            f"/api/v1/documents?course_id={course_a}", **_auth(token_b),
        )
        assert resp.status_code == 404, resp.text

    async def test_another_users_course_id_is_404_for_sessions(
        self, client: AsyncClient
    ) -> None:
        token_a = await _register_and_login(
            client, email="xf_a_sess@example.com"
        )
        token_b = await _register_and_login(
            client, email="xf_b_sess@example.com"
        )
        course_a = await _create_course(client, token_a, name="X-B")

        resp = await client.get(
            f"/api/v1/chat/sessions?course_id={course_a}", **_auth(token_b),
        )
        assert resp.status_code == 404, resp.text

    async def test_random_uuid_for_course_id_returns_404(
        self, client: AsyncClient
    ) -> None:
        """#18b — A UUID that does not exist returns 404 for both endpoints."""
        token = await _register_and_login(
            client, email="random_course_id@example.com"
        )
        bogus = uuid4()
        r1 = await client.get(
            f"/api/v1/documents?course_id={bogus}", **_auth(token),
        )
        assert r1.status_code == 404, r1.text
        r2 = await client.get(
            f"/api/v1/chat/sessions?course_id={bogus}", **_auth(token),
        )
        assert r2.status_code == 404, r2.text
