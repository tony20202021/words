from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_404_NOT_FOUND
from typing import Optional
from pydantic import BaseModel
from app.services import user_service
from app.api.client import get_api_client

router = APIRouter(prefix="/user", tags=["user"])


class GetOrCreateRequest(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None


@router.post("/get_or_create")
async def get_or_create_user(req: GetOrCreateRequest, api_client=Depends(get_api_client)):
    user_id, user_data = await user_service.get_or_create_user(
        req.telegram_id, req.username, req.first_name, req.last_name, api_client
    )
    if user_id is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Could not get or create user")
    return {"user_id": user_id, "user_data": user_data}


@router.get("/{user_id}/is_admin")
async def is_admin(user_id: str, api_client=Depends(get_api_client)):
    result = await user_service.is_admin(user_id, api_client)
    return {"is_admin": result}
