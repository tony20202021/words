from aiogram import Router
from aiogram.types import CallbackQuery
from app.bls_client.client import get_bls_client

router = Router()


@router.callback_query(lambda c: c.data and c.data.startswith("auth:"))
async def handle_auth_callback(callback: CallbackQuery) -> None:
    parts = callback.data.split(":", 2)
    if len(parts) != 3:
        await callback.answer()
        return

    action, token = parts[1], parts[2]
    bls = get_bls_client()

    if action == "confirm":
        result = await bls.auth_confirm(token)
        if result.get("ok"):
            await callback.message.edit_text("✅ Авторизация подтверждена! Вернитесь в браузер.")
        else:
            reason = result.get("reason", "")
            if reason == "expired":
                await callback.message.edit_text("❌ Токен устарел. Попробуйте войти снова.")
            else:
                await callback.message.edit_text("❌ Токен недействителен.")

    elif action == "deny":
        await bls.auth_deny(token)
        await callback.message.edit_text("❌ Авторизация отклонена.")

    await callback.answer()
