"""
Hint management during study sessions.
Allows users to create/edit/delete personal hint texts for individual words.

Flow:
  card (show_answer) → 💡 Подсказки → hint menu → tap type → enter text → saved → back to card
  Callback pattern: hint:{language_id}:{word_id}:{action}[:{hint_type_index}]
"""

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery, Message,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.bls_client.client import get_bls_client

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from common.hint_catalog import hint_types_ordered, setting_key_for

router = Router()

ALL_HINT_TYPES = hint_types_ordered()

# В callback_data имя типа не помещается: hint:<lang 24>:<word 24>:edit: — уже
# 55 байт, а "phoneticassociation" добавляет ещё 20 при лимите Telegram в 64.
# Кнопка с таким callback_data не отправляется, и вместе с ней падает всё
# сообщение с меню подсказок. Поэтому в кнопке едет порядковый номер типа.
_HINT_CODES = list(ALL_HINT_TYPES)


def _hint_code(hint_type: str) -> str:
    return str(_HINT_CODES.index(hint_type))


def _hint_type_by_code(code: str) -> str:
    """Обратное преобразование; неизвестный код даёт пустую строку."""
    if code.isdigit() and int(code) < len(_HINT_CODES):
        return _HINT_CODES[int(code)]
    return ""


async def _get_enabled_hint_types(bls, bls_user_id: str, language_id: str) -> dict:
    """Return only hint types that are enabled in user settings (ordered dict subset)."""
    try:
        settings = await bls.get_hint_settings(bls_user_id, language_id)
    except Exception:
        settings = {}
    setting_key = {ht: setting_key_for(ht) for ht in ALL_HINT_TYPES}
    return {ht: label for ht, label in ALL_HINT_TYPES.items()
            if settings.get(setting_key[ht], False)}


class HintState(StatesGroup):
    input_text = State()   # data: {word_id, language_id, hint_type, session_id}


# ── keyboard helpers ───────────────────────────────────────────────────────────

def _hint_menu_kb(lang_id: str, word_id: str, hints: dict,
                  enabled_types: dict) -> InlineKeyboardMarkup:
    """Build inline keyboard for enabled hint types only."""
    rows = []
    for ht, (icon, label) in enabled_types.items():
        val = hints.get(ht, "").strip()
        status = "✏️" if val else "➕"
        btn_text = f"{icon} {label}: {status}"
        rows.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"hint:{lang_id}:{word_id}:edit:{_hint_code(ht)}",
        )])
        if val:
            rows[-1].append(InlineKeyboardButton(
                text="🗑",
                callback_data=f"hint:{lang_id}:{word_id}:del:{_hint_code(ht)}",
            ))
    rows.append([InlineKeyboardButton(text="← Назад", callback_data=f"hint:{lang_id}:{word_id}:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _hint_menu_text(word_id: str, hints: dict, enabled_types: dict) -> str:
    lines = ["💡 <b>Подсказки к слову</b>\n"]
    for ht, (icon, label) in enabled_types.items():
        val = hints.get(ht, "").strip()
        lines.append(f"{icon} <b>{label}:</b> {val or '<i>не задано</i>'}")
    return "\n".join(lines)


# ── handlers ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("hint:") & F.data.func(lambda d: d.count(":") >= 3))
async def hint_menu(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    """Show hint menu for a word (or process sub-actions)."""
    parts = callback.data.split(":")
    # hint:{lang_id}:{word_id}:{action}[:{hint_type}]
    lang_id   = parts[1]
    word_id   = parts[2]
    action    = parts[3]
    hint_type = _hint_type_by_code(parts[4]) if len(parts) > 4 else None

    bls = get_bls_client()

    if action == "back":
        await state.clear()
        await callback.answer()
        # Delete hint menu message — user goes back to studying
        await callback.message.delete()
        return

    if action == "del" and hint_type:
        await bls.delete_word_hint(bls_user_id, word_id, hint_type)
        action = "show"  # refresh menu

    if action in ("show", "del"):
        hints = await bls.get_word_hints(bls_user_id, word_id)
        enabled = await _get_enabled_hint_types(bls, bls_user_id, lang_id)
        if not enabled:
            await callback.answer("Все типы подсказок отключены в настройках.", show_alert=True)
            return
        await callback.message.edit_text(
            _hint_menu_text(word_id, hints, enabled),
            parse_mode="HTML",
            reply_markup=_hint_menu_kb(lang_id, word_id, hints, enabled),
        )
        await callback.answer()
        return

    if action == "edit" and hint_type:
        icon, label = ALL_HINT_TYPES.get(hint_type, ("💡", hint_type))
        await state.set_state(HintState.input_text)
        await state.update_data(word_id=word_id, language_id=lang_id, hint_type=hint_type)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Отмена", callback_data=f"hint:{lang_id}:{word_id}:show"),
        ]])
        await callback.message.edit_text(
            f"{icon} <b>{label}</b>\n\nВведите текст подсказки:",
            parse_mode="HTML",
            reply_markup=kb,
        )
        await callback.answer()
        return

    await callback.answer()


@router.message(HintState.input_text)
async def hint_save(message: Message, state: FSMContext, bls_user_id: str) -> None:
    """Save hint text entered by user."""
    data = await state.get_data()
    word_id   = data["word_id"]
    lang_id   = data["language_id"]
    hint_type = data["hint_type"]
    text      = (message.text or "").strip()

    if not text:
        await message.answer("Подсказка не может быть пустой. Введите текст или нажмите Отмена.")
        return

    await state.clear()
    bls = get_bls_client()
    ok = await bls.set_word_hint(bls_user_id, word_id, hint_type, text, language_id=lang_id)

    if ok:
        hints = await bls.get_word_hints(bls_user_id, word_id)
        enabled = await _get_enabled_hint_types(bls, bls_user_id, lang_id)
        await message.answer(
            f"✅ Подсказка сохранена!\n\n" + _hint_menu_text(word_id, hints, enabled),
            parse_mode="HTML",
            reply_markup=_hint_menu_kb(lang_id, word_id, hints, enabled),
        )
    else:
        await message.answer("❌ Не удалось сохранить подсказку. Попробуйте ещё раз.")
