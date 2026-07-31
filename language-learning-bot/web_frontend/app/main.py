"""
Web Frontend — FastAPI + Jinja2 + HTMX. Port: 8548
"""

import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.templating import templates, __version__

from app.routers import auth, languages, study, settings, admin, info

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production-please")

app = FastAPI(title="Language Learning Web", version=__version__)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

BASE = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


@app.middleware("http")
async def no_store_dynamic_pages(request: Request, call_next):
    """Prevent browsers from caching dynamic pages (e.g. /stats, /languages) so
    freshly added languages/progress always show. Static assets stay cacheable."""
    response = await call_next(request)
    if not request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-store"
    return response


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
