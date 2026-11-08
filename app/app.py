"""App factory - single entry point for FastAPI.

create_app() keeps side-effects out of import time, allows tests to override
settings, and makes `uvicorn app.app:app` explicit.

Security model (this server holds API keys, your resume and message history):
- CORS only allows the desktop shell and local dev frontends, not any website.
- When JOB_SEARCH_API_TOKEN is set (the Tauri shell sets it per launch), every
  request except /health must send it as `X-API-Token`. Websites cannot read it,
  so they cannot drive the API even though it listens on localhost.
"""

import hmac
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from app.core.logging import get_logger, setup_logging
from app.core.settings import PROJECT_ROOT as REPO_ROOT

setup_logging()
logger = get_logger(__name__)

FRONTEND_DIR = REPO_ROOT / "frontend"

API_TOKEN_ENV = "JOB_SEARCH_API_TOKEN"
EXTRA_ORIGINS_ENV = "JOB_SEARCH_ALLOWED_ORIGINS"
DEFAULT_ORIGINS = [
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
_OPEN_PATHS = {"/health", "/"}

# Import routers after logging is configured.
from app.api.routers import (
    config,
    enrich,
    messages,
    personalization,
    resume,
    tracker,
    usage,
    user_communication,
)


def _allowed_origins() -> list[str]:
    extra = [o.strip() for o in os.environ.get(EXTRA_ORIGINS_ENV, "").split(",")]
    return DEFAULT_ORIGINS + [o for o in extra if o]


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    from app.services.migrations import run_all

    run_all()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="JobSearch Assistant API", version="1.0", lifespan=_lifespan)
    logger.info("initializing JobSearch Assistant API v1.0")

    @app.middleware("http")
    async def require_api_token(request: Request, call_next):
        token = os.environ.get(API_TOKEN_ENV)
        if (
            token
            and request.method != "OPTIONS"
            and request.url.path not in _OPEN_PATHS
            and not hmac.compare_digest(request.headers.get("x-api-token", ""), token)
        ):
            return JSONResponse({"detail": "Missing or invalid API token."}, 401)
        return await call_next(request)

    # Added last so it is outermost: CORS headers also appear on 401 responses.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(personalization.router)
    app.include_router(resume.router)
    app.include_router(user_communication.router)
    app.include_router(messages.router)
    app.include_router(config.router)
    app.include_router(enrich.router)
    app.include_router(tracker.router)
    app.include_router(usage.router)

    @app.get("/health")
    def health_check():
        return {"status": "healthy", "service": "job-search-assistant-backend"}

    @app.get("/", response_class=HTMLResponse)
    def serve_frontend():
        html_path = FRONTEND_DIR / "index.html"
        if html_path.exists():
            return html_path.read_text(encoding="utf-8")
        return "<h1>Frontend index.html not found</h1>"

    return app


# Default app instance for `uvicorn app.app:app` and existing imports
app = create_app()
