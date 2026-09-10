"""App factory - single entry point for FastAPI.

Industry standard: create_app() factory keeps side-effects out of import time,
allows tests to override settings, and makes `uvicorn app.app:app` explicit.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.core.logging import get_logger, setup_logging
from app.core.settings import PROJECT_ROOT as REPO_ROOT

setup_logging()
logger = get_logger(__name__)

FRONTEND_DIR = REPO_ROOT / "frontend"

# Import routers lazily to avoid circular imports at import time
from app.api.routers import (
    config,
    enrich,
    messages,
    personalization,
    resume,
    user_communication,
)


def create_app() -> FastAPI:
    app = FastAPI(title="JobSearch Assistant API", version="1.0")
    logger.info("initializing JobSearch Assistant API v1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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

    @app.get("/health")
    def health_check():
        logger.debug("health check requested")
        return {"status": "healthy", "service": "job-search-assistant-backend"}

    @app.get("/", response_class=HTMLResponse)
    async def serve_frontend():
        html_path = FRONTEND_DIR / "index.html"
        if os.path.exists(html_path):
            logger.debug("serving frontend html path=%s", html_path)
            with open(html_path, "r", encoding="utf-8") as f:
                return f.read()
        logger.warning("frontend index.html not found at %s", html_path)
        return "<h1>Frontend index.html not found</h1>"

    return app


# Default app instance for `uvicorn app.app:app` and existing imports
app = create_app()
