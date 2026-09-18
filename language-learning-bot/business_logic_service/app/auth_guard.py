"""Кто вызывает BLS и вправе ли он действовать за этого пользователя.

До этого модуля BLS верил присланному user_id на слово. Все ручки были открыты
в интернет, и знание чужого идентификатора давало полный доступ к его данным,
а идентификатора админа — к админке.

Вызывающий бывает трёх видов:

  служба  — веб и телеграм, заголовок X-Service-Key. Действуют за любого
            пользователя: они сами его опознают (веб — по подписанной куке,
            бот — по telegram_id). Доверять им по адресу 127.0.0.1 нельзя:
            nginx проксирует ВНЕШНИЕ запросы тоже с 127.0.0.1.
  человек — андроид, заголовок Authorization: Bearer <токен>. Токен выдаётся
            при входе по одноразовому коду из бота и подписан AUTH_SECRET.
  аноним  — ничего не прислал.

Проверка одна на всё приложение (FastAPI dependencies): к её вызову маршрут
уже выбран, поэтому шаблон пути и его параметры известны точно, без разбора
адреса регулярками.

Режим AUTH_MODE (common/auth_keys.py):
  log     — нарушения пишутся в журнал и пропускаются. С него начинаем: видно,
            кто ещё ходит без токена, и никто не отрезан вслепую.
  enforce — нарушения отвергаются: 401 без удостоверения, 403 с чужим.
"""

import base64
import hashlib
import hmac
from typing import Optional, Tuple

from fastapi import HTTPException, Request

from app.logger import setup_logger
from app.services import session_service
from common import auth_keys

logger = setup_logger(__name__)

# Ручки без пользователя: справочники, звук, сам вход по коду.
PUBLIC_ROUTES = frozenset({
    "/health",
    "/version",
    "/languages/",
    "/help",
    "/qr",
    "/hints/schema",
    "/statistics/chart_manifest",
    "/sounds/{sound_path:path}",
    "/auth/mobile/activate",
})

# Ручки, которые зовут только веб и бот. Среди них создание пользователя и
# подтверждение входа в веб — отдать их анониму значит отдать чужие аккаунты.
SERVICE_ROUTES = frozenset({
    "/auth/lookup",
    "/auth/create",
    "/auth/confirm/{token}",
    "/auth/deny/{token}",
    "/auth/status/{token}",
    "/user/get_or_create",
})

# Ручки, где пользователь приходит в теле запроса. /auth/mobile/create сюда, а
# не в служебные: андроид выпускает код для входа в веб — но только для себя.
# Будь она открытой, выпуск кода за чужой user_id с последующей активацией на
# своём телефоне обходил бы всю защиту.
BODY_USER_ROUTES = frozenset({
    "/session/start",
    "/results/batch",
    "/auth/mobile/create",
})

_TOKEN_VERSION = "v1"


# ── токены ───────────────────────────────────────────────────────────────────

def _signature(user_id: str, secret: str) -> str:
    raw = hmac.new(secret.encode(), f"{_TOKEN_VERSION}:{user_id}".encode(),
                   hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def issue_token(user_id: str) -> Optional[str]:
    """Токен пользователя, или None, если ключ подписи не задан."""
    secret = auth_keys.auth_secret()
    if not secret:
        logger.error("AUTH_SECRET не задан — токен выдать нельзя")
        return None
    return f"{user_id}.{_signature(user_id, secret)}"


def verify_token(token: str) -> Optional[str]:
    """user_id из токена, если подпись верна; иначе None."""
    user_id, dot, _ = token.rpartition(".")
    secret = auth_keys.auth_secret()
    if not dot or not user_id or not secret:
        return None
    expected = f"{user_id}.{_signature(user_id, secret)}"
    return user_id if hmac.compare_digest(token, expected) else None


# ── кто вызывает ─────────────────────────────────────────────────────────────

def identify_caller(request: Request) -> Tuple[Optional[str], Optional[str]]:
    """("service", None) | ("user", user_id) | (None, None)."""
    key = request.headers.get("x-service-key", "")
    expected = auth_keys.service_key()
    if key and expected and hmac.compare_digest(key, expected):
        return "service", None
    header = request.headers.get("authorization", "")
    if header[:7].lower() == "bearer ":
        user_id = verify_token(header[7:].strip())
        if user_id:
            return "user", user_id
    return None, None


async def _claimed_user(request: Request, template: str) -> Optional[str]:
    """За какого пользователя просят действовать."""
    params = request.path_params
    if "user_id" in params:
        return params["user_id"]
    if "session_id" in params:
        session = session_service.get_session_by_id(params["session_id"])
        # Нет сессии — нет и чужих данных: ответит сам обработчик (404).
        return session.get("user_id") if session else None
    if template.startswith("/admin"):
        return request.query_params.get("user_id")
    if template in BODY_USER_ROUTES:
        try:
            body = await request.json()   # FastAPI кеширует тело — обработчик его получит
        except Exception:
            return None
        return body.get("user_id") if isinstance(body, dict) else None
    return None


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "?"


def _refuse(request: Request, template: str, kind: Optional[str],
            caller_id: Optional[str], claimed: Optional[str], reason: str) -> None:
    line = (f"auth {reason}: {request.method} {template} "
            f"caller={kind or 'аноним'}:{caller_id or '-'} claimed={claimed or '-'} "
            f"from={_client_ip(request)}")
    if auth_keys.auth_mode() == "enforce":
        logger.warning(line)
        raise HTTPException(status_code=401 if kind is None else 403,
                            detail="Not authorized")
    logger.warning(line + " [режим журнала: пропущено]")


async def authorize(request: Request) -> None:
    """Проверка на все ручки BLS. Подключена в main.py как зависимость приложения."""
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    if template is None or template in PUBLIC_ROUTES:
        return

    kind, caller_id = identify_caller(request)
    if kind == "service":
        return

    if template in SERVICE_ROUTES:
        _refuse(request, template, kind, caller_id, None, "служебная ручка")
        return

    claimed = await _claimed_user(request, template)
    if claimed is None:
        return
    if kind == "user" and caller_id == claimed:
        return
    _refuse(request, template, kind, caller_id, claimed,
            "нет удостоверения" if kind is None else "чужой пользователь")
