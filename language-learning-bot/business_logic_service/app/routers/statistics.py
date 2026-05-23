from fastapi import APIRouter, Depends, HTTPException, Query, Response
from starlette.status import HTTP_404_NOT_FOUND
from datetime import date
from typing import Optional
from app.services import statistics_service
from app.api.client import get_api_client

router = APIRouter(prefix="/statistics", tags=["statistics"])


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
    charts = statistics_service.generate_today_charts(progress)
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
    charts = statistics_service.generate_monthly_charts(all_days, first_finish, show_all=show_all)
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
