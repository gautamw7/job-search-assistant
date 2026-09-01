from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
import os

app = FastAPI(title="JobSearch Assistant API", version="1.0")

# Enable CORS so your frontend can talk to the backend smoothly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"

# Mount JS directory for ES modules
app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")

from api.routers import messages, personalization, resume, user_communication

app.include_router(personalization.router)
app.include_router(resume.router)
app.include_router(user_communication.router)
app.include_router(messages.router)

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serves the modular frontend UI."""
    html_path = FRONTEND_DIR / "index.html"
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Frontend index.html not found</h1>"
