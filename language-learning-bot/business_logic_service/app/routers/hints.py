"""
Hints router — CRUD for user-created hint content on individual words.
Hint types: meaning, phoneticsound, phoneticassociation, writing.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.api.client import get_api_client
from app.services.word_service import ensure_user_word_data

router = APIRouter(prefix="/hints", tags=["hints"])

# Map hint_type → field name stored in user_word_data
HINT_FIELD_MAP = {
    "meaning":             "hint_meaning",
    "phoneticsound":       "hint_phoneticsound",
    "phoneticassociation": "hint_phoneticassociation",
    "writing":             "hint_writing",
}


@router.get("/{user_id}/{word_id}")
async def get_hints(user_id: str, word_id: str, api_client=Depends(get_api_client)):
    """Return all hint texts for a word."""
    resp = await api_client.get_user_word_data(user_id, word_id)
    uwd = (resp.get("result") or {}) if resp.get("success") else {}
    return {hint_type: uwd.get(field) or "" for hint_type, field in HINT_FIELD_MAP.items()}


class HintBody(BaseModel):
    hint_type: str
    text: str
    language_id: Optional[str] = None  # required only when creating new user_word_data


@router.put("/{user_id}/{word_id}")
async def set_hint(
    user_id: str,
    word_id: str,
    body: HintBody,
    api_client=Depends(get_api_client),
):
    """Create or update a single hint field for a word."""
    field = HINT_FIELD_MAP.get(body.hint_type)
    if not field:
        raise HTTPException(status_code=400, detail=f"Unknown hint_type '{body.hint_type}'")

    # Pass language_id so ensure_user_word_data can create a new record if needed
    word_stub = {"language_id": body.language_id} if body.language_id else {}
    ok, result = await ensure_user_word_data(
        api_client, user_id, word_id,
        {field: body.text.strip()},
        word=word_stub,
    )
    if not ok:
        raise HTTPException(status_code=502, detail="Failed to save hint")
    return {"ok": True, "hint_type": body.hint_type, "text": body.text.strip()}


@router.delete("/{user_id}/{word_id}/{hint_type}")
async def delete_hint(
    user_id: str,
    word_id: str,
    hint_type: str,
    api_client=Depends(get_api_client),
):
    """Clear a single hint field (set to empty string)."""
    field = HINT_FIELD_MAP.get(hint_type)
    if not field:
        raise HTTPException(status_code=400, detail=f"Unknown hint_type '{hint_type}'")

    ok, _ = await ensure_user_word_data(api_client, user_id, word_id, {field: ""})
    if not ok:
        raise HTTPException(status_code=502, detail="Failed to clear hint")
    return {"ok": True}
