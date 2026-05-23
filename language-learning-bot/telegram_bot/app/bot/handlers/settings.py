from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from app.bls_client.client import get_bls_client

router = Router()

# Settings displayed in the bot (key → Russian label)
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
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
    languages = await bls.get_languages()
    lang_name = next((l.get("name_ru", l.get("name_foreign", language_id))
                      for l in languages if l.get("id") == language_id), language_id)

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

    languages = await bls.get_languages()
    lang_name = next((l.get("name_ru", l.get("name_foreign", language_id))
                      for l in languages if l.get("id") == language_id), language_id)

    keyboard = _build_settings_keyboard(updated, language_id)
    await callback.message.edit_text(
        _format_settings_text(lang_name),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()
