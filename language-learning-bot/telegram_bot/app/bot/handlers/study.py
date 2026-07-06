from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from app.bls_client.client import get_bls_client
from app.bot.handlers.start import UserState
from app.bot.keyboards import build_card_keyboard
from app.bot.renderer import render_card_text, render_extra_texts
from app.bot.big_word import generate_big_word_image

router = Router()

COMPLETED_TEXT = (
    "🎉 <b>Сессия завершена!</b>\n\n"
    "Все слова на сегодня изучены. Отличная работа!\n"
    "Используйте /study чтобы начать снова."
)

SESSION_STALE_TEXT = (
    "⏰ <b>Сессия устарела</b> — вы давно не занимались.\n"
    "Можно продолжить или /restart чтобы начать заново."
)


async def _display_card(target: Message, card: dict, language_id: str, bls, edit_mode: bool = False) -> None:
    """
    Display a card like the old bot:
      - sounds as voice messages (first)
      - extra content (radicals/refs/tones) as separate messages
      - restart_notice as a separate warning message (when set)
      - main card text + keyboard last
    edit_mode=True: edits the existing message when there are no sounds/extras.
    edit_mode=False: always sends new messages.
    """
    sounds = card.get("sounds") or []
    extras = render_extra_texts(card)
    main_text = render_card_text(card)
    keyboard = build_card_keyboard(card, language_id)
    big_word = card.get("big_word")
    restart_notice = card.get("restart_notice")

    has_extras = bool(sounds or extras or big_word)

    if edit_mode and not has_extras:
        # Simple same-word update (toggle skip, show answer with no extras) — edit in place
        await target.edit_text(main_text, reply_markup=keyboard, parse_mode="HTML")
        return

    # Send new messages: sounds → extras → big word image → restart notice → main card+keyboard (last)
    for url in sounds:
        sound_data = await bls.get_sound(url)
        if sound_data:
            await target.answer_voice(BufferedInputFile(sound_data, filename="sound.ogg"))

    for extra_text in extras:
        await target.answer(extra_text, parse_mode="HTML")

    if big_word:
        try:
            img_bytes = await generate_big_word_image(
                big_word["word"], big_word.get("transcription") or None
            )
            await target.answer_photo(BufferedInputFile(img_bytes, filename="word.png"))
        except Exception:
            pass  # image generation failure must not block the card

    if restart_notice and not edit_mode:
        await target.answer(restart_notice)

    await target.answer(main_text, reply_markup=keyboard, parse_mode="HTML")


@router.message(Command("study"))
async def cmd_study(message: Message, state: FSMContext, bls_user_id: str) -> None:
    """Continue current session (or start a new one if none exists)."""
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
    if resp.get("session_stale"):
        await message.answer(SESSION_STALE_TEXT, parse_mode="HTML")
    await _display_card(message, card, language_id, bls, edit_mode=False)


@router.message(Command("restart"))
async def cmd_restart(message: Message, state: FSMContext, bls_user_id: str) -> None:
    """Reset session and start from the beginning."""
    data = await state.get_data()
    language_id = data.get("language_id")

    if not language_id:
        await message.answer("Сначала выберите язык — /language")
        return

    bls = get_bls_client()
    await bls.end_session(bls_user_id, language_id)
    resp = await bls.start_session(bls_user_id, language_id)

    if resp is None or resp.get("card") is None:
        await message.answer("На сегодня всё изучено! 🎉")
        return

    card = resp["card"]
    await state.set_state(UserState.studying)
    await _display_card(message, card, language_id, bls, edit_mode=False)


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

    if action == "sound":
        idx = int(parts[3]) if len(parts) > 3 else 0
        sounds = (session_resp.get("card") or {}).get("sounds") or []
        if idx >= len(sounds):
            await callback.answer("Звук недоступен", show_alert=True)
            return
        sound_data = await bls.get_sound(sounds[idx])
        if not sound_data:
            await callback.answer("Звук недоступен", show_alert=True)
            return
        await callback.message.answer_audio(BufferedInputFile(sound_data, filename="sound.mp3"))
        await callback.answer()
        return
    elif action == "pick_sound":
        idx = int(parts[3]) if len(parts) > 3 else 0
        card = session_resp.get("card") or {}
        pick_options = card.get("pick_options") or {}
        options = pick_options.get("options", [])
        if idx >= len(options):
            await callback.answer("Звук недоступен", show_alert=True)
            return
        sound_url = options[idx].get("target_text", "")
        sound_data = await bls.get_sound(sound_url) if sound_url else None
        if not sound_data:
            await callback.answer("Звук недоступен", show_alert=True)
            return
        await callback.message.answer_audio(BufferedInputFile(sound_data, filename="sound.mp3"))
        await callback.answer()
        return
    elif action == "pick_answer":
        selected_word_id = parts[3] if len(parts) > 3 else "dont_know"
        resp = await bls.pick_answer(session_id, selected_word_id)
        if resp.get("batch_exhausted"):
            batch = await bls.next_batch(session_id)
            if batch.get("loaded"):
                resp = batch
            else:
                await callback.answer()
                await callback.message.answer(COMPLETED_TEXT, parse_mode="HTML")
                return
    elif action == "add_forbidden_pair":
        bad_word_id = parts[3] if len(parts) > 3 else ""
        resp = await bls.add_forbidden_pair(session_id, bad_word_id)
    elif action == "know":
        resp = await bls.know_word(session_id)
    elif action == "show_answer":
        resp = await bls.show_answer(session_id)
    elif action == "rate":
        rating = parts[3] if len(parts) > 3 else "dont_know"
        resp = await bls.rate_word(session_id, rating)
        if resp.get("batch_exhausted"):
            batch = await bls.next_batch(session_id)
            if batch.get("loaded"):
                resp = batch
            else:
                await callback.answer()
                await callback.message.answer(COMPLETED_TEXT, parse_mode="HTML")
                return
    elif action == "toggle_skip":
        resp = await bls.toggle_skip(session_id)
    elif action == "reconsider":
        resp = await bls.reconsider(session_id)
        if resp.get("batch_exhausted"):
            batch = await bls.next_batch(session_id)
            if batch.get("loaded"):
                resp = batch
            else:
                await callback.answer()
                await callback.message.answer(COMPLETED_TEXT, parse_mode="HTML")
                return
    else:
        await callback.answer()
        return

    card = resp.get("card")
    if card is None:
        await callback.answer()
        await callback.message.answer(COMPLETED_TEXT, parse_mode="HTML")
        return

    await state.update_data(language_id=language_id)

    await callback.answer()

    # Actions that advance to next word → always new message (like old bot)
    # Actions on the same word (show_answer, toggle_skip, pick_answer wrong) → try to edit
    next_word_actions = {"rate", "know", "reconsider"}
    # pick_answer advances word only when correct (show_answer=False in next card); for wrong answer it shows the answer
    if action == "pick_answer":
        next_card_shows_answer = (resp.get("card") or {}).get("show_answer", False)
        edit_mode = next_card_shows_answer  # wrong → edit in place; correct → new message
        pick_result = (resp.get("card") or {}).get("pick_answer_result")
        if pick_result == "correct":
            await callback.message.answer("✓ Правильно!")
        elif pick_result == "wrong":
            await callback.message.answer("✗ Неверно")
    else:
        edit_mode = action not in next_word_actions

    await _display_card(callback.message, card, language_id, bls, edit_mode=edit_mode)
