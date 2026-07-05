import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter, Request, Form, Query, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, Response
from app.templating import templates
import httpx
from app.bls_client import get_bls_client

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from common.hint_catalog import hint_types_ordered, setting_key_for

HINT_TYPES = hint_types_ordered()

# Desired display order for extra_content groups in the web UI
_EXTRA_ORDER = ["radicals", "references", "tones"]


def _group_extra_items(items: list) -> list:
    """Split flat extra_content list into per-group blocks for separate UI cards."""
    groups_list: list = []
    current_group = None
    current_items: list = []
    for item in items:
        g = item.get("group", "")
        if g != current_group:
            if current_items:
                groups_list.append({"group": current_group, "items": current_items})
            current_group = g
            current_items = [item]
        else:
            current_items.append(item)
    if current_items:
        groups_list.append({"group": current_group, "items": current_items})
    return groups_list


def _prepare_card(card: dict) -> None:
    """Reorder extra_content groups for display (radicals → references → tones).
    Reference filtering by word number is handled by the BLS card_builder."""
    extra = card.get("extra_content") or []
    if not extra:
        card["extra_groups"] = []
        return

    # Group items preserving per-group insertion order
    groups: dict = {}
    group_order: list = []
    for item in extra:
        g = item.get("group", "")
        if g not in groups:
            groups[g] = []
            group_order.append(g)
        groups[g].append(item)

    # Rebuild in desired order (radicals → references → tones), unknown groups appended
    sorted_items: list = []
    for g in _EXTRA_ORDER:
        sorted_items.extend(groups.pop(g, []))
    for g in group_order:
        if g in groups:
            sorted_items.extend(groups.pop(g))

    card["extra_content"] = sorted_items
    card["extra_groups"] = _group_extra_items(sorted_items)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8573")

router = APIRouter()


@router.get("/sound/{sound_path:path}")
async def proxy_sound(sound_path: str):
    encoded = quote(sound_path, safe="").replace(".", "%2E")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND_URL}/api/sounds/{encoded}", timeout=10.0)
    if resp.is_success:
        return Response(content=resp.content, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="Sound not found")


def _require_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None, RedirectResponse("/login", status_code=302)
    return user_id, None


async def _page_ctx(bls, user_id: str, language_id: str) -> dict:
    """Fetch language info + stats for page chrome (header, progress bar)."""
    langs = await bls.get_languages()
    lang = next((l for l in langs if l["id"] == language_id), {})
    stats = await bls.get_statistics(user_id, language_id)
    return {
        "lang": lang,
        "stats": stats,
        "words_for_today": stats.get("words_for_today", 0),
        "words_studied": stats.get("words_studied", 0),
        "total_words": stats.get("total_words", 0),
    }


# ── Pages ─────────────────────────────────────────────────────────────────────

@router.get("/study/{language_id}")
async def study_page(request: Request, language_id: str, force: bool = Query(False)):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect

    bls = get_bls_client()

    if force:
        await bls.end_session(user_id, language_id)

    resp = await bls.get_session(user_id, language_id)
    session_stale = bool(resp and resp.get("session_stale"))
    new_session = resp is None
    if new_session:
        session_mode = "ignore_dates" if force else None
        resp = await bls.start_session(user_id, language_id, session_mode=session_mode)

    if resp is None:
        return templates.TemplateResponse("study.html", {
            "request": request, "language_id": language_id,
            "card": None, "no_words": False, "error": "Не удалось запустить сессию.",
            "lang": {}, "words_for_today": 0, "session_stale": False,
        })

    card = resp.get("card")

    if card is None:
        stats = await bls.get_statistics(user_id, language_id)
        return templates.TemplateResponse("study.html", {
            "request": request, "language_id": language_id,
            "card": None, "no_words": True, "error": None,
            "lang": {}, "words_for_today": stats.get("words_for_today", 0), "session_stale": False,
        })

    ctx = await _page_ctx(bls, user_id, language_id)
    _prepare_card(card)
    return templates.TemplateResponse("study.html", {
        "request": request, "language_id": language_id,
        "card": card, "no_words": False, "error": None, "session_stale": session_stale, **ctx,
    })


# ── HTMX card endpoints — return word_card.html partial ──────────────────────

def _session_error(language_id: str) -> HTMLResponse:
    return HTMLResponse(
        f"<p class='text-danger'>Сессия не найдена. "
        f"<a href='/study/{language_id}'>Начать заново</a></p>"
    )


async def _card_partial(request, bls, user_id, language_id, resp):
    ctx = await _page_ctx(bls, user_id, language_id)
    card = resp.get("card")
    if card:
        _prepare_card(card)
    return templates.TemplateResponse("partials/word_card.html", {
        "request": request, "language_id": language_id,
        "card": card, **ctx,
    })


@router.post("/study/{language_id}/show_answer")
async def show_answer(request: Request, language_id: str):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    session_resp = await bls.get_session(user_id, language_id)
    if not session_resp:
        return _session_error(language_id)
    resp = await bls.show_answer(session_resp["session_id"])
    return await _card_partial(request, bls, user_id, language_id, resp)


@router.post("/study/{language_id}/know")
async def know_word(request: Request, language_id: str):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    session_resp = await bls.get_session(user_id, language_id)
    if not session_resp:
        return _session_error(language_id)
    resp = await bls.know_word(session_resp["session_id"])
    return await _card_partial(request, bls, user_id, language_id, resp)


@router.post("/study/{language_id}/rate")
async def rate_word(request: Request, language_id: str, rating: str = Form(...)):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    session_resp = await bls.get_session(user_id, language_id)
    if not session_resp:
        return _session_error(language_id)
    resp = await bls.rate_word(session_resp["session_id"], rating)

    if resp.get("batch_exhausted"):
        batch_resp = await bls.next_batch(resp["session_id"])
        if batch_resp.get("loaded"):
            resp = batch_resp
        else:
            progress = await bls.get_progress(resp["session_id"])
            return templates.TemplateResponse("partials/completed.html", {
                "request": request, "language_id": language_id, "progress": progress,
            })

    return await _card_partial(request, bls, user_id, language_id, resp)


@router.post("/study/{language_id}/toggle_skip")
async def toggle_skip(request: Request, language_id: str):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    session_resp = await bls.get_session(user_id, language_id)
    if not session_resp:
        return _session_error(language_id)
    resp = await bls.toggle_skip(session_resp["session_id"])
    return await _card_partial(request, bls, user_id, language_id, resp)


@router.post("/study/{language_id}/reconsider")
async def reconsider_word(request: Request, language_id: str):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    session_resp = await bls.get_session(user_id, language_id)
    if not session_resp:
        return _session_error(language_id)
    resp = await bls.reconsider(session_resp["session_id"])

    if resp.get("batch_exhausted"):
        batch_resp = await bls.next_batch(resp["session_id"])
        if batch_resp.get("loaded"):
            resp = batch_resp
        else:
            progress = await bls.get_progress(resp["session_id"])
            return templates.TemplateResponse("partials/completed.html", {
                "request": request, "language_id": language_id, "progress": progress,
            })

    return await _card_partial(request, bls, user_id, language_id, resp)


@router.post("/study/{language_id}/pick_answer")
async def pick_answer(request: Request, language_id: str, selected_word_id: str = Form(...)):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    session_resp = await bls.get_session(user_id, language_id)
    if not session_resp:
        return _session_error(language_id)
    resp = await bls.pick_answer(session_resp["session_id"], selected_word_id)
    if resp.get("batch_exhausted"):
        batch_resp = await bls.next_batch(resp["session_id"])
        if batch_resp.get("loaded"):
            resp = batch_resp
        else:
            progress = await bls.get_progress(resp["session_id"])
            return templates.TemplateResponse("partials/completed.html", {
                "request": request, "language_id": language_id, "progress": progress,
            })
    return await _card_partial(request, bls, user_id, language_id, resp)


@router.post("/study/{language_id}/add_forbidden_pair")
async def add_forbidden_pair(request: Request, language_id: str, bad_word_id: str = Form(...)):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    session_resp = await bls.get_session(user_id, language_id)
    if not session_resp:
        return _session_error(language_id)
    resp = await bls.add_forbidden_pair(session_resp["session_id"], bad_word_id)
    return await _card_partial(request, bls, user_id, language_id, resp)


@router.post("/study/{language_id}/clear_forbidden_pairs")
async def clear_forbidden_pairs(request: Request, language_id: str):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    session_resp = await bls.get_session(user_id, language_id)
    if not session_resp:
        return _session_error(language_id)
    resp = await bls.clear_forbidden_pairs(session_resp["session_id"])
    return await _card_partial(request, bls, user_id, language_id, resp)


@router.post("/study/{language_id}/restart")
async def restart_session(request: Request, language_id: str):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    await bls.end_session(user_id, language_id)
    return RedirectResponse(f"/study/{language_id}", status_code=302)


# ── Hint endpoints ────────────────────────────────────────────────────────────

async def _hints_ctx(bls, user_id: str, language_id: str, word_id: str) -> dict:
    """Fetch hints + filter hint_types to those enabled in settings."""
    hints, hint_settings = await asyncio.gather(
        bls.get_word_hints(user_id, word_id),
        bls.get_hint_settings(user_id, language_id),
    )
    # hint_settings keys: show_hint_meaning, show_hint_phoneticsound, …
    enabled_types = {ht: v for ht, v in HINT_TYPES.items()
                     if hint_settings.get(setting_key_for(ht), False)}
    return {"language_id": language_id, "word_id": word_id,
            "hints": hints, "hint_types": enabled_types}


@router.get("/study/{language_id}/hints/{word_id}")
async def get_hints(request: Request, language_id: str, word_id: str):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    ctx = await _hints_ctx(bls, user_id, language_id, word_id)
    return templates.TemplateResponse("partials/hints_panel.html", {
        "request": request, **ctx,
    })


@router.post("/study/{language_id}/hints/{word_id}/{hint_type}")
async def save_hint(request: Request, language_id: str, word_id: str, hint_type: str,
                    text: str = Form(...)):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    text = text.strip()
    if text:
        await bls.set_word_hint(user_id, word_id, hint_type, text, language_id=language_id)
    ctx = await _hints_ctx(bls, user_id, language_id, word_id)
    return templates.TemplateResponse("partials/hints_panel.html", {
        "request": request, **ctx,
    })


@router.delete("/study/{language_id}/hints/{word_id}/{hint_type}")
async def delete_hint(request: Request, language_id: str, word_id: str, hint_type: str):
    user_id, redirect = _require_user(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    await bls.delete_word_hint(user_id, word_id, hint_type)
    ctx = await _hints_ctx(bls, user_id, language_id, word_id)
    return templates.TemplateResponse("partials/hints_panel.html", {
        "request": request, **ctx,
    })
