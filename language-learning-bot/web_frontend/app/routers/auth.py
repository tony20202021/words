from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional
from app.bls_client import get_bls_client

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/login")
async def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/languages", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    mode: str = Form(...),
    telegram_id: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
):
    bls = get_bls_client()

    if mode == "telegram":
        tg_id = int(telegram_id) if telegram_id and telegram_id.strip() else None
        if not tg_id:
            return _render_login(request, error="Введите Telegram ID")
        result = await bls.auth_lookup(mode="telegram", telegram_id=tg_id)
        if result.get("found") is True:
            return _render_pending(request, result["token"], telegram_id, result.get("message_sent", False))
        # not found → ask to create
        return _render_login(request, not_found=True, mode="telegram", telegram_id=tg_id)

    if mode == "name":
        if not name or not name.strip():
            return _render_login(request, error="Введите имя")
        result = await bls.auth_lookup(mode="name", name=name.strip())
        found = result.get("found")
        if found is True:
            # Log in directly
            await _store_session(request, result["user_id"], first_name=result.get("first_name", ""))
            return RedirectResponse("/languages", status_code=302)
        if found == "multiple":
            return _render_login(request, error="Найдено несколько пользователей — уточните имя",
                                 mode="name", name=name)
        # not found
        return _render_login(request, not_found=True, mode="name", name=name)

    return _render_login(request, error="Неверный режим входа")


@router.post("/auth/create")
async def auth_create(
    request: Request,
    mode: str = Form(...),
    telegram_id: Optional[str] = Form(None),
    first_name: str = Form(...),
):
    tg_id = int(telegram_id) if telegram_id and telegram_id.strip() else None
    bls = get_bls_client()
    result = await bls.auth_create(
        mode=mode,
        first_name=first_name.strip(),
        telegram_id=tg_id,
    )
    if not result.get("ok"):
        return _render_login(request, error="Не удалось создать пользователя")

    if mode == "name":
        await _store_session(request, result["user_id"], first_name=result.get("first_name", ""))
        return RedirectResponse("/languages", status_code=302)

    # telegram: show pending screen
    return _render_pending(request, result["token"], telegram_id, result.get("message_sent", False))


@router.get("/auth/poll")
async def auth_poll(request: Request, token: str):
    """HTMX polling — returns fragment or HX-Redirect on confirmation."""
    bls = get_bls_client()
    result = await bls.auth_status(token)
    status = result.get("status", "error")

    if status == "confirmed":
        await _store_session(request, result["user_id"], result.get("telegram_id"),
                             first_name=result.get("first_name", ""))
        return HTMLResponse(
            '<div id="auth-status">✅ Подтверждено! Переход…</div>',
            headers={"HX-Redirect": "/languages"},
        )

    error_messages = {
        "denied":    "❌ Авторизация отклонена. <a href='/login'>Попробовать снова</a>",
        "expired":   "⏰ Время вышло. <a href='/login'>Попробовать снова</a>",
        "not_found": "❌ Токен не найден. <a href='/login'>Попробовать снова</a>",
        "error":     "❌ Ошибка. <a href='/login'>Попробовать снова</a>",
    }
    if status in error_messages:
        return HTMLResponse(
            f'<div id="auth-status" class="alert alert-danger mt-3">{error_messages[status]}</div>'
        )

    # pending — HTMX will re-poll
    return HTMLResponse(
        f'<div id="auth-status"'
        f' hx-get="/auth/poll?token={token}"'
        f' hx-trigger="every 2s" hx-swap="outerHTML">'
        f'<div class="d-flex align-items-center gap-2 text-muted">'
        f'<div class="spinner-border spinner-border-sm"></div>'
        f'Ожидание подтверждения в Telegram…'
        f'</div></div>'
    )


@router.get("/autologin")
async def autologin(request: Request, telegram_id: int):
    """Direct login via Telegram ID in URL (sent by bot). No confirmation needed."""
    bls = get_bls_client()
    result = await bls.auth_lookup(mode="telegram", telegram_id=telegram_id, direct=True)
    if result.get("found") is True:
        await _store_session(request, result["user_id"], telegram_id, first_name=result.get("first_name", ""))
        return RedirectResponse("/languages", status_code=302)
    return _render_login(request, error="Пользователь не найден. Войдите вручную.")


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)


# ── helpers ───────────────────────────────────────────────────────────────────

async def _store_session(request: Request, user_id: str, telegram_id=None, first_name: str = ""):
    from app.bls_client import get_bls_client as _get_bls
    request.session["user_id"] = user_id
    request.session["first_name"] = first_name or ""
    if telegram_id:
        request.session["telegram_id"] = int(telegram_id)
    request.session["is_admin"] = await _get_bls().is_admin(user_id)


def _render_login(request: Request, error: str = None, not_found: bool = False,
                  mode: str = None, telegram_id: int = None, name: str = None):
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error,
        "not_found": not_found,
        "prev_mode": mode,
        "prev_telegram_id": telegram_id,
        "prev_name": name,
    })


def _render_pending(request: Request, token: str, telegram_id: int, message_sent: bool):
    return templates.TemplateResponse("auth_pending.html", {
        "request": request,
        "token": token,
        "telegram_id": telegram_id,
        "message_sent": message_sent,
    })
