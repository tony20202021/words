"""
Business Logic Service — FastAPI application.
Port: 8531
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.logger import setup_logger
from app.api.client import init_api_client
from app.routers import session, user, settings, statistics, languages, auth, admin, hints, sounds, info, results

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    backend_url = os.environ.get("BACKEND_URL", "http://localhost:8573")
    init_api_client(backend_url)
    logger.info(f"BLS started. Backend: {backend_url}")
    yield
    logger.info("BLS shutting down.")


app = FastAPI(title="Business Logic Service", version="0.1.0", lifespan=lifespan)

app.include_router(session.router)
app.include_router(user.router)
app.include_router(settings.router)
app.include_router(statistics.router)
app.include_router(languages.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(hints.router)
app.include_router(sounds.router)
app.include_router(info.router)
app.include_router(results.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
