import asyncio
import time
from functools import partial
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from starlette.status import HTTP_404_NOT_FOUND
from datetime import date
from typing import Optional, Dict, Any
from app.services import statistics_service
from app.api.client import get_api_client

router = APIRouter(prefix="/statistics", tags=["statistics"])

# ── chart cache (TTL=60s, anti-stampede per key) ──────────────────────────────
_chart_cache: Dict[str, Any] = {}   # key → {"ts": float, "data": dict}
_chart_locks: Dict[str, asyncio.Lock] = {}
_CHART_TTL = 60.0


def _cache_key(*parts) -> str:
    return "|".join(str(p) for p in parts)


async def _get_charts_cached(key: str, generator):
    """Return cached chart dict or call generator() in executor, cache result."""
    entry = _chart_cache.get(key)
    if entry and time.monotonic() - entry["ts"] < _CHART_TTL:
        return entry["data"]

    if key not in _chart_locks:
        _chart_locks[key] = asyncio.Lock()
    async with _chart_locks[key]:
        # re-check after acquiring lock
        entry = _chart_cache.get(key)
        if entry and time.monotonic() - entry["ts"] < _CHART_TTL:
            return entry["data"]
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, generator)
        _chart_cache[key] = {"ts": time.monotonic(), "data": data}
        return data


@router.get("/{user_id}/{language_id}")
async def get_progress(user_id: str, language_id: str, api_client=Depends(get_api_client)):
    progress = await statistics_service.get_user_progress(user_id, language_id, api_client)
    return statistics_service.compute_statistics_summary(progress)


@router.get("/{user_id}/{language_id}/chart/{chart_name}")
async def get_today_chart(
    user_id: str,
    language_id: str,
    chart_name: str,
    api_client=Depends(get_api_client),
):
    progress = await statistics_service.get_user_progress(user_id, language_id, api_client)
    key = _cache_key("today", user_id, language_id)
    charts = await _get_charts_cached(key, lambda: statistics_service.generate_today_charts(progress))
    if chart_name not in charts:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Chart '{chart_name}' not available")
    return Response(content=charts[chart_name], media_type="image/png")


@router.get("/{user_id}/{language_id}/monthly-chart/{chart_name}")
async def get_monthly_chart(
    user_id: str,
    language_id: str,
    chart_name: str,
    show_all: bool = Query(True),
    api_client=Depends(get_api_client),
):
    all_days, first_finish = await statistics_service.get_monthly_statistics(
        user_id, language_id, date.today(), api_client, show_all=show_all
    )
    key = _cache_key("monthly", user_id, language_id, show_all)
    charts = await _get_charts_cached(
        key,
        partial(statistics_service.generate_monthly_charts, all_days, first_finish, show_all=show_all)
    )
    if chart_name not in charts:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Chart '{chart_name}' not available")
    return Response(content=charts[chart_name], media_type="image/png")


@router.post("/{user_id}/{language_id}/daily")
async def update_daily(
    user_id: str,
    language_id: str,
    action_date: Optional[date] = None,
    api_client=Depends(get_api_client),
):
    if action_date is None:
        action_date = date.today()
    progress = await statistics_service.get_user_progress(user_id, language_id, api_client)
    await statistics_service.update_daily_statistics(user_id, language_id, action_date, progress, api_client)
    return {"ok": True}
