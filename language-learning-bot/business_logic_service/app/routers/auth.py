from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel
from app.services import auth_service
from app.api.client import get_api_client

router = APIRouter(prefix="/auth", tags=["auth"])


class LookupRequest(BaseModel):
    mode: str  # "telegram" | "name"
    telegram_id: Optional[int] = None
    name: Optional[str] = None
    direct: bool = False  # skip token creation and Telegram message


class CreateRequest(BaseModel):
    mode: str  # "telegram" | "name"
    telegram_id: Optional[int] = None
    first_name: str


@router.post("/lookup")
async def lookup(body: LookupRequest, api_client=Depends(get_api_client)):
    """
    Look up user by telegram_id or name.
    Telegram: if found, creates token and sends Telegram message.
    Name: if found, returns user_id directly (no confirmation needed).
    """
    if body.mode == "telegram":
        if not body.telegram_id:
            raise HTTPException(status_code=400, detail="telegram_id required")
        result = await auth_service.lookup_telegram(body.telegram_id, api_client)
        if result["found"]:
            first_name = result.get("first_name", "")
            if body.direct:
                return {"found": True, "user_id": result["user_id"], "first_name": first_name}
            token = auth_service.create_token(body.telegram_id, result["user_id"], first_name=first_name)
            message_sent = await auth_service.send_auth_request(body.telegram_id, token)
            return {"found": True, "token": token, "message_sent": message_sent,
                    "first_name": first_name}
        return {"found": False, "mode": "telegram", "telegram_id": body.telegram_id}

    if body.mode == "name":
        if not body.name:
            raise HTTPException(status_code=400, detail="name required")
        return await auth_service.lookup_name(body.name.strip(), api_client)

    raise HTTPException(status_code=400, detail="mode must be 'telegram' or 'name'")


@router.post("/create")
async def create(body: CreateRequest, api_client=Depends(get_api_client)):
    """
    Create a new user.
    Telegram mode: creates user + sends Telegram confirmation → returns token.
    Name mode: creates user with generated pseudo-id → returns user_id directly.
    """
    if body.mode == "telegram":
        if not body.telegram_id:
            raise HTTPException(status_code=400, detail="telegram_id required")
        result = await auth_service.create_user_by_telegram(
            body.telegram_id, body.first_name, api_client
        )
        return result

    if body.mode == "name":
        result = await auth_service.create_user_by_name(body.first_name, api_client)
        return result

    raise HTTPException(status_code=400, detail="mode must be 'telegram' or 'name'")


@router.post("/confirm/{token}")
async def confirm_auth(token: str):
    """Telegram bot calls this when user presses Да."""
    entry = auth_service.get_token_entry(token)
    if not entry:
        return {"ok": False, "reason": "not_found"}
    if entry["status"] != "pending":
        return {"ok": False, "reason": entry["status"]}
    ok = auth_service.confirm_token(token)
    return {"ok": ok}


@router.post("/deny/{token}")
async def deny_auth(token: str):
    """Telegram bot calls this when user presses Нет."""
    ok = auth_service.deny_token(token)
    return {"ok": ok}


@router.get("/status/{token}")
async def auth_status(token: str):
    """Web polls this to check if user confirmed via Telegram."""
    entry = auth_service.get_token_entry(token)
    if not entry:
        return {"status": "not_found"}
    is_confirmed = entry["status"] == "confirmed"
    return {
        "status": entry["status"],
        "user_id": entry.get("user_id") if is_confirmed else None,
        "telegram_id": entry.get("telegram_id") if is_confirmed else None,
        "first_name": entry.get("first_name", "") if is_confirmed else None,
    }
