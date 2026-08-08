from pathlib import Path
from uuid import UUID
from app.core.config import settings
from app.processing.dispatcher import DocumentDispatcher
from app.processing.schemas import ProcessingResult
from app.processing.exceptions import ProcessingFailed, ProcessingError
from app.processing.embeddings.base import BaseEmbeddingProvider, BaseVectorStore


class DocumentProcessingPipeline:
    """Coordinating pipeline for document processing runs."""

    def __init__(
        self,
        dispatcher: DocumentDispatcher | None = None,
        embedding_provider: BaseEmbeddingProvider | None = None,
        vector_store: BaseVectorStore | None = None,
    ) -> None:
        self.dispatcher = dispatcher or DocumentDispatcher()
        
        if embedding_provider is None:
            from app.processing.embeddings.provider import SentenceTransformerEmbeddingProvider
            embedding_provider = SentenceTransformerEmbeddingProvider()
        if vector_store is None:
            from app.processing.embeddings.qdrant import QdrantVectorStore
            vector_store = QdrantVectorStore()
            
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    async def run(
        self,
        file_path: Path,
        file_type: str,
        filename: str,
        file_size: int,
        document_id: UUID | None = None,
        owner_id: UUID | None = None,
    ) -> ProcessingResult:
        """Execute the document processing pipeline on the target file.

        Raises ProcessingFailed if any processing error occurs.
        """
        try:
            result = await self.dispatcher.dispatch(
                file_path=file_path,
                file_type=file_type,
                filename=filename,
                file_size=file_size,
            )
            
            if result.chunks:
                texts = [chunk.text for chunk in result.chunks]
                embeddings = await self.embedding_provider.generate_embeddings(texts)
                
                from uuid import uuid4
                from app.processing.embeddings.schemas import EmbeddingVector
                
                await self.vector_store.create_collection(
                    collection_name=settings.QDRANT_COLLECTION,
                    vector_size=settings.EMBEDDING_DIMENSION,
                )
                
                vectors = []
                for idx, chunk in enumerate(result.chunks):
                    chunk_uuid = str(uuid4())
                    page_num = chunk.metadata.get("page")
                    if page_num is not None:
                        try:
                            page_num = int(page_num)
                        except (ValueError, TypeError):
                            pass
                    
                    payload_metadata = dict(chunk.metadata)
                    payload_metadata["text"] = chunk.text
                    
                    payload = {
                        "document_id": str(document_id) if document_id else None,
                        "owner_id": str(owner_id) if owner_id else None,
                        "chunk_id": chunk_uuid,
                        "page_number": page_num,
                        "chunk_index": chunk.index,
                        "metadata": payload_metadata,
                    }
                    vectors.append(
                        EmbeddingVector(
                            chunk_id=chunk_uuid,
                            vector=embeddings[idx],
                            metadata=payload,
                        )
                    )
                
                await self.vector_store.upsert_vectors(
                    collection_name=settings.QDRANT_COLLECTION,
                    vectors=vectors,
                )
                
            return result
        except ProcessingError as exc:
            # Re-raise known domain exceptions
            raise exc
        except Exception as exc:
            # Wrap unexpected exceptions
            raise ProcessingFailed(f"An unexpected error occurred during processing: {exc}") from exc

