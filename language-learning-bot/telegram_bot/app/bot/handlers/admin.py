"""
Admin commands for the Telegram bot.
Requires is_admin=True for the calling user.
"""

import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.bls_client.client import get_bls_client

router = Router()


class AdminState(StatesGroup):
    broadcast_input = State()


def _admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика",   callback_data="admin:stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users:1")],
        [InlineKeyboardButton(text="📢 Рассылка",     callback_data="admin:broadcast")],
    ])


async def _check_admin(bls_user_id: str) -> bool:
    return await get_bls_client().is_admin(bls_user_id)


# ── /admin command ────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, bls_user_id: str) -> None:
    if not await _check_admin(bls_user_id):
        await message.answer("❌ У вас нет прав администратора.")
        return
    await message.answer("⚙️ <b>Панель администратора</b>", parse_mode="HTML",
                         reply_markup=_admin_menu_keyboard())


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, bls_user_id: str) -> None:
    if not await _check_admin(bls_user_id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    bls = get_bls_client()
    stats = await bls.admin_global_stats(bls_user_id)

    lines = [f"📊 <b>Статистика бота</b>",
             f"Пользователей: {stats.get('total_users', '?')}",
             f"Языков: {len(stats.get('languages', []))}",
             ""]
    for l in stats.get("languages", []):
        lines.append(f"• {l['name_ru']}: {l['word_count']} слов, {l['active_users']} активных")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Меню", callback_data="admin:menu")]
    ])
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=kb)
    await callback.answer()


# ── Users ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:users:"))
async def admin_users(callback: CallbackQuery, bls_user_id: str) -> None:
    if not await _check_admin(bls_user_id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    page = int(callback.data.split(":")[-1])
    bls = get_bls_client()
    data = await bls.admin_list_users(bls_user_id, page)
    users = data.get("users", [])
    total_pages = data.get("total_pages", 1)

    lines = [f"👥 <b>Пользователи</b> (стр. {page}/{total_pages})", ""]
    for u in users:
        admin_mark = " 👑" if u.get("is_admin") else ""
        name = f"{u.get('first_name', '')} {u.get('last_name', '') or ''}".strip()
        uname = f"@{u['username']}" if u.get("username") else ""
        lines.append(f"• {name} {uname}{admin_mark} — tg:{u.get('telegram_id', '?')}")
        lines.append(f"  ID: <code>{u.get('id', '?')}</code>")

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="←", callback_data=f"admin:users:{page-1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="→", callback_data=f"admin:users:{page+1}"))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        nav,
        [InlineKeyboardButton(text="← Меню", callback_data="admin:menu")],
    ])
    await callback.message.edit_text("\n".join(lines) or "Нет пользователей",
                                     parse_mode="HTML", reply_markup=kb)
    await callback.answer()


# ── Broadcast ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    if not await _check_admin(bls_user_id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminState.broadcast_input)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отмена", callback_data="admin:menu")]
    ])
    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\nВведите текст сообщения:", parse_mode="HTML", reply_markup=kb
    )
    await callback.answer()


@router.message(AdminState.broadcast_input)
async def admin_broadcast_send(message: Message, state: FSMContext, bls_user_id: str) -> None:
    if not await _check_admin(bls_user_id):
        await state.clear()
        return

    text = message.text or ""
    bot_token = os.environ.get("BOT_TOKEN", "")
    bls = get_bls_client()

    await state.clear()
    status_msg = await message.answer("📤 Отправляю...")

    sent = 0
    errors = 0
    page = 1

    import aiohttp
    while True:
        data = await bls.admin_list_users(bls_user_id, page)
        users = data.get("users", [])
        if not users:
            break
        for u in users:
            tg_id = u.get("telegram_id")
            if not tg_id or not bot_token:
                continue
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={"chat_id": tg_id, "text": text},
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as resp:
                        if (await resp.json()).get("ok"):
                            sent += 1
                        else:
                            errors += 1
            except Exception:
                errors += 1
        if page >= data.get("total_pages", 1):
            break
        page += 1

    await status_msg.edit_text(
        f"✅ Рассылка завершена.\nОтправлено: {sent}, ошибок: {errors}",
        reply_markup=_admin_menu_keyboard(),
    )


# ── Back to menu ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:menu")
async def admin_menu_back(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    await state.clear()
    await callback.message.edit_text("⚙️ <b>Панель администратора</b>", parse_mode="HTML",
                                     reply_markup=_admin_menu_keyboard())
    await callback.answer()
