"""Semantic search endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_active_user, get_retrieval_service
from app.db.models.user import User
from app.schemas.search import SearchRequest, SearchResponse
from app.services.retrieval_service import RetrievalService
from app.processing.exceptions import ProcessingError

router = APIRouter()


@router.post(
    "",
    response_model=SearchResponse,
    summary="Perform semantic search",
)
async def semantic_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_active_user),
    service: RetrievalService = Depends(get_retrieval_service),
) -> SearchResponse:
    """Search for relevant document chunks using vector embeddings.

    Restricted to documents owned by the authenticated user.
    """
    try:
        results = await service.retrieve(
            query=request.query,
            owner_id=current_user.id,
            limit=request.top_k,
            score_threshold=request.score_threshold,
            document_id=request.document_id,
            mode=request.mode,
        )
        return SearchResponse(results=results)
    except ProcessingError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred during search: {exc}",
        ) from exc
