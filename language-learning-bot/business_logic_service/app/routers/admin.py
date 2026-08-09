"""
Admin API router — all endpoints require the caller to pass a user_id that is admin.
The web frontend verifies admin status from session; the bot verifies via is_admin().
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import Response
from typing import Optional
from pydantic import BaseModel
from app.services import admin_service
from app.services.user_service import is_admin
from app.api.client import get_api_client

router = APIRouter(prefix="/admin", tags=["admin"])

EDITABLE_WORD_FIELDS = {
    "foreign", "translation", "transcription",
    "radicals", "references", "tones", "sounds", "number",
    "part_of_speech", "lemma",
}


async def _check_admin(user_id: str, api_client):
    if not await is_admin(user_id, api_client):
        raise HTTPException(status_code=403, detail="Admin access required")


# ── Global stats ──────────────────────────────────────────────────────────────

@router.get("/stats")
async def global_stats(user_id: str = Query(...), api_client=Depends(get_api_client)):
    await _check_admin(user_id, api_client)
    return await admin_service.get_global_stats(api_client)


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    user_id: str = Query(...),
    page: int = Query(1, ge=1),
    api_client=Depends(get_api_client),
):
    await _check_admin(user_id, api_client)
    return await admin_service.get_users_page(page, api_client)


@router.get("/users/{target_user_id}")
async def user_details(
    target_user_id: str,
    user_id: str = Query(...),
    api_client=Depends(get_api_client),
):
    await _check_admin(user_id, api_client)
    return await admin_service.get_user_details(target_user_id, api_client)


class ToggleAdminRequest(BaseModel):
    is_admin: bool


@router.post("/users/{target_user_id}/toggle_admin")
async def toggle_admin(
    target_user_id: str,
    body: ToggleAdminRequest,
    user_id: str = Query(...),
    api_client=Depends(get_api_client),
):
    await _check_admin(user_id, api_client)
    ok = await admin_service.set_admin(target_user_id, body.is_admin, api_client)
    return {"ok": ok}


# ── Languages ─────────────────────────────────────────────────────────────────

@router.get("/languages")
async def list_languages(user_id: str = Query(...), api_client=Depends(get_api_client)):
    await _check_admin(user_id, api_client)
    return await admin_service.get_global_stats(api_client)  # includes lang list with counts


@router.get("/languages/{language_id}")
async def language_detail(
    language_id: str,
    user_id: str = Query(...),
    api_client=Depends(get_api_client),
):
    await _check_admin(user_id, api_client)
    lang = await admin_service.get_language_with_stats(language_id, api_client)
    if not lang:
        raise HTTPException(status_code=404, detail="Language not found")
    return lang


class LanguageBody(BaseModel):
    name_ru: str
    name_foreign: str


@router.post("/languages")
async def create_language(
    body: LanguageBody,
    user_id: str = Query(...),
    api_client=Depends(get_api_client),
):
    await _check_admin(user_id, api_client)
    return await admin_service.create_language(body.name_ru, body.name_foreign, api_client)


@router.put("/languages/{language_id}")
async def update_language(
    language_id: str,
    body: LanguageBody,
    user_id: str = Query(...),
    api_client=Depends(get_api_client),
):
    await _check_admin(user_id, api_client)
    ok = await admin_service.update_language(language_id, body.name_ru, body.name_foreign, api_client)
    return {"ok": ok}


@router.delete("/languages/{language_id}")
async def delete_language(
    language_id: str,
    user_id: str = Query(...),
    api_client=Depends(get_api_client),
):
    await _check_admin(user_id, api_client)
    ok = await admin_service.delete_language(language_id, api_client)
    return {"ok": ok}


# ── Words ─────────────────────────────────────────────────────────────────────

@router.get("/languages/{language_id}/words")
async def list_words(
    language_id: str,
    user_id: str = Query(...),
    page: int = Query(1, ge=1),
    api_client=Depends(get_api_client),
):
    await _check_admin(user_id, api_client)
    return await admin_service.get_words_page(language_id, page, api_client)


@router.get("/languages/{language_id}/words/by_number/{number}")
async def word_by_number(
    language_id: str,
    number: int,
    user_id: str = Query(...),
    api_client=Depends(get_api_client),
):
    await _check_admin(user_id, api_client)
    word = await admin_service.get_word_by_number(language_id, number, api_client)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    return word


class WordFieldBody(BaseModel):
    field: str
    value: str


@router.patch("/words/{word_id}")
async def update_word(
    word_id: str,
    body: WordFieldBody,
    user_id: str = Query(...),
    api_client=Depends(get_api_client),
):
    await _check_admin(user_id, api_client)
    if body.field not in EDITABLE_WORD_FIELDS:
        raise HTTPException(status_code=400, detail=f"Field '{body.field}' is not editable")
    ok = await admin_service.update_word_field(word_id, body.field, body.value, api_client)
    return {"ok": ok}


@router.delete("/words/{word_id}")
async def delete_word(
    word_id: str,
    user_id: str = Query(...),
    api_client=Depends(get_api_client),
):
    await _check_admin(user_id, api_client)
    ok = await admin_service.delete_word(word_id, api_client)
    return {"ok": ok}


# ── Export ────────────────────────────────────────────────────────────────────

MIME_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv":  "text/csv",
    "json": "application/json",
}

@router.get("/languages/{language_id}/export")
async def export_words(
    language_id: str,
    user_id: str = Query(...),
    fmt: str = Query("xlsx", alias="format"),
    start: Optional[int] = Query(None),
    end: Optional[int] = Query(None),
    api_client=Depends(get_api_client),
):
    await _check_admin(user_id, api_client)
    if fmt not in MIME_TYPES:
        raise HTTPException(status_code=400, detail="format must be xlsx, csv, or json")
    data = await admin_service.export_words(language_id, fmt, start, end, api_client)
    if data is None:
        raise HTTPException(status_code=502, detail="Export failed")
    return Response(
        content=data,
        media_type=MIME_TYPES[fmt],
        headers={"Content-Disposition": f'attachment; filename="words.{fmt}"'},
    )


# ── Import ────────────────────────────────────────────────────────────────────

@router.post("/languages/{language_id}/import")
async def import_words(
    language_id: str,
    user_id: str = Query(...),
    file: UploadFile = File(...),
    clear_existing: bool = Query(False),
    api_client=Depends(get_api_client),
):
    await _check_admin(user_id, api_client)
    file_data = await file.read()
    result = await admin_service.import_words(
        language_id, file_data, file.filename,
        {"clear_existing": clear_existing},
        api_client,
    )
    if not result["ok"]:
        raise HTTPException(status_code=502, detail=result.get("error", "Import failed"))
    return result
