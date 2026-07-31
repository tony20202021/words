from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.bls_client.client import get_bls_client

router = Router()


class SettingsState(StatesGroup):
    waiting_number = State()   # data: {num_language_id, num_key}

SETTING_LABELS = {
    "skip_marked":                   None,  # state-dependent label, see _build_settings_keyboard
    "show_skip_button":              "Показывать кнопку Пропускать",
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
    "random_transcription":          "Дополнительно использовать транскрипцию",
    "random_sound":                  "Дополнительно использовать звук",
    "random_pick_mode":              "Режим выбора (pick mode)",
    "show_charts":                   "Показывать графики",
    "show_short_captions":           "Короткие подписи",
    "receive_messages":              "Получать сообщения",
    "show_debug":                    "Отладочная информация",
}

# (label, min_value)
NUMERIC_LABELS = {
    "start_word":                 ("Начальное слово",              1),
    "reset_same_day_hours":       ("Сброс: перерыв за день (ч)",   0),
    "reset_cross_midnight_hours": ("Сброс: час после полуночи",    0),
    "unknown_limit_new_words":    ("Лимит неизвестных слов",       0),
    "max_check_interval":         ("Макс. интервал повторения",    1),
    "quiz_options_count":         ("Вариантов в режиме выбора",    2),
}


def _build_settings_keyboard(settings: dict, language_id: str) -> InlineKeyboardMarkup:
    buttons = []
    for key, label in SETTING_LABELS.items():
        val = settings.get(key, False)
        if key == "skip_marked":
            btn_text = "✅ Пропускать исключённые слова" if val else "❌ Не пропускать исключённые слова"
        else:
            icon = "✅" if val else "❌"
            btn_text = f"{icon} {label}"
        buttons.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"settings:{language_id}:{key}",
        )])
    for key, (label, _min) in NUMERIC_LABELS.items():
        val = settings.get(key, 0)
        buttons.append([InlineKeyboardButton(text=f"· {label} ·", callback_data="noop")])
        buttons.append([
            InlineKeyboardButton(text="−", callback_data=f"set_num:{language_id}:{key}:-1"),
            InlineKeyboardButton(text=f"✏️ {val}", callback_data=f"num_input:{language_id}:{key}"),
            InlineKeyboardButton(text="+", callback_data=f"set_num:{language_id}:{key}:1"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def _lang_name(bls, language_id: str) -> str:
    """Resolve human-readable name for language_id via BLS. Fallback to id."""
    try:
        languages = await bls.get_languages()
        lang = next((l for l in languages if l.get("id") == language_id), None)
        return lang["name_ru"] if lang else language_id
    except Exception:
        return language_id


def _format_settings_text(language_name: str) -> str:
    return f"⚙️ <b>Настройки: {language_name}</b>\n\nНажмите на кнопку, чтобы переключить:"


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext, bls_user_id: str) -> None:
    data = await state.get_data()
    language_id = data.get("language_id")

    if not language_id:
        await message.answer("Сначала выберите язык — /language")
        return

    bls = get_bls_client()
    lang_name = data.get("language_name") or await _lang_name(bls, language_id)
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


@router.callback_query(F.data.startswith("num_input:"))
async def prompt_numeric_input(callback: CallbackQuery, state: FSMContext) -> None:
    _, language_id, key = callback.data.split(":", 2)
    label, min_val = NUMERIC_LABELS.get(key, (key, 0))
    await state.update_data(num_language_id=language_id, num_key=key)
    await state.set_state(SettingsState.waiting_number)
    await callback.message.answer(
        f"Введите число для «{label}» (минимум {min_val}).\nОтмена — /cancel"
    )
    await callback.answer()


@router.message(SettingsState.waiting_number, Command("cancel"))
async def cancel_numeric_input(message: Message, state: FSMContext) -> None:
    await state.set_state(None)
    await message.answer("Отменено.")


@router.message(SettingsState.waiting_number)
async def process_numeric_input(message: Message, state: FSMContext, bls_user_id: str) -> None:
    data = await state.get_data()
    language_id = data.get("num_language_id")
    key = data.get("num_key")
    if not language_id or not key:
        await state.set_state(None)
        await message.answer("Что-то пошло не так, откройте /settings заново.")
        return
    label, min_val = NUMERIC_LABELS.get(key, (key, 0))
    text = (message.text or "").strip()
    try:
        value = int(text)
    except ValueError:
        await message.answer(f"Нужно целое число (минимум {min_val}). Попробуйте ещё раз или /cancel.")
        return
    if value < min_val:
        value = min_val

    bls = get_bls_client()
    await bls.set_setting(bls_user_id, language_id, key, value)
    await state.set_state(None)

    updated = await bls.get_settings(bls_user_id, language_id)
    lang_name = await _lang_name(bls, language_id)
    keyboard = _build_settings_keyboard(updated, language_id)
    await message.answer(
        f"✅ «{label}» → <b>{value}</b>\n\n" + _format_settings_text(lang_name),
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery) -> None:
    await callback.answer()
