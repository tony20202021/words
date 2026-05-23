import os
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.bls_client.client import BLSClient, get_bls_client
from app.bot.keyboards import build_language_keyboard, build_card_keyboard
from app.bot.renderer import render_card_text

router = Router()


class UserState(StatesGroup):
    idle = State()
    studying = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bls_user_id: str) -> None:
    bls = get_bls_client()
    languages = await bls.get_languages()

    if not languages:
        await message.answer("Нет доступных языков.")
        return

    await state.set_state(UserState.idle)
    await state.update_data(bls_user_id=bls_user_id)
    await message.answer(
        "👋 Добро пожаловать!\n\nВыберите язык для изучения:",
        reply_markup=build_language_keyboard(languages),
    )


@router.message(Command("web"))
async def cmd_web(message: Message) -> None:
    web_url = os.environ.get("WEB_URL", "http://136.244.102.39:8800")
    url = f"{web_url}/autologin?telegram_id={message.from_user.id}"
    await message.answer(f"🌐 Веб-версия:\n{url}", disable_web_page_preview=True)


@router.message(Command("language"))
async def cmd_language(message: Message, state: FSMContext, bls_user_id: str) -> None:
    bls = get_bls_client()
    languages = await bls.get_languages()
    await state.update_data(bls_user_id=bls_user_id)
    await message.answer(
        "Выберите язык:",
        reply_markup=build_language_keyboard(languages),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def select_language(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    language_id = callback.data.split(":", 1)[1]
    bls = get_bls_client()

    resp = await bls.get_session(bls_user_id, language_id)
    if resp is None:
        resp = await bls.start_session(bls_user_id, language_id)

    if resp is None:
        await callback.answer("Нет слов для изучения.", show_alert=True)
        return

    card = resp.get("card")
    if card is None:
        await callback.answer("На сегодня всё изучено! 🎉", show_alert=True)
        return

    await state.set_state(UserState.studying)
    await state.update_data(bls_user_id=bls_user_id, language_id=language_id)

    await callback.message.edit_text(
        render_card_text(card),
        reply_markup=build_card_keyboard(card, language_id),
        parse_mode="HTML",
    )
    await callback.answer()
