import asyncio
import httpx
from uuid import uuid4
from app.core.security import create_access_token
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.db.models.user import User
from sqlalchemy import select

async def debug_chat():
    async with AsyncSessionLocal() as session:
        # 1. Setup test user
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            print("No user found. Creating one...")
            user = User(
                full_name="Debug User",
                email="debug@example.com",
                hashed_password="hashed_password",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        # 2. Generate JWT
        token = create_access_token(subject=user.id)
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(base_url="http://localhost:8000/api/v1") as client:
            print("\n--- Testing GET /chat/sessions ---")
            try:
                resp = await client.get("/chat/sessions", headers=headers)
                print(f"Status: {resp.status_code}")
                print(f"Response: {resp.text}")
            except Exception as e:
                print(f"Request failed: {e}")

            print("\n--- Testing POST /chat/sessions ---")
            try:
                payload = {"title": "Debug Session"}
                resp = await client.post("/chat/sessions", json=payload, headers=headers)
                print(f"Status: {resp.status_code}")
                print(f"Response: {resp.text}")
            except Exception as e:
                print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_chat())
