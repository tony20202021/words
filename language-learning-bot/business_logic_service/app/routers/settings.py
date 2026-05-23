from fastapi import APIRouter, Depends
from typing import Any
from pydantic import BaseModel
from app.services import settings_service
from app.api.client import get_api_client

router = APIRouter(prefix="/settings", tags=["settings"])


class ToggleValueRequest(BaseModel):
    value: Any = None


@router.get("/{user_id}/{language_id}")
async def get_settings(user_id: str, language_id: str, api_client=Depends(get_api_client)):
    return await settings_service.get_settings(user_id, language_id, api_client)


@router.put("/{user_id}/{language_id}/{key}")
async def set_setting(
    user_id: str, language_id: str, key: str,
    req: ToggleValueRequest,
    api_client=Depends(get_api_client),
):
    settings = await settings_service.get_settings(user_id, language_id, api_client)
    settings[key] = req.value
    await settings_service.save_settings(user_id, language_id, settings, api_client)
    return settings


@router.post("/{user_id}/{language_id}/{key}/toggle")
async def toggle_setting(user_id: str, language_id: str, key: str, api_client=Depends(get_api_client)):
    return await settings_service.toggle_setting(user_id, language_id, key, api_client)


@router.get("/{user_id}/{language_id}/hints")
async def get_hint_settings(user_id: str, language_id: str, api_client=Depends(get_api_client)):
    return await settings_service.get_hint_settings(user_id, language_id, api_client)


@router.post("/{user_id}/{language_id}/hints/{hint_key}/toggle")
async def toggle_hint(
    user_id: str, language_id: str, hint_key: str, api_client=Depends(get_api_client)
):
    return await settings_service.toggle_hint(user_id, language_id, hint_key, api_client)
