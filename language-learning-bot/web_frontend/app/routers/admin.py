"""
Web admin router. All endpoints require session user to have admin rights.
"""

from fastapi import APIRouter, Request, Form, UploadFile, File, Query
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional
from app.bls_client import get_bls_client

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

MIME_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv":  "text/csv",
    "json": "application/json",
}

WORD_FIELD_LABELS = {
    "foreign":       "Иностранное слово",
    "translation":   "Перевод",
    "transcription": "Транскрипция",
    "radicals":      "Радикалы",
    "references":    "Ссылки",
    "tones":         "Тоны",
    "sounds":        "Звуки",
    "number":        "Номер слова",
}


def _require_admin(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None, RedirectResponse("/login", status_code=302)
    if not request.session.get("is_admin"):
        return None, RedirectResponse("/languages", status_code=302)
    return user_id, None


def _render(request: Request, template: str, ctx: dict):
    ctx["request"] = request
    return templates.TemplateResponse(template, ctx)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("")
@router.get("/")
async def dashboard(request: Request):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    stats = await bls.admin_global_stats(user_id)
    return _render(request, "admin/dashboard.html", {"stats": stats})


# ── Languages ─────────────────────────────────────────────────────────────────

@router.get("/languages")
async def language_list(request: Request):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    stats = await bls.admin_global_stats(user_id)
    return _render(request, "admin/languages.html", {"languages": stats.get("languages", [])})


@router.post("/languages/create")
async def create_language(
    request: Request,
    name_ru: str = Form(...),
    name_foreign: str = Form(...),
):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    await bls.admin_create_language(user_id, name_ru.strip(), name_foreign.strip())
    return RedirectResponse("/admin/languages", status_code=302)


@router.get("/languages/{language_id}")
async def language_detail(request: Request, language_id: str):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    lang = await bls.admin_language_detail(user_id, language_id)
    return _render(request, "admin/language_detail.html", {
        "lang": lang, "language_id": language_id
    })


@router.post("/languages/{language_id}/update")
async def update_language(
    request: Request,
    language_id: str,
    name_ru: str = Form(...),
    name_foreign: str = Form(...),
):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    await bls.admin_update_language(user_id, language_id, name_ru.strip(), name_foreign.strip())
    return RedirectResponse(f"/admin/languages/{language_id}", status_code=302)


@router.post("/languages/{language_id}/delete")
async def delete_language(request: Request, language_id: str):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    await bls.admin_delete_language(user_id, language_id)
    return RedirectResponse("/admin/languages", status_code=302)


# ── Words ─────────────────────────────────────────────────────────────────────

@router.get("/languages/{language_id}/words")
async def word_list(request: Request, language_id: str, page: int = Query(1, ge=1),
                    number: Optional[int] = Query(None)):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect
    bls = get_bls_client()

    found_word = None
    if number is not None:
        found_word = await bls.admin_word_by_number(user_id, language_id, number)

    data = await bls.admin_list_words(user_id, language_id, page)
    lang = await bls.admin_language_detail(user_id, language_id)
    return _render(request, "admin/words.html", {
        "lang": lang,
        "language_id": language_id,
        "data": data,
        "found_word": found_word,
        "search_number": number,
        "field_labels": WORD_FIELD_LABELS,
    })


@router.post("/words/{word_id}/update")
async def update_word(
    request: Request,
    word_id: str,
    language_id: str = Form(...),
    field: str = Form(...),
    value: str = Form(...),
):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    await bls.admin_update_word(user_id, word_id, field, value.strip())
    return RedirectResponse(f"/admin/languages/{language_id}/words", status_code=302)


@router.post("/words/{word_id}/delete")
async def delete_word(request: Request, word_id: str, language_id: str = Form(...)):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    await bls.admin_delete_word(user_id, word_id)
    return RedirectResponse(f"/admin/languages/{language_id}/words", status_code=302)


# ── Export ────────────────────────────────────────────────────────────────────

@router.get("/languages/{language_id}/export")
async def export_words(
    request: Request,
    language_id: str,
    fmt: str = Query("xlsx"),
    start: Optional[int] = Query(None),
    end: Optional[int] = Query(None),
):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    data = await bls.admin_export_words(user_id, language_id, fmt, start, end)
    if data is None:
        return _render(request, "admin/language_detail.html", {"error": "Экспорт не удался"})
    mime = MIME_TYPES.get(fmt, "application/octet-stream")
    return Response(
        content=data, media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="words.{fmt}"'},
    )


# ── Import ────────────────────────────────────────────────────────────────────

@router.post("/languages/{language_id}/import")
async def import_words(
    request: Request,
    language_id: str,
    file: UploadFile = File(...),
    clear_existing: bool = Form(False),
):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    file_data = await file.read()
    result = await bls.admin_import_words(user_id, language_id, file_data, file.filename, clear_existing)
    lang = await bls.admin_language_detail(user_id, language_id)
    msg = "Импорт выполнен успешно." if result.get("ok") else f"Ошибка импорта: {result.get('error')}"
    return _render(request, "admin/language_detail.html", {
        "lang": lang, "language_id": language_id,
        "import_message": msg, "import_ok": result.get("ok"),
    })


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users")
async def user_list(request: Request, page: int = Query(1, ge=1)):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    data = await bls.admin_list_users(user_id, page)
    return _render(request, "admin/users.html", {"data": data})


@router.get("/users/{target_user_id}")
async def user_detail(request: Request, target_user_id: str):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    detail = await bls.admin_user_details(user_id, target_user_id)
    return _render(request, "admin/user_detail.html", {"detail": detail})


@router.post("/users/{target_user_id}/toggle_admin")
async def toggle_admin(request: Request, target_user_id: str, is_admin: bool = Form(...)):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    await bls.admin_toggle_admin(user_id, target_user_id, is_admin)
    return RedirectResponse(f"/admin/users/{target_user_id}", status_code=302)


# ── Broadcast ─────────────────────────────────────────────────────────────────

@router.get("/broadcast")
async def broadcast_page(request: Request):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect
    return _render(request, "admin/broadcast.html", {})


@router.post("/broadcast/send")
async def broadcast_send(request: Request, text: str = Form(...)):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect

    bls = get_bls_client()
    users_data = await bls.admin_list_users(user_id, page=1)
    total_pages = users_data.get("total_pages", 1)

    import os, httpx as _httpx
    bot_token = os.environ.get("BOT_TOKEN", "")
    sent = 0
    errors = []

    for pg in range(1, total_pages + 1):
        page_data = await bls.admin_list_users(user_id, page=pg)
        for u in page_data.get("users", []):
            tg_id = u.get("telegram_id")
            if not tg_id or tg_id == int(user_id.split("-")[0] if "-" in user_id else 0):
                continue
            if not bot_token:
                break
            try:
                async with _httpx.AsyncClient(timeout=5) as hc:
                    r = await hc.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={"chat_id": tg_id, "text": text},
                    )
                if r.json().get("ok"):
                    sent += 1
                else:
                    errors.append(f"tg:{tg_id} → {r.json().get('description', '?')}")
            except Exception as e:
                errors.append(f"tg:{tg_id} → {e}")

    return _render(request, "admin/broadcast.html", {
        "sent": sent, "errors": errors, "done": True,
    })


# ── Diagnostics ───────────────────────────────────────────────────────────────

@router.get("/diagnostics")
async def diagnostics(request: Request):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect

    import psutil, sys, platform

    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    cpu_pct = psutil.cpu_percent(interval=0.3)
    cpu_count = psutil.cpu_count(logical=True)

    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            u = psutil.disk_usage(part.mountpoint)
            disks.append({
                "mount": part.mountpoint,
                "total": round(u.total / 1024**3, 1),
                "used": round(u.used / 1024**3, 1),
                "pct": u.percent,
            })
        except PermissionError:
            pass

    import httpx as _httpx
    services = []
    for name, url in [
        ("Backend (API)", "http://localhost:8500/api/health"),
        ("BLS", "http://localhost:8700/health"),
        ("Web Frontend", "http://localhost:8800/health"),
    ]:
        try:
            r = await _httpx.AsyncClient(timeout=2).get(url)
            ok = r.status_code == 200
        except Exception:
            ok = False
        services.append({"name": name, "ok": ok, "url": url})

    ctx = {
        "cpu_pct": cpu_pct,
        "cpu_count": cpu_count,
        "ram_total": round(vm.total / 1024**3, 1),
        "ram_used": round(vm.used / 1024**3, 1),
        "ram_pct": vm.percent,
        "swap_total": round(swap.total / 1024**3, 1),
        "swap_used": round(swap.used / 1024**3, 1),
        "disks": disks,
        "services": services,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.platform(),
    }
    return _render(request, "admin/diagnostics.html", ctx)
