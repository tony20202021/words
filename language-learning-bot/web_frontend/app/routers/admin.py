"""
Web admin router. All endpoints require session user to have admin rights.
"""

from fastapi import APIRouter, Request, Form, UploadFile, File, Query
from fastapi.responses import RedirectResponse, Response
from app.access import require_admin as _require_admin
from app.templating import templates
from typing import Annotated, Optional
from pydantic import BeforeValidator
from app.bls_client import get_bls_client


def _blank_to_none(value):
    """
    Пустое поле формы приходит как '' и для необязательного числа значит «не задано».

    Форма экспорта шлёт start и end всегда, даже пустыми (<input type="number">
    без значения), а Optional[int] на '' отвечал 422 — то есть кнопка «Скачать»
    без указанного диапазона просто не работала.
    """
    return None if isinstance(value, str) and not value.strip() else value


# Query() обязан лежать внутри Annotated: с Query в значении по умолчанию
# FastAPI теряет BeforeValidator и снова отвечает 422 на пустую строку.
OptionalNumber = Annotated[Optional[int], BeforeValidator(_blank_to_none), Query()]

router = APIRouter(prefix="/admin")

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
    # Форма в language_detail.html шлёт поле «format», а ручка читала только
    # «fmt» — выбор CSV/JSON молча игнорировался и всегда скачивался xlsx.
    fmt_from_form: Optional[str] = Query(None, alias="format"),
    start: OptionalNumber = None,
    end: OptionalNumber = None,
):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect
    fmt = fmt_from_form or fmt
    bls = get_bls_client()
    data = await bls.admin_export_words(user_id, language_id, fmt, start, end)
    if data is None:
        # Шаблон страницы языка начинается с lang.name_ru и language_id: без них
        # сообщение «Экспорт не удался» само падало на UndefinedError, и вместо
        # него админ видел 500.
        lang = await bls.admin_language_detail(user_id, language_id)
        return _render(request, "admin/language_detail.html", {
            "lang": lang, "language_id": language_id,
            "error": "Экспорт не удался",
        })
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
    bls = get_bls_client()
    return _render(request, "admin/broadcast.html", {
        "users": await _broadcast_users(bls, user_id),
        "languages": await bls.get_languages(),
    })


async def _broadcast_users(bls, admin_id: str) -> list:
    """Все, кому вообще можно написать: есть telegram_id и это не сам админ."""
    out = []
    первая = await bls.admin_list_users(admin_id, page=1)
    for pg in range(1, (первая.get("total_pages", 1) or 1) + 1):
        data = первая if pg == 1 else await bls.admin_list_users(admin_id, page=pg)
        for u in data.get("users", []):
            uid = str(u.get("id") or u.get("user_id") or "")
            if not u.get("telegram_id") or uid == str(admin_id):
                continue
            имя = " ".join(x for x in (u.get("first_name"), u.get("last_name")) if x)
            out.append({"id": uid, "telegram_id": u.get("telegram_id"),
                        "name": имя or u.get("username") or uid,
                        "username": u.get("username") or ""})
    return out


async def _wants_messages(bls, uid: str, language_id: str) -> bool:
    """
    Согласен ли человек получать это письмо.

    Настройка «Получать сообщения» живёт ПО ЯЗЫКУ, а рассылка языка может и не
    касаться — отсюда несоответствие, которое заметил владелец. Разрешено так:

      выбран язык            спрашиваем настройку ИМЕННО ЭТОГО языка;
      независимо от языка    не спрашиваем вовсе, шлём всем.

    Второе — решение владельца: «в этом режиме вообще не проверять языки,
    рассылать всегда, это будут какие-нибудь общесистемные сообщения».
    Настройка про язык и не может отвечать за сообщение о самой службе.

    Раньше настройку не читали НИГДЕ: рассылка шла всем подряд, и выключивший
    её человек всё равно получал письма про свой язык. Настройка была
    обещанием, которого код не выполнял.
    """
    if not language_id or language_id == "any":
        return True
    s = await bls.get_settings(uid, language_id)
    return bool(s.get("receive_messages", True))


@router.get("/broadcasts")
async def broadcasts_page(request: Request):
    """История отправленных рассылок."""
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect
    bls = get_bls_client()
    return _render(request, "admin/broadcasts.html", {
        "broadcasts": await bls.get_broadcasts(user_id, limit=100),
    })


@router.post("/broadcast/send")
async def broadcast_send(request: Request, text: str = Form(...),
                         recipient: str = Form("all"),
                         language_id: str = Form("any")):
    user_id, redirect = _require_admin(request)
    if redirect:
        return redirect

    import os
    import httpx as _httpx

    bls = get_bls_client()
    languages = await bls.get_languages()
    все = await _broadcast_users(bls, user_id)
    цель = все if recipient == "all" else [u for u in все if u["id"] == recipient]

    bot_token = os.environ.get("BOT_TOKEN", "")
    sent, errors, skipped = 0, [], []

    if not цель:
        errors.append("получатель не найден — возможно, у него нет телеграма")
    if not bot_token:
        errors.append("BOT_TOKEN не задан — отправлять нечем")

    for u in цель if bot_token else []:
        if not await _wants_messages(bls, u["id"], language_id):
            # Пропуск называется вслух: иначе «отправлено 0» выглядит поломкой,
            # а человек просто отказался от сообщений.
            skipped.append(f"{u['name']} — выключено «Получать сообщения» "
                           f"для этого языка")
            continue
        try:
            async with _httpx.AsyncClient(timeout=5) as hc:
                r = await hc.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": u["telegram_id"], "text": text},
                )
            if r.json().get("ok"):
                sent += 1
            else:
                errors.append(f"{u['name']} → {r.json().get('description', '?')}")
        except Exception as e:
            errors.append(f"{u['name']} → {type(e).__name__}")

    # История пишется всегда, в том числе когда не ушло ничего: «отправлено 0»
    # без записи выглядит как сбой, а причина — отказ человека от сообщений —
    # видна только здесь. Отчёт на странице живёт до перезагрузки, запись —
    # сколько нужно.
    кому = "всем" if recipient == "all" else next(
        (u["name"] for u in цель), recipient)
    язык = "независимо от языка" if language_id == "any" else next(
        (l.get("name_ru", "") for l in languages if str(l.get("id")) == language_id),
        language_id)
    try:
        await bls.add_broadcast(user_id, {
            "text": text,
            "sent_by": user_id,
            "recipient": recipient,
            "recipient_name": кому,
            "language_id": language_id,
            "language_name": язык,
            "sent_count": sent,
            "skipped": skipped,
            "errors": errors,
        })
    except Exception as e:                      # история не должна ломать отправку
        errors.append(f"рассылка ушла, но в историю не записалась: "
                      f"{type(e).__name__}")

    return _render(request, "admin/broadcast.html", {
        "sent": sent, "errors": errors, "skipped": skipped, "done": True,
        "users": все, "languages": languages,
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
        if part.mountpoint.startswith("/snap/") or part.mountpoint == "/boot/efi":
            continue
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

    # top-5 by CPU (two-pass: init → wait → read) and by RSS
    import asyncio as _asyncio
    _snapshot = {}
    for p in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            p.cpu_percent()          # prime the counter
            _snapshot[p.pid] = p
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    await _asyncio.sleep(0.3)        # let the counter accumulate

    _PORT_SERVICE = {
        "8573": "Backend API",
        "8531": "BLS",
        "8548": "Web Frontend",
        "8527": "MongoDB",
    }

    def _proc_info(p):
        """Return (hint, service) for a process."""
        import re as _re
        try:
            cmd = p.cmdline()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "", ""
        full = " ".join(cmd)
        binary = cmd[0] if cmd else ""

        # ── service label ──────────────────────────────────────────────
        service = ""

        # uvicorn → identify by port
        if "uvicorn" in full:
            port = ""
            for i, tok in enumerate(cmd):
                if tok == "--port" and i + 1 < len(cmd):
                    port = cmd[i + 1]
            if not port:
                m = _re.search(r"--port[= ](\d+)", full)
                port = m.group(1) if m else ""
            hint = f":{port}" if port else "uvicorn"
            service = _PORT_SERVICE.get(port, f"uvicorn :{port}")
            return hint, service

        # python scripts
        for tok in cmd:
            if tok.endswith(".py") and not tok.startswith("-"):
                stem = tok.split("/")[-1].removesuffix(".py")
                if stem == "main_frontend":
                    service = "Telegram Bot (старый)"
                elif stem == "main_backend":
                    service = "Backend API"
                elif "process-name" in full:
                    m = _re.search(r"--process-name[= ](\S+)", full)
                    service = m.group(1) if m else stem
                if stem and stem != p.name():
                    return stem, service

        # well-known binaries
        if "claude-code" in binary or binary.endswith("/claude"):
            return "Claude Code", "Claude Code"
        if ".cursor-server/bin" in binary or ".vscode-server/bin" in binary:
            # distinguish Cursor node roles
            if "--type=extensionHost" in full:
                return "Cursor IDE", "Extension Host"
            if "htmlServerMain" in full:
                return "Cursor IDE", "HTML Language Server"
            if "cursorpyright" in full or "pylance" in full:
                return "Cursor IDE", "Python Language Server"
            return "Cursor IDE", "Cursor IDE"
        if ".vscode-server" in full or ".cursor-server" in full:
            return "Cursor IDE", "Cursor IDE"

        # mongod
        if p.name() in ("mongod", "mongos"):
            return "mongod", "MongoDB"

        # node .js
        for tok in cmd:
            if tok.endswith(".js") and not tok.startswith("-"):
                stem = tok.split("/")[-1].removesuffix(".js")
                return stem, ""

        # fallback cwd
        try:
            cwd = p.cwd()
            parts = [s for s in cwd.split("/") if s]
            hint = "/".join(parts[-2:]) if len(parts) >= 2 else "/".join(parts)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            hint = ""
        return hint, service

    all_procs = []
    for pid, p in _snapshot.items():
        try:
            cpu = p.cpu_percent()
            mi = p.memory_info()
            try:
                cmdline = " ".join(p.cmdline())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                cmdline = ""
            hint, service = _proc_info(p)
            all_procs.append({
                "pid": pid,
                "name": p.name(),
                "hint": hint,
                "service": service,
                "cpu": round(cpu or 0, 1),
                "mem_mb": round(mi.rss / 1024**2, 1) if mi else 0,
                "cmdline": cmdline,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    top_cpu = sorted(all_procs, key=lambda x: x["cpu"], reverse=True)[:5]
    top_mem = sorted(all_procs, key=lambda x: x["mem_mb"], reverse=True)[:10]

    import httpx as _httpx
    import socket as _socket

    def _port_open(port: int) -> bool:
        try:
            with _socket.create_connection(("localhost", port), timeout=1):
                return True
        except OSError:
            return False

    def _proc_running(*keywords) -> bool:
        """Return True if any process has all keywords in its cmdline string."""
        for p in psutil.process_iter():
            try:
                cmd = " ".join(p.cmdline())
                if all(kw in cmd for kw in keywords):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    services = []
    for name, url, disabled in [
        ("MongoDB",                                    None,                               False),
        ("Backend API",                                "http://localhost:8573/api/health", False),
        ("BLS (Business Logic Service)",               "http://localhost:8531/health",     False),
        ("Web Frontend",                               "http://localhost:8548/health",     False),
        ("Telegram Bot (новый)",                       None,                               False),
        ("Telegram Bot (старый)",                      None,                               False),
        ("Генерация картинок",                         None,                               True),
    ]:
        if disabled:
            services.append({"name": name, "ok": False, "disabled": True})
            continue
        if url is None:
            if name == "MongoDB":
                ok = _port_open(8527)
            elif "новый" in name:
                ok = _proc_running("telegram_bot", "app.main")
            elif "старый" in name:
                ok = _proc_running("main_frontend")
            else:
                ok = False
            services.append({"name": name, "ok": ok, "disabled": False})
            continue
        try:
            r = await _httpx.AsyncClient(timeout=2).get(url)
            ok = r.status_code == 200
        except Exception:
            ok = False
        services.append({"name": name, "ok": ok, "disabled": False})

    ctx = {
        "cpu_pct": cpu_pct,
        "cpu_count": cpu_count,
        "ram_total": round(vm.total / 1024**3, 1),
        "ram_used": round(vm.used / 1024**3, 1),
        "ram_pct": vm.percent,
        "swap_total": round(swap.total / 1024**3, 1),
        "swap_used": round(swap.used / 1024**3, 1),
        "disk_used": round(sum(d["used"] for d in disks), 1),
        "disk_total": round(sum(d["total"] for d in disks), 1),
        "disk_pct": round(max((d["pct"] for d in disks), default=0), 1),
        "disks": disks,
        "services": services,
        "top_cpu": top_cpu,
        "top_mem": top_mem,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.platform(),
    }
    return _render(request, "admin/diagnostics.html", ctx)
