import hashlib
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import Settings, get_settings
from app.services.browser import BrowserFetchError, fetch_html
from app.services.cleaner import extract_content
from app.utils.cache import cache


router = APIRouter(prefix="/fetch", tags=["fetch"])


def _rate_limit_key(request: Request) -> str:
    """Rate limit per API key, falling back to client IP for unauthenticated hits."""

    return request.headers.get("x-api-key") or get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key)


class FetchRequest(BaseModel):
    """Request body for fetching a URL."""

    url: str = Field(..., min_length=1, examples=["https://example.com"])


class FetchResponse(BaseModel):
    """Normalized response for successful content extraction."""

    success: bool
    content: str
    title: str = ""
    url: str
    cached: bool = False


def require_api_key(
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Validate X-API-Key against configured SHA-256 key hashes."""

    allowed_hashes = settings.allowed_key_hashes
    if not allowed_hashes:
        return
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "error": "Missing X-API-Key header."},
        )
    candidate_hash = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    if candidate_hash not in allowed_hashes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "error": "Invalid API key."},
        )


def validate_url(url: str) -> None:
    """Reject invalid or unsupported URLs before they reach the browser."""

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": "Invalid URL. Use http or https."},
        )


@router.post("", response_model=FetchResponse)
@router.post("/", response_model=FetchResponse, include_in_schema=False)
@limiter.limit(lambda: get_settings().request_rate_limit)
async def fetch(
    request: Request,
    payload: FetchRequest,
    _: None = Depends(require_api_key),
) -> FetchResponse:
    """Fetch a URL, extract clean Markdown, and cache the result in Redis."""

    validate_url(payload.url)
    cache_key = f"fetch:{hashlib.md5(payload.url.encode('utf-8')).hexdigest()}"

    cached = cache.get(cache_key)
    if cached:
        cached["cached"] = True
        return FetchResponse(**cached)

    try:
        html = await fetch_html(payload.url)
        extracted = await extract_content(html, payload.url)
    except BrowserFetchError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"success": False, "error": str(exc)},
        ) from exc

    response = FetchResponse(
        success=True,
        content=extracted["content"],
        title=extracted["title"],
        url=payload.url,
        cached=False,
    )
    cache.set(cache_key, response.model_dump())
    return response
