"""
Web Frontend — FastAPI + Jinja2 + HTMX. Port: 8548
"""

import logging
import httpx
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.templating import templates, __version__

from app.routers import auth, languages, study, settings, admin, info

# Этим ключом подписывается сессионная кука, в которой лежат user_id и is_admin.
# Значение по умолчанию делало подделку тривиальной: зная строку, кто угодно
# подписывает куку с чужим user_id и is_admin=true и получает чужой аккаунт, а с
# админским id — удаление языков, импорт с очисткой и рассылку. Заглушка в коде
# опаснее отсутствия ключа: отсутствие видно сразу, а заглушка молча работает.
PLACEHOLDER_KEYS = {
    "change-me-in-production", "change-me-in-production-please",
    "secret", "changeme", "",
}
SECRET_KEY = os.environ.get("SECRET_KEY", "")
if SECRET_KEY in PLACEHOLDER_KEYS:
    raise RuntimeError(
        "SECRET_KEY не задан или оставлен заглушкой. Этим ключом подписывается "
        "сессионная кука с user_id и is_admin — с известным значением подделать "
        "её может кто угодно. Сгенерируйте: python -c \"import secrets; "
        "print(secrets.token_urlsafe(48))\" и положите в .env")

app = FastAPI(title="Language Learning Web", version=__version__)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

BASE = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


@app.middleware("http")
async def no_store_dynamic_pages(request: Request, call_next):
    """Prevent browsers from caching dynamic pages (e.g. /stats, /languages) so
    freshly added languages/progress always show. Static assets stay cacheable."""
    response = await call_next(request)
    if not request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    """
    Отказ BLS не должен превращаться в белый экран с 500.

    Веб-фронтенд stateless и полностью зависит от BLS: если тот недоступен,
    падает любой маршрут. Раньше исключение улетало наружу, и пользователь
    видел стандартную страницу ошибки без единой подсказки, что делать.
    Теперь — понятное сообщение и кнопки «Повторить» и «К списку языков».

    HTMX-запросы получают тот же фрагмент, чтобы ошибка отрисовалась внутри
    страницы, а не заменила её целиком.
    """
    logging.exception("необработанная ошибка на %s", request.url.path)
    # httpx свои ошибки от встроенных ConnectionError/TimeoutError не наследует
    # (httpx.ConnectError -> TransportError -> HTTPError -> Exception), поэтому
    # проверка на встроенные типы не срабатывала никогда, и недоступность BLS —
    # единственный случай, ради которого ветка и заводилась, — отдавала 500.
    unreachable = (ConnectionError, TimeoutError, httpx.TransportError)
    status = 503 if isinstance(exc, unreachable) else 500
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "title": "Сервер недоступен",
            "message": "Не удалось получить данные. "
                       "Попробуйте повторить через несколько секунд.",
            "detail": f"{type(exc).__name__}: {exc}",
        },
        status_code=status,
    )


app.include_router(auth.router)
app.include_router(languages.router)
app.include_router(study.router)
app.include_router(settings.router)
app.include_router(admin.router)
app.include_router(info.router)


@app.get("/")
async def index(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/languages", status_code=302)
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}
