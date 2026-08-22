import asyncio
from app.db.session import AsyncSessionLocal
from app.db.models.user import User
from app.services.chat_service import ChatService
from app.rag.service import RAGService
from app.processing.embeddings.provider import SentenceTransformerEmbeddingProvider
from app.processing.embeddings.qdrant import QdrantVectorStore
from sqlalchemy import select

async def debug_chat_direct():
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

        # 2. Setup ChatService dependencies
        # We need a RAGService for the ChatService
        emb_provider = SentenceTransformerEmbeddingProvider()
        vec_store = QdrantVectorStore()
        rag_service = RAGService(embedding_provider=emb_provider, vector_store=vec_store)

        chat_service = ChatService(session=session, rag_service=rag_service)

        print("\n--- Testing list_user_sessions ---")
        try:
            sessions = await chat_service.list_user_sessions(owner_id=user.id)
            print(f"Successfully listed {len(sessions)} sessions.")
        except Exception as e:
            print(f"list_user_sessions failed: {e}")
            import traceback
            traceback.print_exc()

        print("\n--- Testing create_session ---")
        try:
            session_obj = await chat_service.create_session(
                owner=user,
                title="Debug Session"
            )
            print(f"Successfully created session: {session_obj.id}")
        except Exception as e:
            print(f"create_session failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_chat_direct())
