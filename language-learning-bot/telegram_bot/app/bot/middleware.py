"""
UserMiddleware: resolves Telegram user → BLS user_id on every update.
Injects bls_user_id into handler data so handlers never call get_or_create_user themselves.
"""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from app.bls_client.client import BLSClient


class UserMiddleware(BaseMiddleware):
    def __init__(self, bls: BLSClient) -> None:
        self._bls = bls
        self._cache: Dict[int, str] = {}  # telegram_id → bls_user_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user: User | None = data.get("event_from_user")
        if tg_user and tg_user.id not in self._cache:
            result = await self._bls.get_or_create_user(
                tg_user.id, tg_user.username, tg_user.first_name, tg_user.last_name
            )
            data_obj = result.get("data") or {}
            bls_id = (data_obj.get("id") or data_obj.get("user_id")
                      or (data_obj.get("user_data") or {}).get("id"))
            # Кэшируем ТОЛЬКО удачный ответ. Раньше при недоступном BLS сюда
            # подставлялся telegram_id и оседал в кэше навсегда: после
            # восстановления сервиса повторный запрос уже не делался, и человек
            # до перезапуска процесса работал с несуществующим аккаунтом —
            # прогресс уходил в никуда, а внешне всё выглядело исправным.
            if result.get("status") == 200 and bls_id:
                self._cache[tg_user.id] = bls_id

        if tg_user:
            # Подстановка telegram_id остаётся как аварийный ход на текущий
            # апдейт, но она НЕ запоминается: следующий апдейт попробует снова.
            data["bls_user_id"] = self._cache.get(tg_user.id, str(tg_user.id))

        return await handler(event, data)
