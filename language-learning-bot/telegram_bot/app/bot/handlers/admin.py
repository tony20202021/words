"""
Admin panel for the new Telegram bot.
Features: stats, users (+admin toggle), languages (create/edit/delete),
words (search/edit/delete), export (with range), import (xlsx/csv/json),
broadcast, diagnostics.
All handlers require is_admin=True.
"""

import os
import platform
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BufferedInputFile, Document,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.bls_client.client import get_bls_client

router = Router()

EDITABLE_WORD_FIELDS = [
    ("foreign",        "Слово (иностранное)"),
    ("translation",    "Перевод"),
    ("transcription",  "Транскрипция"),
    ("radicals",       "Радикалы"),
    ("references",     "Ссылки"),
    ("tones",          "Тоны"),
    ("number",         "Номер слова"),
]

EXPORT_FORMATS = ["xlsx", "csv", "json"]


class AdminState(StatesGroup):
    broadcast_input    = State()
    lang_create_ru     = State()
    lang_create_foreign= State()
    lang_edit_field    = State()   # data: {lang_id, field, name_ru, name_foreign}
    word_search        = State()   # data: {lang_id}
    word_edit_field    = State()   # data: {word_id, lang_id, field}
    export_range_input = State()   # data: {lang_id, fmt}
    import_waiting     = State()   # data: {lang_id, clear_existing}


# ── helpers ────────────────────────────────────────────────────────────────────

async def _check_admin(bls_user_id: str) -> bool:
    return await get_bls_client().is_admin(bls_user_id)


def _btn(text: str, cb: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=cb)


def _kb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=list(rows))


def _menu_kb() -> InlineKeyboardMarkup:
    return _kb(
        [_btn("📊 Статистика",    "admin:stats")],
        [_btn("👥 Пользователи",  "admin:users:1")],
        [_btn("🌐 Языки",         "admin:langs")],
        [_btn("📢 Рассылка",      "admin:broadcast")],
        [_btn("🔧 Диагностика",   "admin:diag")],
    )


def _back_menu() -> list:
    return [_btn("← Меню", "admin:menu")]


async def _guard(obj, bls_user_id: str, is_callback: bool = False) -> bool:
    """Returns True if NOT admin (caller should return early)."""
    if await _check_admin(bls_user_id):
        return False
    if is_callback:
        await obj.answer("Нет доступа", show_alert=True)
    else:
        await obj.answer("❌ У вас нет прав администратора.")
    return True


# ── /admin ────────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, bls_user_id: str) -> None:
    if await _guard(message, bls_user_id):
        return
    await message.answer("⚙️ <b>Панель администратора</b>",
                         parse_mode="HTML", reply_markup=_menu_kb())


@router.callback_query(F.data == "admin:menu")
async def admin_menu_back(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    await state.clear()
    await callback.message.edit_text("⚙️ <b>Панель администратора</b>",
                                     parse_mode="HTML", reply_markup=_menu_kb())
    await callback.answer()


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    bls = get_bls_client()
    stats = await bls.admin_global_stats(bls_user_id)
    lines = ["📊 <b>Статистика бота</b>",
             f"Пользователей: <b>{stats.get('total_users', '?')}</b>",
             f"Языков: <b>{len(stats.get('languages', []))}</b>", ""]
    for lang in stats.get("languages", []):
        lines.append(f"• {lang['name_ru']}: {lang['word_count']} слов, "
                     f"{lang['active_users']} активных")
    kb = _kb(_back_menu())
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=kb)
    await callback.answer()


# ── Users ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:users:"))
async def admin_users(callback: CallbackQuery, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    page = int(callback.data.split(":")[-1])
    bls = get_bls_client()
    data = await bls.admin_list_users(bls_user_id, page)
    users = data.get("users", [])
    total_pages = data.get("total_pages", 1)

    lines = [f"👥 <b>Пользователи</b> (стр. {page}/{total_pages})", ""]
    for u in users:
        admin_mark = " 👑" if u.get("is_admin") else ""
        name = f"{u.get('first_name', '')} {u.get('last_name') or ''}".strip()
        uname = f" @{u['username']}" if u.get("username") else ""
        lines.append(f"• {name}{uname}{admin_mark}")
        lines.append(f"  <code>{u.get('id', '?')}</code>  tg:{u.get('telegram_id', '?')}")

    nav = []
    if page > 1:
        nav.append(_btn("←", f"admin:users:{page-1}"))
    if page < total_pages:
        nav.append(_btn("→", f"admin:users:{page+1}"))
    rows = []
    if nav:
        rows.append(nav)
    # User detail buttons (first 5 on the page)
    for u in users[:5]:
        uid = u.get("id", "")
        name = f"{u.get('first_name', '')}".strip() or uid[:8]
        rows.append([_btn(f"👤 {name}", f"admin:user:{uid}")])
    rows.append(_back_menu())
    await callback.message.edit_text("\n".join(lines) or "Нет пользователей",
                                     parse_mode="HTML",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:user:"))
async def admin_user_detail(callback: CallbackQuery, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    target_id = callback.data.split(":", 2)[2]
    bls = get_bls_client()
    user = await bls.admin_get_user_details(bls_user_id, target_id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    name = f"{user.get('first_name', '')} {user.get('last_name') or ''}".strip()
    uname = f"@{user['username']}" if user.get("username") else "—"
    is_adm = user.get("is_admin", False)
    lines = [
        f"👤 <b>{name}</b>",
        f"Username: {uname}",
        f"Telegram ID: <code>{user.get('telegram_id', '?')}</code>",
        f"DB ID: <code>{user.get('id', '?')}</code>",
        f"Админ: {'✅ да' if is_adm else '❌ нет'}",
    ]
    toggle_text = "🔴 Снять права admin" if is_adm else "🟢 Дать права admin"
    toggle_val = "0" if is_adm else "1"
    kb = _kb(
        [_btn(toggle_text, f"admin:user_admin:{target_id}:{toggle_val}")],
        [_btn("← Пользователи", "admin:users:1")],
        _back_menu(),
    )
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:user_admin:"))
async def admin_toggle_admin(callback: CallbackQuery, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    parts = callback.data.split(":")
    target_id = parts[2]
    make_admin = parts[3] == "1"
    bls = get_bls_client()
    result = await bls.admin_toggle_admin(bls_user_id, target_id, make_admin)
    status = "назначен администратором" if make_admin else "лишён прав администратора"
    await callback.answer(f"✅ Пользователь {status}", show_alert=True)
    # Refresh user detail
    callback.data = f"admin:user:{target_id}"
    await admin_user_detail(callback, bls_user_id)


# ── Languages ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:langs")
async def admin_langs(callback: CallbackQuery, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    bls = get_bls_client()
    stats = await bls.admin_global_stats(bls_user_id)
    langs = stats.get("languages", [])
    lines = ["🌐 <b>Языки</b>", ""]
    rows = []
    for lang in langs:
        lid = lang.get("id", "")
        lines.append(f"• {lang['name_ru']} ({lang.get('name_foreign', '')}) "
                     f"— {lang['word_count']} слов")
        rows.append([_btn(f"⚙️ {lang['name_ru']}", f"admin:lang:{lid}")])
    rows.append([_btn("➕ Создать язык", "admin:lang_create")])
    rows.append(_back_menu())
    await callback.message.edit_text("\n".join(lines) or "Нет языков",
                                     parse_mode="HTML",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:lang:"))
async def admin_lang_detail(callback: CallbackQuery, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    lang_id = callback.data.split(":", 2)[2]
    bls = get_bls_client()
    # Use global stats to find language info (simpler than separate endpoint)
    stats = await bls.admin_global_stats(bls_user_id)
    lang = next((l for l in stats.get("languages", []) if l.get("id") == lang_id), None)
    if not lang:
        await callback.answer("Язык не найден", show_alert=True)
        return
    lines = [
        f"🌐 <b>{lang['name_ru']}</b> ({lang.get('name_foreign', '')})",
        f"Слов: {lang['word_count']}",
        f"Активных пользователей: {lang.get('active_users', '?')}",
        f"ID: <code>{lang_id}</code>",
    ]
    kb = _kb(
        [_btn("✏️ Переименовать", f"admin:lang_edit:{lang_id}")],
        [_btn("🔍 Найти слово по номеру", f"admin:word_search:{lang_id}")],
        [_btn("📤 Экспорт слов", f"admin:export:{lang_id}"),
         _btn("📥 Импорт слов", f"admin:import:{lang_id}")],
        [_btn("🗑 Удалить язык", f"admin:lang_del:{lang_id}")],
        [_btn("← Языки", "admin:langs")],
        _back_menu(),
    )
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=kb)
    await callback.answer()


# Language create

@router.callback_query(F.data == "admin:lang_create")
async def admin_lang_create_start(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    await state.set_state(AdminState.lang_create_ru)
    kb = _kb([_btn("Отмена", "admin:langs")])
    await callback.message.edit_text(
        "🌐 <b>Создание языка</b>\n\nВведите русское название языка (напр. <i>Китайский</i>):",
        parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.message(AdminState.lang_create_ru)
async def admin_lang_create_ru(message: Message, state: FSMContext, bls_user_id: str) -> None:
    if await _guard(message, bls_user_id):
        await state.clear()
        return
    await state.update_data(name_ru=message.text.strip())
    await state.set_state(AdminState.lang_create_foreign)
    await message.answer(
        f"Русское название: <b>{message.text.strip()}</b>\n\n"
        "Теперь введите название на иностранном языке (напр. <i>中文</i>):",
        parse_mode="HTML")


@router.message(AdminState.lang_create_foreign)
async def admin_lang_create_foreign(message: Message, state: FSMContext, bls_user_id: str) -> None:
    if await _guard(message, bls_user_id):
        await state.clear()
        return
    data = await state.get_data()
    name_ru = data.get("name_ru", "")
    name_foreign = message.text.strip()
    await state.clear()
    bls = get_bls_client()
    result = await bls.admin_create_language(bls_user_id, name_ru, name_foreign)
    if result.get("id") or result.get("_id"):
        await message.answer(
            f"✅ Язык <b>{name_ru} ({name_foreign})</b> создан.",
            parse_mode="HTML", reply_markup=_kb([_btn("← Языки", "admin:langs")], _back_menu()))
    else:
        await message.answer("❌ Не удалось создать язык.",
                             reply_markup=_kb([_btn("← Языки", "admin:langs")], _back_menu()))


# Language edit (rename)

@router.callback_query(F.data.startswith("admin:lang_edit:"))
async def admin_lang_edit_menu(callback: CallbackQuery, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    lang_id = callback.data.split(":", 2)[2]
    bls = get_bls_client()
    stats = await bls.admin_global_stats(bls_user_id)
    lang = next((l for l in stats.get("languages", []) if l.get("id") == lang_id), {})
    kb = _kb(
        [_btn("✏️ Русское название",      f"admin:lang_field:{lang_id}:ru")],
        [_btn("✏️ Иностранное название",   f"admin:lang_field:{lang_id}:foreign")],
        [_btn("← Назад", f"admin:lang:{lang_id}")],
    )
    await callback.message.edit_text(
        f"✏️ <b>Редактирование: {lang.get('name_ru', lang_id)}</b>\n\nЧто изменить?",
        parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:lang_field:"))
async def admin_lang_field_start(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    parts = callback.data.split(":")
    lang_id, field = parts[2], parts[3]
    bls = get_bls_client()
    stats = await bls.admin_global_stats(bls_user_id)
    lang = next((l for l in stats.get("languages", []) if l.get("id") == lang_id), {})
    await state.update_data(lang_id=lang_id, field=field,
                            name_ru=lang.get("name_ru", ""),
                            name_foreign=lang.get("name_foreign", ""))
    await state.set_state(AdminState.lang_edit_field)
    label = "русское название" if field == "ru" else "иностранное название"
    current = lang.get("name_ru" if field == "ru" else "name_foreign", "")
    kb = _kb([_btn("Отмена", f"admin:lang:{lang_id}")])
    await callback.message.edit_text(
        f"Текущее {label}: <b>{current}</b>\n\nВведите новое значение:",
        parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.message(AdminState.lang_edit_field)
async def admin_lang_field_save(message: Message, state: FSMContext, bls_user_id: str) -> None:
    if await _guard(message, bls_user_id):
        await state.clear()
        return
    data = await state.get_data()
    lang_id = data["lang_id"]
    field = data["field"]
    new_value = message.text.strip()
    name_ru = new_value if field == "ru" else data["name_ru"]
    name_foreign = new_value if field == "foreign" else data["name_foreign"]
    await state.clear()
    bls = get_bls_client()
    ok = await bls.admin_update_language(bls_user_id, lang_id, name_ru, name_foreign)
    text = f"✅ Язык обновлён: <b>{name_ru} ({name_foreign})</b>" if ok else "❌ Не удалось обновить язык."
    await message.answer(text, parse_mode="HTML",
                         reply_markup=_kb([_btn("← Язык", f"admin:lang:{lang_id}")], _back_menu()))


# Language delete

@router.callback_query(F.data.startswith("admin:lang_del:"))
async def admin_lang_del_confirm(callback: CallbackQuery, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    lang_id = callback.data.split(":", 2)[2]
    # Don't use lang_del_ok: prefix longer than 64 chars risk — keep it simple
    kb = _kb(
        [_btn("✅ Да, удалить", f"admin:lang_del_ok:{lang_id}"),
         _btn("Отмена", f"admin:lang:{lang_id}")],
    )
    await callback.message.edit_text(
        "⚠️ <b>Удалить язык?</b>\n\nЭто действие необратимо. Все слова языка будут удалены.",
        parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:lang_del_ok:"))
async def admin_lang_del_execute(callback: CallbackQuery, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    lang_id = callback.data.split(":", 2)[2]
    bls = get_bls_client()
    result = await bls.admin_delete_language(bls_user_id, lang_id)
    ok = result.get("ok", False) if isinstance(result, dict) else bool(result)
    text = "✅ Язык удалён." if ok else "❌ Не удалось удалить язык."
    await callback.message.edit_text(text, reply_markup=_kb([_btn("← Языки", "admin:langs")], _back_menu()))
    await callback.answer()


# ── Words ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:word_search:"))
async def admin_word_search_start(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    lang_id = callback.data.split(":", 2)[2]
    await state.update_data(lang_id=lang_id)
    await state.set_state(AdminState.word_search)
    kb = _kb([_btn("Отмена", f"admin:lang:{lang_id}")])
    await callback.message.edit_text(
        "🔍 <b>Поиск слова по номеру</b>\n\nВведите номер слова:",
        parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.message(AdminState.word_search)
async def admin_word_search_exec(message: Message, state: FSMContext, bls_user_id: str) -> None:
    if await _guard(message, bls_user_id):
        await state.clear()
        return
    data = await state.get_data()
    lang_id = data["lang_id"]
    await state.clear()
    try:
        number = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите целое число.",
                             reply_markup=_kb([_btn("← Язык", f"admin:lang:{lang_id}")]))
        return
    bls = get_bls_client()
    word = await bls.admin_word_by_number(bls_user_id, lang_id, number)
    if not word:
        await message.answer("❌ Слово не найдено.",
                             reply_markup=_kb([_btn("← Язык", f"admin:lang:{lang_id}")]))
        return
    await _show_word(message, word, lang_id)


def _word_text(word: dict) -> str:
    lines = [
        f"📝 <b>Слово #{word.get('word_number', '?')}</b>",
        f"Иностранное: <b>{word.get('word_foreign', '—')}</b>",
        f"Перевод: {word.get('translation', '—')}",
    ]
    if word.get("transcription"):
        lines.append(f"Транскрипция: {word['transcription']}")
    if word.get("tones"):
        lines.append(f"Тоны: {word['tones']}")
    if word.get("radicals"):
        lines.append(f"Радикалы: {word['radicals'][:80]}…" if len(word.get("radicals","")) > 80 else f"Радикалы: {word['radicals']}")
    lines.append(f"\nID: <code>{word.get('id', word.get('_id', '?'))}</code>")
    return "\n".join(lines)


def _word_kb(word_id: str, lang_id: str) -> InlineKeyboardMarkup:
    rows = []
    for field, label in EDITABLE_WORD_FIELDS:
        rows.append([_btn(f"✏️ {label}", f"admin:word_edit:{word_id}:{lang_id}:{field}")])
    rows.append([_btn("🗑 Удалить", f"admin:word_del:{word_id}:{lang_id}")])
    rows.append([_btn("← Язык", f"admin:lang:{lang_id}")])
    rows.append(_back_menu())
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _show_word(obj, word: dict, lang_id: str) -> None:
    word_id = str(word.get("id") or word.get("_id", ""))
    text = _word_text(word)
    kb = _word_kb(word_id, lang_id)
    if isinstance(obj, Message):
        await obj.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await obj.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("admin:word_edit:"))
async def admin_word_edit_start(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    parts = callback.data.split(":")
    word_id, lang_id, field = parts[2], parts[3], parts[4]
    field_label = dict(EDITABLE_WORD_FIELDS).get(field, field)
    await state.update_data(word_id=word_id, lang_id=lang_id, field=field)
    await state.set_state(AdminState.word_edit_field)
    kb = _kb([_btn("Отмена", f"admin:lang:{lang_id}")])
    await callback.message.edit_text(
        f"✏️ <b>Редактировать: {field_label}</b>\n\nВведите новое значение:",
        parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.message(AdminState.word_edit_field)
async def admin_word_edit_save(message: Message, state: FSMContext, bls_user_id: str) -> None:
    if await _guard(message, bls_user_id):
        await state.clear()
        return
    data = await state.get_data()
    word_id = data["word_id"]
    lang_id = data["lang_id"]
    field = data["field"]
    await state.clear()
    bls = get_bls_client()
    ok = await bls.admin_update_word(bls_user_id, word_id, field, message.text.strip())
    if ok:
        await message.answer("✅ Поле обновлено.",
                             reply_markup=_kb([_btn("← Язык", f"admin:lang:{lang_id}")], _back_menu()))
    else:
        await message.answer("❌ Не удалось обновить поле.",
                             reply_markup=_kb([_btn("← Язык", f"admin:lang:{lang_id}")], _back_menu()))


@router.callback_query(F.data.startswith("admin:word_del:"))
async def admin_word_del_confirm(callback: CallbackQuery, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    parts = callback.data.split(":")
    word_id, lang_id = parts[2], parts[3]
    kb = _kb(
        [_btn("✅ Да, удалить", f"admin:word_del_ok:{word_id}:{lang_id}"),
         _btn("Отмена", f"admin:lang:{lang_id}")],
    )
    await callback.message.edit_text(
        "⚠️ <b>Удалить слово?</b>\n\nЭто действие необратимо.",
        parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:word_del_ok:"))
async def admin_word_del_execute(callback: CallbackQuery, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    parts = callback.data.split(":")
    word_id, lang_id = parts[2], parts[3]
    bls = get_bls_client()
    ok = await bls.admin_delete_word(bls_user_id, word_id)
    text = "✅ Слово удалено." if ok else "❌ Не удалось удалить слово."
    await callback.message.edit_text(text,
                                     reply_markup=_kb([_btn("← Язык", f"admin:lang:{lang_id}")], _back_menu()))
    await callback.answer()


# ── Export ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:export:"))
async def admin_export_menu(callback: CallbackQuery, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    lang_id = callback.data.split(":", 2)[2]
    rows = []
    for fmt in EXPORT_FORMATS:
        rows.append([
            _btn(f"📥 {fmt.upper()} (все)", f"admin:export_dl:{lang_id}:{fmt}:all"),
            _btn(f"📥 {fmt.upper()} (диапазон)", f"admin:export_range:{lang_id}:{fmt}"),
        ])
    rows.append([_btn("← Назад", f"admin:lang:{lang_id}")])
    await callback.message.edit_text(
        "📤 <b>Экспорт слов</b>\n\nВыберите формат и диапазон:",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:export_range:"))
async def admin_export_range_start(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    parts = callback.data.split(":")
    lang_id, fmt = parts[2], parts[3]
    await state.set_state(AdminState.export_range_input)
    await state.update_data(lang_id=lang_id, fmt=fmt)
    kb = _kb([_btn("Отмена", f"admin:export:{lang_id}")])
    await callback.message.edit_text(
        f"📤 <b>Экспорт {fmt.upper()} — диапазон</b>\n\n"
        "Введите диапазон номеров слов через дефис или пробел:\n"
        "<code>1-500</code>  или  <code>100 300</code>",
        parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.message(AdminState.export_range_input)
async def admin_export_range_exec(message: Message, state: FSMContext, bls_user_id: str) -> None:
    if await _guard(message, bls_user_id):
        await state.clear()
        return
    data = await state.get_data()
    lang_id, fmt = data["lang_id"], data["fmt"]
    text = (message.text or "").strip()

    # parse "N-M" or "N M"
    try:
        parts = text.replace("-", " ").split()
        start, end = int(parts[0]), int(parts[1])
        if start > end or start < 1:
            raise ValueError
    except (ValueError, IndexError):
        await message.answer("❌ Неверный формат. Введите диапазон, например: <code>1-500</code>",
                             parse_mode="HTML")
        return

    await state.clear()
    status = await message.answer(f"⏳ Экспортирую слова {start}–{end}…")
    bls = get_bls_client()
    file_data = await bls.admin_export_words(bls_user_id, lang_id, fmt, start=start, end=end)
    if not file_data:
        await status.edit_text("❌ Не удалось выполнить экспорт.")
        return
    filename = f"words_{lang_id}_{start}-{end}.{fmt}"
    await message.answer_document(
        BufferedInputFile(file_data, filename=filename),
        caption=f"📥 Экспорт слов {start}–{end} ({fmt.upper()})",
    )
    await status.delete()


@router.callback_query(F.data.startswith("admin:export_dl:"))
async def admin_export_download(callback: CallbackQuery, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    parts = callback.data.split(":")
    lang_id, fmt = parts[2], parts[3]
    await callback.answer("⏳ Генерирую файл…")
    bls = get_bls_client()
    data = await bls.admin_export_words(bls_user_id, lang_id, fmt)
    if not data:
        await callback.message.answer("❌ Не удалось выполнить экспорт.")
        return
    filename = f"words_{lang_id}.{fmt}"
    await callback.message.answer_document(
        BufferedInputFile(data, filename=filename),
        caption=f"📥 Экспорт слов ({fmt.upper()})",
    )


# ── Import ────────────────────────────────────────────────────────────────────

IMPORT_ALLOWED_EXT = {".xlsx", ".csv", ".json"}


@router.callback_query(F.data.startswith("admin:import:"))
async def admin_import_start(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    lang_id = callback.data.split(":", 2)[2]
    kb = _kb(
        [_btn("➕ Добавить к существующим", f"admin:import_mode:{lang_id}:add")],
        [_btn("🗑 Очистить и импортировать", f"admin:import_mode:{lang_id}:clear")],
        [_btn("← Назад", f"admin:lang:{lang_id}")],
    )
    await callback.message.edit_text(
        "📥 <b>Импорт слов</b>\n\nВыберите режим импорта:",
        parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:import_mode:"))
async def admin_import_mode(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    parts = callback.data.split(":")
    lang_id, mode = parts[2], parts[3]
    clear_existing = (mode == "clear")
    await state.set_state(AdminState.import_waiting)
    await state.update_data(lang_id=lang_id, clear_existing=clear_existing)
    mode_text = "🗑 <b>очистить и импортировать</b>" if clear_existing else "➕ <b>добавить к существующим</b>"
    kb = _kb([_btn("Отмена", f"admin:lang:{lang_id}")])
    await callback.message.edit_text(
        f"📥 <b>Импорт слов</b> — {mode_text}\n\n"
        "Пришлите файл <b>XLSX, CSV или JSON</b>:",
        parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.message(AdminState.import_waiting, F.document)
async def admin_import_file(message: Message, state: FSMContext, bls_user_id: str) -> None:
    if await _guard(message, bls_user_id):
        await state.clear()
        return
    data = await state.get_data()
    lang_id = data["lang_id"]
    clear_existing = data["clear_existing"]

    doc: Document = message.document
    filename = doc.file_name or "import.xlsx"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in IMPORT_ALLOWED_EXT:
        await message.answer(
            f"❌ Неподдерживаемый формат файла. Разрешены: XLSX, CSV, JSON\n"
            f"Получен файл: <code>{filename}</code>",
            parse_mode="HTML")
        return

    status = await message.answer("⏳ Загружаю файл…")
    try:
        bot = message.bot
        file = await bot.get_file(doc.file_id)
        file_data = await bot.download_file(file.file_path)
        file_bytes = file_data.read() if hasattr(file_data, "read") else bytes(file_data)
    except Exception as e:
        await status.edit_text(f"❌ Не удалось скачать файл: {e}")
        return

    await status.edit_text("⏳ Отправляю на сервер…")
    await state.clear()

    bls = get_bls_client()
    result = await bls.admin_import_words(bls_user_id, lang_id, file_bytes, filename, clear_existing)

    ok = result.get("ok") or result.get("imported") is not None
    if ok:
        imported = result.get("imported") or result.get("result", {})
        if isinstance(imported, dict):
            n = imported.get("imported", imported.get("count", "?"))
        else:
            n = "?"
        mode_text = "очищены и импортированы" if clear_existing else "добавлены"
        await status.edit_text(
            f"✅ <b>Импорт завершён.</b>\n"
            f"Слов {mode_text}: <b>{n}</b>",
            parse_mode="HTML",
            reply_markup=_kb([_btn("← К языку", f"admin:lang:{lang_id}")]))
    else:
        err = result.get("error") or result.get("detail") or "неизвестная ошибка"
        await status.edit_text(
            f"❌ <b>Ошибка импорта:</b> {err}",
            parse_mode="HTML",
            reply_markup=_kb([_btn("← К языку", f"admin:lang:{lang_id}")]))


@router.message(AdminState.import_waiting)
async def admin_import_wrong_input(message: Message) -> None:
    """User sent text instead of a file in import_waiting state."""
    await message.answer("📎 Пришлите файл XLSX, CSV или JSON.")


# ── Broadcast ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    await state.set_state(AdminState.broadcast_input)
    kb = _kb([_btn("Отмена", "admin:menu")])
    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\nВведите текст сообщения:",
        parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.message(AdminState.broadcast_input)
async def admin_broadcast_send(message: Message, state: FSMContext, bls_user_id: str) -> None:
    if await _guard(message, bls_user_id):
        await state.clear()
        return
    text = message.text or ""
    bot_token = os.environ.get("BOT_TOKEN", "")
    bls = get_bls_client()
    await state.clear()
    status_msg = await message.answer("📤 Отправляю…")

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
                errors += 1
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
        f"✅ <b>Рассылка завершена.</b>\nОтправлено: {sent}, ошибок: {errors}",
        parse_mode="HTML", reply_markup=_kb(_back_menu()))


# ── Diagnostics ───────────────────────────────────────────────────────────────

async def _diag_text() -> str:
    lines = ["🔧 <b>Диагностика сервера</b>", ""]
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        lines += [
            f"CPU: <b>{cpu}%</b>",
            f"RAM: <b>{mem.percent}%</b> ({mem.used // 1024**2} / {mem.total // 1024**2} МБ)",
            f"Disk: <b>{disk.percent}%</b> ({disk.used // 1024**3} / {disk.total // 1024**3} ГБ)",
            "",
        ]
    except ImportError:
        lines.append("(psutil не установлен)")

    # Service statuses
    services = ["langbot-db", "langbot-backend", "langbot-bls", "langbot-web", "langbot-telegram"]
    lines.append("Сервисы:")
    for svc in services:
        try:
            proc = await asyncio.create_subprocess_exec(
                "systemctl", "is-active", svc,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
            status = stdout.decode().strip()
            icon = "🟢" if status == "active" else "🔴"
            lines.append(f"  {icon} {svc}: {status}")
        except Exception:
            lines.append(f"  ❓ {svc}: н/д")

    lines += ["", f"Python: {platform.python_version()}", f"OS: {platform.system()} {platform.release()}"]
    return "\n".join(lines)


@router.callback_query(F.data.in_({"admin:diag", "admin:diag_refresh"}))
async def admin_diag(callback: CallbackQuery, bls_user_id: str) -> None:
    if await _guard(callback, bls_user_id, is_callback=True):
        return
    await callback.answer("⏳")
    text = await _diag_text()
    kb = _kb(
        [_btn("🔄 Обновить", "admin:diag_refresh")],
        _back_menu(),
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
