from fastapi import APIRouter, Depends
from app.api.client import get_api_client

router = APIRouter(prefix="/languages", tags=["languages"])


@router.get("/")
async def get_languages(api_client=Depends(get_api_client)):
    response = await api_client.get_languages()
    return response.get("result") or []
