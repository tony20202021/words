from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from app.bls_client.client import get_bls_client

router = Router()

SETTING_LABELS = {
    "skip_marked":                   "Исключённые слова",
    "use_check_date":                "Учитывать дату",
    "show_check_date":               "Показывать дату проверки",
    "show_hint_meaning":             "Ассоциация на русском",
    "show_hint_phoneticsound":       "Звучание по слогам",
    "show_hint_phoneticassociation": "Ассоциация звучания",
    "show_hint_writing":             "Ассоциация написания",
    "show_big":                      "Показывать крупное написание",
    "show_writing_images":           "Показывать картинки",
    "show_radicals":                 "Показывать радикалы",
    "show_references":               "Показывать ссылки",
    "show_tones":                    "Показывать тоны",
    "show_sounds":                   "Показывать звуки",
    "random_foreign":                "Рандомно начинать с иностранных слов",
    "random_transcription":          "Рандомно начинать с транскрипций",
    "random_sound":                  "Рандомно начинать со звуков",
    "show_charts":                   "Показывать графики",
    "show_short_captions":           "Короткие подписи",
    "receive_messages":              "Получать сообщения",
    "show_debug":                    "Отладочная информация",
}

# (label, min_value)
NUMERIC_LABELS = {
    "start_word":              ("Начальное слово",        1),
    "reset_session_days":      ("Сброс сессии (дни)",     0),
    "reset_session_hours":     ("Сброс сессии (часы)",    0),
    "unknown_limit_new_words": ("Лимит неизвестных слов", 0),
}


def _build_settings_keyboard(settings: dict, language_id: str) -> InlineKeyboardMarkup:
    buttons = []
    for key, label in SETTING_LABELS.items():
        val = settings.get(key, False)
        icon = "✅" if val else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {label}",
            callback_data=f"settings:{language_id}:{key}",
        )])
    for key, (label, _min) in NUMERIC_LABELS.items():
        val = settings.get(key, 0)
        buttons.append([
            InlineKeyboardButton(text="−", callback_data=f"set_num:{language_id}:{key}:-1"),
            InlineKeyboardButton(text=f"{label}: {val}", callback_data="noop"),
            InlineKeyboardButton(text="+", callback_data=f"set_num:{language_id}:{key}:1"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _format_settings_text(language_name: str) -> str:
    return f"⚙️ <b>Настройки: {language_name}</b>\n\nНажмите на кнопку, чтобы переключить:"


async def _lang_name(bls, language_id: str) -> str:
    languages = await bls.get_languages()
    return next(
        (l.get("name_ru", l.get("name_foreign", language_id))
         for l in languages if l.get("id") == language_id),
        language_id,
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext, bls_user_id: str) -> None:
    data = await state.get_data()
    language_id = data.get("language_id")

    if not language_id:
        await message.answer("Сначала выберите язык — /language")
        return

    bls = get_bls_client()
    lang_name = await _lang_name(bls, language_id)
    settings = await bls.get_settings(bls_user_id, language_id)
    keyboard = _build_settings_keyboard(settings, language_id)

    await message.answer(
        _format_settings_text(lang_name),
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("settings:"))
async def toggle_setting(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    _, language_id, key = callback.data.split(":", 2)

    bls = get_bls_client()
    updated = await bls.toggle_setting(bls_user_id, language_id, key)
    lang_name = await _lang_name(bls, language_id)

    keyboard = _build_settings_keyboard(updated, language_id)
    await callback.message.edit_text(
        _format_settings_text(lang_name),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_num:"))
async def change_numeric_setting(callback: CallbackQuery, bls_user_id: str) -> None:
    parts = callback.data.split(":", 3)
    if len(parts) < 4:
        await callback.answer()
        return
    _, language_id, key, delta_str = parts
    delta = int(delta_str)

    bls = get_bls_client()
    current = await bls.get_settings(bls_user_id, language_id)
    _label, min_val = NUMERIC_LABELS.get(key, ("", 0))
    new_val = max(min_val, current.get(key, 0) + delta)
    await bls.set_setting(bls_user_id, language_id, key, new_val)
    updated = await bls.get_settings(bls_user_id, language_id)
    lang_name = await _lang_name(bls, language_id)

    keyboard = _build_settings_keyboard(updated, language_id)
    await callback.message.edit_text(
        _format_settings_text(lang_name),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery) -> None:
    await callback.answer()
