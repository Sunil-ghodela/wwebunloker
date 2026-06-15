import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.routers.fetch import limiter, router as fetch_router


logging.basicConfig(level=logging.INFO)
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI-ready web fetching and Markdown extraction gateway.",
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.include_router(fetch_router)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a consistent JSON error body for rate-limited requests."""

    return JSONResponse(
        status_code=429,
        content={"success": False, "error": "Rate limit exceeded."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Prevent internal tracebacks from leaking to API clients."""

    logging.exception("Unhandled API error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error."},
    )


@app.get("/")
async def health_check() -> dict[str, str]:
    """Health check endpoint for load balancers and uptime monitors."""

    return {"status": "ok", "service": "Web Unlocker API"}
