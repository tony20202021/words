"""
Sound proxy — lets Android (and other clients) stream audio files through BLS
without knowing the backend URL.
GET /sounds/{path} → proxies to BACKEND_URL/api/sounds/{encoded_path}
"""

import os
from urllib.parse import quote
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter(prefix="/sounds", tags=["sounds"])

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8500")


@router.get("/{sound_path:path}")
async def proxy_sound(sound_path: str):
    encoded = quote(sound_path, safe="").replace(".", "%2E")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{BACKEND_URL}/api/sounds/{encoded}")
        if resp.status_code == 200:
            content_type = resp.headers.get("content-type", "audio/mpeg")
            return Response(content=resp.content, media_type=content_type)
        raise HTTPException(status_code=404, detail="Sound not found")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Backend error: {e}")
