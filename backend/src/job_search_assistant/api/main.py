import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from job_search_assistant.services.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

app = FastAPI(title="JobSearch Assistant API", version="1.0")
logger.info("initializing JobSearch Assistant API v1.0")

# Enable CORS so frontend (Vite 3000, Tauri) can talk to backend
# allow_credentials=False required when using wildcard origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from job_search_assistant.services.paths import PROJECT_ROOT as ROOT_DIR

# Repo root is one level above backend
REPO_ROOT = ROOT_DIR.parent
FRONTEND_DIR = REPO_ROOT / "frontend"

from job_search_assistant.api.routers import (
    config,
    enrich,
    messages,
    personalization,
    resume,
    user_communication,
)

app.include_router(personalization.router)
app.include_router(resume.router)
app.include_router(user_communication.router)
app.include_router(messages.router)
app.include_router(
    config.router
)  # Include the config router for Bright Data and Gemini credentials
app.include_router(enrich.router)


@app.get("/health")
def health_check():
    logger.debug("health check requested")
    return {"status": "healthy", "service": "job-search-assistant-backend"}


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serves the modular frontend UI."""
    html_path = FRONTEND_DIR / "index.html"
    if os.path.exists(html_path):
        logger.debug("serving frontend html path=%s", html_path)
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    logger.warning("frontend index.html not found at %s", html_path)
    return "<h1>Frontend index.html not found</h1>"
