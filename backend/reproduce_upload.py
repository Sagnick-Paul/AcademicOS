import asyncio
import os
from pathlib import Path
from uuid import uuid4
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.db.models.user import User
from app.services.document_service import DocumentService
from app.storage.local import LocalStorage

async def reproduce_upload():
    # 1. Setup
    async with AsyncSessionLocal() as session:
        # Get a test user
        from sqlalchemy import select
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            print("Error: No user found in database. Please create one first.")
            return

        service = DocumentService(session=session)

        # Create a dummy PDF (starts with %PDF-)
        test_file = Path("test_upload.pdf")
        test_file.write_bytes(b"%PDF-1.4\n% some dummy content")
        content = test_file.read_bytes()

        print(f"Attempting to create document for user {user.email}...")
        try:
            doc = await service.create_document(
                owner=user,
                content=content,
                original_filename="test_upload.pdf",
                content_type="application/pdf",
            )
            print(f"Document created successfully: {doc.id}")

            print("Attempting to process document...")
            await service.process_document(doc.id)
            print("Processing completed successfully!")

        except Exception as e:
            print(f"Upload failed with error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if test_file.exists():
                test_file.unlink()

if __name__ == "__main__":
    asyncio.run(reproduce_upload())
