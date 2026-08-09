"""
Общие проверки доступа для веб-маршрутов.

Функция _require_user была скопирована дословно в четыре роутера. Копии пока не
разошлись, но менять правило входа пришлось бы в четырёх местах, а заметить, что
одну забыли, было бы нечем — маршрут просто продолжал бы пускать.
"""

from fastapi import Request
from fastapi.responses import RedirectResponse


def require_user(request: Request):
    """(user_id, None) для вошедшего, иначе (None, редирект на вход)."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None, RedirectResponse("/login", status_code=302)
    return user_id, None


def require_admin(request: Request):
    """(user_id, None) для админа, иначе (None, редирект)."""
    user_id, redirect = require_user(request)
    if redirect:
        return None, redirect
    if not request.session.get("is_admin"):
        return None, RedirectResponse("/", status_code=302)
    return user_id, None
