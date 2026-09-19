import time
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from starlette.status import HTTP_502_BAD_GATEWAY, HTTP_404_NOT_FOUND
from datetime import date
from typing import Optional, Dict, Any
from app.services import chart_cache, statistics_service
from app.api.client import get_api_client

router = APIRouter(prefix="/statistics", tags=["statistics"])

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from common.chart_manifest import CHART_SECTIONS, CHART_CAPTIONS

@router.get("/chart_manifest")
async def get_chart_manifest():
    return {"sections": CHART_SECTIONS, "captions": CHART_CAPTIONS}


@router.get("/{user_id}/{language_id}")
async def get_progress(user_id: str, language_id: str, api_client=Depends(get_api_client)):
    progress = await statistics_service.get_user_progress(user_id, language_id, api_client)
    return statistics_service.compute_statistics_summary(progress)


@router.get("/{user_id}/{language_id}/chart/{chart_name}")
async def get_today_chart(
    user_id: str,
    language_id: str,
    chart_name: str,
    res: str = Query("screen", pattern="^(screen|zoom)$",
                     description="screen — под экран, быстро; zoom — для увеличения"),
    api_client=Depends(get_api_client),
):
    chart_cache.note_view(user_id, language_id)
    charts = await chart_cache.today_charts(user_id, language_id, api_client, res)
    if chart_name not in charts:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Chart '{chart_name}' not available")
    return Response(content=charts[chart_name], media_type="image/png")


@router.get("/{user_id}/{language_id}/monthly-chart/{chart_name}")
async def get_monthly_chart(
    user_id: str,
    language_id: str,
    chart_name: str,
    show_all: bool = Query(True),
    res: str = Query("screen", pattern="^(screen|zoom)$",
                     description="screen — под экран, быстро; zoom — для увеличения"),
    api_client=Depends(get_api_client),
):
    chart_cache.note_view(user_id, language_id)
    charts = await chart_cache.monthly_charts(user_id, language_id, show_all, api_client, res)
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
        action_date = statistics_service.study_day()
    progress = await statistics_service.get_user_progress(user_id, language_id, api_client)
    written = await statistics_service.update_daily_statistics(
        user_id, language_id, action_date, progress, api_client
    )
    if not written:
        # Прежде здесь стоял безусловный {"ok": true}: результат записи никто не
        # смотрел, и неудача выглядела как успех. Именно на этом молча ничего не
        # записалось при проверке выкладки 4.4.0 — а ответ был «ок».
        raise HTTPException(
            status_code=HTTP_502_BAD_GATEWAY,
            detail="Failed to write daily statistics",
        )
    return {"ok": True}
