from enum import Enum

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import require_api_key
from app.schemas.context import (
    ContextBundleItem,
    ContextBundleRequest,
    ContextBundleResponse,
    ContextSearchRequest,
    ContextSearchResponse,
    ContextSearchResult,
)
from app.services import retrieval_service

router = APIRouter(
    prefix="/context",
    tags=["context"],
    dependencies=[Depends(require_api_key)],
)


class ViewType(str, Enum):
    main = "main"
    current = "current"


@router.post("/search", response_model=ContextSearchResponse)
def search_context(body: ContextSearchRequest):
    if body.view not in {ViewType.main.value, ViewType.current.value}:
        raise HTTPException(status_code=400, detail="Unsupported view")

    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query must not be blank")

    try:
        results = retrieval_service.search_notes(
            query=query,
            view=body.view,
            limit=body.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ContextSearchResponse(
        query=query,
        view=body.view,
        results=[
            ContextSearchResult(
                path=result.path,
                title=result.title,
                score=result.score,
                reasons=result.reasons,
                excerpt=result.excerpt,
                view=result.view,
                sources=result.sources,
            )
            for result in results
        ],
    )


@router.post("/bundle", response_model=ContextBundleResponse)
def build_context_bundle(body: ContextBundleRequest):
    if body.view not in {ViewType.main.value, ViewType.current.value}:
        raise HTTPException(status_code=400, detail="Unsupported view")

    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query must not be blank")

    try:
        items, used_tokens = retrieval_service.build_context_bundle(
            query=query,
            view=body.view,
            limit=body.limit,
            token_budget=body.token_budget,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ContextBundleResponse(
        query=query,
        view=body.view,
        token_budget=body.token_budget,
        used_tokens=used_tokens,
        items=[
            ContextBundleItem(
                path=item.path,
                title=item.title,
                score=item.score,
                reasons=item.reasons,
                excerpt=item.excerpt,
                view=item.view,
                sources=item.sources,
                content=item.content,
                content_tokens=item.content_tokens,
                truncated=item.truncated,
            )
            for item in items
        ],
    )
