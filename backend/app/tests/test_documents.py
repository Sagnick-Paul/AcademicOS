"""Document management tests — Step 4.

Covers every scenario listed in the implementation brief:

  #1  Upload valid PDF → 201 + metadata
  #2  Upload valid PNG → 201
  #3  Upload unsupported extension (.exe) → 415
  #4  Real PDF with wrong Content-Type (image/jpeg) → 415
  #5  Zero-byte upload → 400
  #6  Oversized upload → 413
  #7  List documents (newest first) → 200, both present, correct order
  #8  Retrieve own document → 200, body matches
  #9  Retrieve another user's document → 404
  #10 Delete own document → 204
  #11 Delete another user's document → 404
  #12 File removed from disk after delete
  #13 DB row removed after delete
  +n  No auth header on upload → 401
"""
from __future__ import annotations

import io
from pathlib import Path
from uuid import UUID

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from httpx import AsyncClient

# ---------- constants — minimal valid file payloads ----------

_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"xref\n0 2\n0000000000 65535 f \n0000000009 00000 n \n"
    b"trailer\n<< /Size 2 /Root 1 0 R >>\n"
    b"startxref\n9\n%%EOF"
)

_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"          # PNG signature (8 bytes)
    b"\x00\x00\x00\rIHDR"         # IHDR chunk length + type
    b"\x00\x00\x00\x01"           # width  = 1
    b"\x00\x00\x00\x01"           # height = 1
    b"\x08\x02"                   # bit depth 8, color type RGB
    b"\x00\x00\x00"               # compression, filter, interlace
    b"\x90wS\xde"                 # CRC
    b"\x00\x00\x00\x0cIDATx\x9c"  # IDAT
    b"b\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"  # IEND
)

# A size just over the 50 MB cap (MAX_UPLOAD_SIZE_MB = 50 in default settings).
_MAX_MB = 50
_OVERSIZED_BYTES = b"X" * (_MAX_MB * 1024 * 1024 + 1)


# ---------- helpers ----------


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


def _pdf_upload(filename: str = "test.pdf") -> dict:
    """Return kwargs for an httpx multipart PDF upload."""
    return {
        "files": {"file": (filename, io.BytesIO(_PDF_BYTES), "application/pdf")},
    }


def _png_upload(filename: str = "test.png") -> dict:
    """Return kwargs for an httpx multipart PNG upload."""
    return {
        "files": {"file": (filename, io.BytesIO(_PNG_BYTES), "image/png")},
    }


def _auth(token: str) -> dict:
    return {"headers": {"Authorization": f"Bearer {token}"}}


# ---------- tests ----------


class TestUploadValidation:
    """Scenarios #1–6: file validation on POST /upload."""

    async def test_upload_valid_pdf(self, client: AsyncClient) -> None:
        """#1 — Upload a valid PDF; expect 201 with correct metadata."""
        token = await _register_and_login(client, email="pdf@example.com")
        resp = await client.post(
            "/api/v1/documents/upload", **_pdf_upload(), **_auth(token)
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["file_type"] == "pdf"
        assert body["original_filename"] == "test.pdf"
        assert body["file_size"] == len(_PDF_BYTES)
        # Structural sanity: UUID-parseable id and owner_id
        UUID(body["id"])
        UUID(body["owner_id"])

    async def test_upload_valid_png(self, client: AsyncClient) -> None:
        """#2 — Upload a valid PNG; expect 201."""
        token = await _register_and_login(client, email="png@example.com")
        resp = await client.post(
            "/api/v1/documents/upload", **_png_upload(), **_auth(token)
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["file_type"] == "png"

    async def test_upload_invalid_extension(self, client: AsyncClient) -> None:
        """#3 — .exe extension should be rejected with 415."""
        token = await _register_and_login(client, email="exe@example.com")
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("malware.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")},
            **_auth(token),
        )
        assert resp.status_code == 415, resp.text

    async def test_upload_mismatched_content_type(self, client: AsyncClient) -> None:
        """#4 — Real PDF bytes but declared as image/jpeg → 415."""
        token = await _register_and_login(client, email="mime@example.com")
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("spoof.pdf", io.BytesIO(_PDF_BYTES), "image/jpeg")},
            **_auth(token),
        )
        assert resp.status_code == 415, resp.text

    async def test_upload_empty_file(self, client: AsyncClient) -> None:
        """#5 — Zero-byte upload should return 400."""
        token = await _register_and_login(client, email="empty@example.com")
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
            **_auth(token),
        )
        assert resp.status_code == 400, resp.text

    async def test_upload_oversized_file(self, client: AsyncClient) -> None:
        """#6 — File exceeding 50 MB cap should return 413."""
        token = await _register_and_login(client, email="big@example.com")
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("huge.pdf", io.BytesIO(_OVERSIZED_BYTES), "application/pdf")},
            **_auth(token),
        )
        assert resp.status_code == 413, resp.text


class TestListAndFetch:
    """Scenarios #7–9: listing and single-doc retrieval."""

    async def test_list_documents_newest_first(self, client: AsyncClient) -> None:
        """#7 — Upload two docs; list should return both, newest first."""
        token = await _register_and_login(client, email="list@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        r1 = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("first.pdf", io.BytesIO(_PDF_BYTES), "application/pdf")},
            headers=headers,
        )
        assert r1.status_code == 201
        id_first = r1.json()["id"]

        r2 = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("second.pdf", io.BytesIO(_PDF_BYTES), "application/pdf")},
            headers=headers,
        )
        assert r2.status_code == 201
        id_second = r2.json()["id"]

        listing = await client.get("/api/v1/documents", headers=headers)
        assert listing.status_code == 200
        ids = [d["id"] for d in listing.json()]
        assert id_first in ids
        assert id_second in ids
        # Newest first: second upload should appear before first
        assert ids.index(id_second) < ids.index(id_first)

    async def test_retrieve_own_document(self, client: AsyncClient) -> None:
        """#8 — Upload then GET by id → 200, body matches upload response."""
        token = await _register_and_login(client, email="getme@example.com")
        up = await client.post(
            "/api/v1/documents/upload", **_pdf_upload(), **_auth(token)
        )
        assert up.status_code == 201
        doc_id = up.json()["id"]

        get = await client.get(f"/api/v1/documents/{doc_id}", **_auth(token))
        assert get.status_code == 200
        assert get.json()["id"] == doc_id
        assert get.json()["original_filename"] == "test.pdf"

    async def test_retrieve_another_users_document_returns_404(
        self, client: AsyncClient
    ) -> None:
        """#9 — User B GETting user A's document id must receive 404."""
        token_a = await _register_and_login(client, email="owner9@example.com")
        token_b = await _register_and_login(client, email="thief9@example.com")

        up = await client.post(
            "/api/v1/documents/upload", **_pdf_upload(), **_auth(token_a)
        )
        assert up.status_code == 201
        doc_id = up.json()["id"]

        get = await client.get(f"/api/v1/documents/{doc_id}", **_auth(token_b))
        assert get.status_code == 404


class TestDelete:
    """Scenarios #10–13: deletion and post-delete state verification."""

    async def test_delete_own_document(self, client: AsyncClient) -> None:
        """#10 — Upload → DELETE → 204."""
        token = await _register_and_login(client, email="del10@example.com")
        up = await client.post(
            "/api/v1/documents/upload", **_pdf_upload(), **_auth(token)
        )
        assert up.status_code == 201
        doc_id = up.json()["id"]

        resp = await client.delete(f"/api/v1/documents/{doc_id}", **_auth(token))
        assert resp.status_code == 204

    async def test_delete_another_users_document_returns_404(
        self, client: AsyncClient
    ) -> None:
        """#11 — User B trying to DELETE user A's doc gets 404."""
        token_a = await _register_and_login(client, email="owner11@example.com")
        token_b = await _register_and_login(client, email="thief11@example.com")

        up = await client.post(
            "/api/v1/documents/upload", **_pdf_upload(), **_auth(token_a)
        )
        assert up.status_code == 201
        doc_id = up.json()["id"]

        resp = await client.delete(f"/api/v1/documents/{doc_id}", **_auth(token_b))
        assert resp.status_code == 404

    async def test_file_removed_from_disk_after_delete(
        self, client: AsyncClient, upload_tmp_path: Path
    ) -> None:
        """#12 — After DELETE the physical file must not exist in tmp_path."""
        token = await _register_and_login(client, email="disk12@example.com")
        up = await client.post(
            "/api/v1/documents/upload", **_pdf_upload(), **_auth(token)
        )
        assert up.status_code == 201
        storage_path: str = up.json()["storage_path"]  # e.g. "pdf/abcdef.pdf"

        # Confirm file exists before delete
        expected_file = upload_tmp_path / storage_path
        assert expected_file.is_file(), f"File should exist before delete: {expected_file}"

        doc_id = up.json()["id"]
        resp = await client.delete(f"/api/v1/documents/{doc_id}", **_auth(token))
        assert resp.status_code == 204

        # File must be gone after delete
        assert not expected_file.exists(), f"File should be gone after delete: {expected_file}"

    async def test_db_row_removed_after_delete(
        self,
        client: AsyncClient,
        db_session,
    ) -> None:
        """#13 — After DELETE, a fresh repo lookup must return None."""
        from app.db.repositories.document_repository import DocumentRepository

        token = await _register_and_login(client, email="db13@example.com")
        up = await client.post(
            "/api/v1/documents/upload", **_pdf_upload(), **_auth(token)
        )
        assert up.status_code == 201
        doc_id = UUID(up.json()["id"])

        resp = await client.delete(f"/api/v1/documents/{doc_id}", **_auth(token))
        assert resp.status_code == 204

        # Fresh session — nothing cached
        repo = DocumentRepository(db_session)
        result = await repo.get_by_id(doc_id)
        assert result is None, "Document row must be absent from DB after delete"


class TestAuthGuard:
    """Bonus scenario n — endpoints reject missing auth with 401."""

    async def test_upload_without_auth_returns_401(self, client: AsyncClient) -> None:
        """No auth header → 401 (verifies dependency wiring is correct)."""
        resp = await client.post(
            "/api/v1/documents/upload", **_pdf_upload()
        )
        assert resp.status_code == 401

    async def test_list_without_auth_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/documents")
        assert resp.status_code == 401

    async def test_get_without_auth_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get(f"/api/v1/documents/{'0' * 32}")
        # Either 401 (auth guard fires) or 422 (UUID parse fails first); 404 is wrong.
        assert resp.status_code in (401, 422)

    async def test_delete_without_auth_returns_401(self, client: AsyncClient) -> None:
        resp = await client.delete(f"/api/v1/documents/{'0' * 32}")
        assert resp.status_code in (401, 422)
