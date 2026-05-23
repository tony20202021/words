from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.bls_client.client import get_bls_client
from app.bot.handlers.start import UserState
from app.bot.keyboards import build_card_keyboard
from app.bot.renderer import render_card_text

router = Router()

COMPLETED_TEXT = (
    "🎉 <b>Сессия завершена!</b>\n\n"
    "Все слова на сегодня изучены. Отличная работа!\n"
    "Используйте /study чтобы начать снова."
)


@router.message(Command("study"))
async def cmd_study(message: Message, state: FSMContext, bls_user_id: str) -> None:
    data = await state.get_data()
    language_id = data.get("language_id")

    if not language_id:
        await message.answer("Сначала выберите язык — /language")
        return

    bls = get_bls_client()
    resp = await bls.get_session(bls_user_id, language_id)
    if resp is None:
        resp = await bls.start_session(bls_user_id, language_id)

    if resp is None or resp.get("card") is None:
        await message.answer("На сегодня всё изучено! 🎉")
        return

    card = resp["card"]
    await state.set_state(UserState.studying)
    await message.answer(
        render_card_text(card),
        reply_markup=build_card_keyboard(card, language_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("study:"))
async def handle_study_callback(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    parts = callback.data.split(":")
    # format: study:{language_id}:{action}[:{param}]
    language_id = parts[1]
    action = parts[2]

    bls = get_bls_client()
    session_resp = await bls.get_session(bls_user_id, language_id)
    if not session_resp:
        await callback.answer("Сессия не найдена. Начните заново: /study", show_alert=True)
        return

    session_id = session_resp["session_id"]

    if action == "know":
        resp = await bls.know_word(session_id)
    elif action == "show_answer":
        resp = await bls.show_answer(session_id)
    elif action == "rate":
        rating = parts[3] if len(parts) > 3 else "dont_know"
        resp = await bls.rate_word(session_id, rating)
        if resp.get("batch_exhausted"):
            batch = await bls.next_batch(resp["session_id"])
            if batch.get("loaded"):
                resp = batch
            else:
                await callback.message.edit_text(COMPLETED_TEXT, parse_mode="HTML")
                await callback.answer()
                return
    elif action == "toggle_skip":
        resp = await bls.toggle_skip(session_id)
    elif action == "reconsider":
        resp = await bls.reconsider(session_id)
    else:
        await callback.answer()
        return

    card = resp.get("card")
    if card is None:
        await callback.message.edit_text(COMPLETED_TEXT, parse_mode="HTML")
        await callback.answer()
        return

    await state.update_data(language_id=language_id)
    await callback.message.edit_text(
        render_card_text(card),
        reply_markup=build_card_keyboard(card, language_id),
        parse_mode="HTML",
    )
    await callback.answer()
