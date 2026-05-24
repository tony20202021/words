"""
Web Frontend — FastAPI + Jinja2 + HTMX. Port: 8800
"""

import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common.version import __version__

from app.routers import auth, languages, study, settings, admin, info

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production-please")

app = FastAPI(title="Language Learning Web", version=__version__)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / "templates"))
templates.env.globals["app_version"] = __version__
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")

app.include_router(auth.router)
app.include_router(languages.router)
app.include_router(study.router)
app.include_router(settings.router)
app.include_router(admin.router)
app.include_router(info.router)


@app.get("/")
async def index(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/languages", status_code=302)
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}
