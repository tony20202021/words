import asyncio
import os
from urllib.parse import quote
from fastapi import APIRouter, Request, Form, Query, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, Response
from app.templating import templates
from pathlib import Path
import httpx
from app.bls_client import get_bls_client

HINT_TYPES = {
    "meaning":             ("🧠", "Ассоциация (рус)"),
    "phoneticsound":       ("🎵", "Звучание по слогам"),
    "phoneticassociation": ("💡", "Ассоциация фонетики"),
    "writing":             ("✍️", "Написание"),
}

# Desired display order for extra_content groups in the web UI
_EXTRA_ORDER = ["radicals", "references", "tones"]


def _prepare_card(card: dict) -> None:
    """Reorder extra_content groups for display (radicals → references → tones).
    Reference filtering by word number is handled by the BLS card_builder."""
    extra = card.get("extra_content") or []
    if not extra:
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

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8500")

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
    new_session = resp is None
    if new_session:
        settings = {"use_check_date": False, "skip_marked": False, "start_word": 1} if force else None
        resp = await bls.start_session(user_id, language_id, settings=settings)

    if resp is None:
        return templates.TemplateResponse("study.html", {
            "request": request, "language_id": language_id,
            "card": None, "no_words": False, "error": "Не удалось запустить сессию.",
            "lang": {}, "words_for_today": 0,
        })

    card = resp.get("card")

    if card is None:
        stats = await bls.get_statistics(user_id, language_id)
        return templates.TemplateResponse("study.html", {
            "request": request, "language_id": language_id,
            "card": None, "no_words": True, "error": None,
            "lang": {}, "words_for_today": stats.get("words_for_today", 0),
        })

    ctx = await _page_ctx(bls, user_id, language_id)
    wft_key = f"wft_{language_id}"
    if new_session or force:
        # Set words_for_today once at session start; preserve it across page refreshes
        request.session[wft_key] = ctx["words_for_today"]
    else:
        ctx["words_for_today"] = request.session.get(wft_key, ctx["words_for_today"])

    _prepare_card(card)
    return templates.TemplateResponse("study.html", {
        "request": request, "language_id": language_id,
        "card": card, "no_words": False, "error": None, **ctx,
    })


# ── HTMX card endpoints — return word_card.html partial ──────────────────────

def _session_error(language_id: str) -> HTMLResponse:
    return HTMLResponse(
        f"<p class='text-danger'>Сессия не найдена. "
        f"<a href='/study/{language_id}'>Начать заново</a></p>"
    )


async def _card_partial(request, bls, user_id, language_id, resp):
    ctx = await _page_ctx(bls, user_id, language_id)
    ctx["words_for_today"] = request.session.get(f"wft_{language_id}", ctx["words_for_today"])
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
    setting_key = {
        "meaning":             "show_hint_meaning",
        "phoneticsound":       "show_hint_phoneticsound",
        "phoneticassociation": "show_hint_phoneticassociation",
        "writing":             "show_hint_writing",
    }
    enabled_types = {ht: v for ht, v in HINT_TYPES.items()
                     if hint_settings.get(setting_key[ht], False)}
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
