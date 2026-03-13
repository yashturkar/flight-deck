from pydantic import BaseModel, Field


class ContextSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    view: str = "current"
    limit: int = Field(default=10, ge=1, le=50)


class ContextSearchResult(BaseModel):
    path: str
    title: str
    score: float
    reasons: list[str]
    excerpt: str
    view: str
    sources: list[str] | None = None


class ContextSearchResponse(BaseModel):
    query: str
    view: str
    results: list[ContextSearchResult]


class ContextBundleRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    view: str = "current"
    limit: int = Field(default=10, ge=1, le=50)
    token_budget: int = Field(default=4000, ge=1, le=50000)


class ContextBundleItem(ContextSearchResult):
    content: str | None = None
    content_tokens: int = 0
    truncated: bool = False


class ContextBundleResponse(BaseModel):
    query: str
    view: str
    token_budget: int
    used_tokens: int
    items: list[ContextBundleItem]
