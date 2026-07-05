import os
import sys
from pathlib import Path
import asyncio
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.bls_client.client import BLSClient, get_bls_client
from app.bot.keyboards import build_language_keyboard, build_welcome_keyboard

from app.bls_client.client import get_bls_client as _get_bls_client

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from common.version import __version__

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

    first_name = message.from_user.first_name or ""

    # Сообщение 1 — приветствие
    await message.answer(
        f"Здравствуйте, {first_name}!\n"
        f"Добро пожаловать в бот для изучения иностранных слов! <i>(v{__version__})</i>",
        parse_mode="HTML",
    )

    # Сообщение 2 — навигация
    await message.answer(
        "🌐 Веб-версия: /web\n"
        "📱 Android-приложение: /android\n"
        "🔑 Войти в приложение: /connect_android",
    )

    # Сообщение 3 — статистика по языкам (параллельно)
    stats_list = await asyncio.gather(*[bls.get_statistics(bls_user_id, l["id"]) for l in languages])
    stats_lines = [
        f"В системе доступно для изучения:\n{len(languages)} языков.",
        "📊 Ваш прогресс по языкам:",
    ]
    for lang, stat in zip(languages, stats_list):
        pct = stat.get("progress_percentage", 0.0)
        total = stat.get("total_words", 0)
        for_today = stat.get("words_for_today", 0)
        today_str = f", {for_today} к повторению" if for_today else ""
        stats_lines.append(f"• {lang['name_ru']}: {pct:.1f}% ({total} слов{today_str})")
    stats_lines.append("📋 Используйте кнопки ниже для навигации:")
    await message.answer(
        "\n".join(stats_lines),
        reply_markup=build_welcome_keyboard(),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("welcome:"))
async def welcome_nav(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    action = callback.data.split(":", 1)[1]
    await callback.answer()
    if action == "language":
        await _send_language_selection(callback.message, bls_user_id, state)
    elif action == "stats":
        from app.bot.handlers.stats import cmd_stats
        await cmd_stats(callback.message, bls_user_id)
    elif action == "android":
        await cmd_android(callback.message)

    elif action == "hints":
        await callback.message.answer(
            "💡 <b>О подсказках</b>\n\n"
            "Подсказки помогают запомнить слово:\n"
            "• <b>Фонетическая</b> — звуковая ассоциация\n"
            "• <b>Ассоциация</b> — образная связь\n"
            "• <b>Значение</b> — пояснение смысла\n"
            "• <b>Написание</b> — подсказка по написанию\n\n"
            "Настройки подсказок: /settings",
            parse_mode="HTML",
        )
    elif action == "help":
        from app.bot.handlers.help import cmd_help as _cmd_help
        await _cmd_help(callback.message)


@router.message(Command("web"))
async def cmd_web(message: Message, bls_user_id: str) -> None:
    web_url = os.environ.get("WEB_URL", "http://136.244.102.39:8548")
    bls = get_bls_client()
    result = await bls.mobile_create_token(bls_user_id)
    code = result.get("code") if result else None
    if code:
        url = f"{web_url}/login?code={code}"
        caption = (
            f"🌐 <b>Веб-версия</b>\n\n"
            f"Код: <code>{code}</code>\n\n"
            f"{url}\n\n"
            f"<i>Ссылка действует 10 минут и используется один раз.</i>"
        )
        # Try to send QR code image with caption
        qr_png = await bls.get_qr_png(url)
        if qr_png:
            from aiogram.types import BufferedInputFile
            await message.answer_photo(
                BufferedInputFile(qr_png, filename="web_qr.png"),
                caption=caption,
                parse_mode="HTML",
            )
        else:
            await message.answer(caption, parse_mode="HTML", disable_web_page_preview=True)
    else:
        await message.answer(f"🌐 <b>Веб-версия</b>\n{web_url}",
                             parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("connect_android"))
async def cmd_connect_android(message: Message, bls_user_id: str) -> None:
    """Generate a one-time code the user enters in the Android app to log in."""
    bls = get_bls_client()
    result = await bls.mobile_create_token(bls_user_id)
    if not result or "code" not in result:
        await message.answer("Не удалось создать код. Попробуйте позже.")
        return
    code = result["code"]
    bls_url = os.environ.get("BLS_PUBLIC_URL") or os.environ.get("BLS_URL", "http://localhost:8531")
    await message.answer(
        f"📱 <b>Подключение Android-приложения</b>\n\n"
        f"Адрес сервера:\n<code>{bls_url}</code>\n\n"
        f"Код:\n<code>{code}</code>\n\n"
        f"<i>Код действителен 10 минут и используется один раз.</i>",
        parse_mode="HTML",
    )


_APK_PATH = Path(__file__).parent.parent.parent.parent.parent / "android" / "LangBot.apk"


@router.message(Command("android"))
async def cmd_android(message: Message) -> None:
    """Send the LangBot APK file for direct installation."""
    if not _APK_PATH.exists():
        await message.answer("APK не найден. Обратитесь к администратору.")
        return
    web_url = os.environ.get("WEB_URL", "http://136.244.102.39:8548")
    download_url = f"{web_url}/download/android"
    text = (
        f"📱 <b>LangBot для Android</b> v{__version__}\n\n"
        f"1. Нажмите на файл → <b>Открыть</b>\n"
        f"2. Разрешите установку из Telegram (один раз)\n"
        f"3. Установите приложение\n"
        f"4. В приложении введите адрес BLS и код из /connect_android\n\n"
        f"Или скачайте по ссылке:\n{download_url}"
    )
    bls = get_bls_client()
    qr_png = await bls.get_qr_png(download_url)
    if qr_png:
        from aiogram.types import BufferedInputFile
        await message.answer_photo(
            BufferedInputFile(qr_png, filename="android_qr.png"),
            caption=text,
            parse_mode="HTML",
        )
    else:
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
    apk = FSInputFile(_APK_PATH, filename=f"LangBot-v{__version__}.apk")
    await message.answer_document(apk)


async def _send_language_selection(target_message, bls_user_id: str, state: FSMContext) -> None:
    """Полное сообщение выбора языка — как в старом боте."""
    bls = get_bls_client()
    languages = await bls.get_languages()

    state_data = await state.get_data()
    current_lang_id = state_data.get("language_id")

    # Собираем статистику по всем языкам (параллельно)
    stats_list = await asyncio.gather(*[bls.get_statistics(bls_user_id, l["id"]) for l in languages])
    lang_stats = [{**lang, "stat": stat} for lang, stat in zip(languages, stats_list)]

    lines = []

    # Текущий язык
    current = next((l for l in lang_stats if l["id"] == current_lang_id), None)
    if current:
        s = current["stat"]
        pct = s.get("progress_percentage", 0)
        studied = s.get("words_studied", 0)
        lines.append(
            f"🔹 Текущий язык: {current['name_ru']} ({current['name_foreign']})"
            + (f" - Прогресс: {pct:.1f}% ({studied} изучено)" if studied > 0 else "")
        )
        lines.append("")

    lines.append("🌍 Доступные языки для изучения:\n")
    for l in lang_stats:
        if l["id"] == current_lang_id:
            continue
        s = l["stat"]
        total = s.get("total_words", 0)
        studied = s.get("words_studied", 0)
        pct = s.get("progress_percentage", 0)
        for_today = s.get("words_for_today", 0)
        row = f"• {l['name_ru']} ({l['name_foreign']}) - {total} слов"
        if studied > 0:
            row += f" - Прогресс: {pct:.1f}% ({studied} изучено)"
        if for_today > 0:
            row += f" - {for_today} к повторению"
        lines.append(row)

    lines.append("\nВыберите язык с помощью кнопок ниже:")
    lines.append("\nДругие доступные команды:")
    lines.append("/start - Вернуться на начальный экран")
    lines.append("/help - Получить справку")
    lines.append("/android - Скачать Android-приложение")
    lines.append("/stats - Показать статистику")

    # Кнопки с кол-вом слов и прогрессом
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for l in lang_stats:
        s = l["stat"]
        total = s.get("total_words", 0)
        studied = s.get("words_studied", 0)
        pct = s.get("progress_percentage", 0)
        for_today = s.get("words_for_today", 0)
        btn = f"{l['name_ru']} ({l['name_foreign']}) - {total} сл."
        if studied > 0:
            btn += f" - {pct:.1f}%"
        if for_today > 0:
            btn += f" 🔔{for_today}"
        builder.button(text=btn, callback_data=f"lang:{l['id']}")
    builder.adjust(1)

    await target_message.answer("\n".join(lines), reply_markup=builder.as_markup())


@router.message(Command("language"))
async def cmd_language(message: Message, state: FSMContext, bls_user_id: str) -> None:
    await _send_language_selection(message, bls_user_id, state)


def _bool(v: bool) -> str:
    return "✅" if v else "❌"


@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def select_language(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    language_id = callback.data.split(":", 1)[1]
    bls = get_bls_client()
    await callback.answer()

    # Получаем данные языка
    languages = await bls.get_languages()
    lang = next((l for l in languages if l["id"] == language_id), None)
    lang_name = f"{lang['name_ru']} ({lang['name_foreign']})" if lang else language_id

    await state.update_data(bls_user_id=bls_user_id, language_id=language_id, language_name=lang["name_ru"] if lang else language_id)

    # Сообщение 1 — выбранный язык
    await callback.message.answer(
        f"✅ Вы выбрали язык: <b>{lang_name}</b>",
        parse_mode="HTML",
    )

    # Сообщение 2 — настройки
    s = await bls.get_settings(bls_user_id, language_id)

    def b(v): return "✅" if v else "❌"

    settings_lines = [
        "⚙️ <b>Ваши настройки для этого языка:</b>",
        f"   • Короткие подписи: <b>{b(s.get('show_short_captions', True))}</b>",
        f"   • Начальное слово: <b>{s.get('start_word', 1)}</b>",
        f"   • Пропускать исключённые слова: <b>{b(s.get('skip_marked', False))}</b>",
        "",
        "🖼️ <b>Настройки даты проверки:</b>",
        f"   • Период повторения: <b>{b(s.get('use_check_date', True))}</b>",
        f"   • Дата проверки: <b>{b(s.get('show_check_date', True))}</b>",
        "",
        "💡 <b>Настройки подсказок:</b>",
        f"   • Фонетика: <b>{b(s.get('show_hint_phoneticsound', False))}</b>",
        f"   • Ассоциация: <b>{b(s.get('show_hint_phoneticassociation', False))}</b>",
        f"   • Значение: <b>{b(s.get('show_hint_meaning', False))}</b>",
        f"   • Написание: <b>{b(s.get('show_hint_writing', False))}</b>",
        "",
        "🖼️ <b>Настройки написания:</b>",
        f"   • Крупное написание: <b>{b(s.get('show_big', False))}</b>",
        f"   • Картинки написания: <b>{b(s.get('show_writing_images', False))}</b>",
        f"   • Радикалы: <b>{b(s.get('show_radicals', True))}</b>",
        f"   • Ссылки: <b>{b(s.get('show_references', True))}</b>",
        f"   • Тоны: <b>{b(s.get('show_tones', True))}</b>",
        f"   • Звуки: <b>{b(s.get('show_sounds', True))}</b>",
        f"   • Доп. транскрипция: <b>{b(s.get('random_transcription', True))}</b>",
        f"   • Доп. звук: <b>{b(s.get('random_sound', True))}</b>",
        f"   • Pick mode: <b>{b(s.get('random_pick_mode', False))}</b> (вариантов: {s.get('quiz_options_count', 3)})",
        "",
        f"📊 Графики: <b>{b(s.get('show_charts', False))}</b>",
        f"📤 Получать сообщения: <b>{b(s.get('receive_messages', True))}</b>",
        "",
        "🔄 <b>Сброс сессии:</b>",
        f"   • перерыв за день: <b>{s.get('reset_same_day_hours', 16)}</b> ч",
        f"   • час после полуночи: <b>{s.get('reset_cross_midnight_hours', 6)}</b>",
        f"🔄 Лимит неизвестных слов: <b>{s.get('unknown_limit_new_words', 10)}</b>",
        f"🔁 Макс. интервал: <b>{s.get('max_check_interval', 365)}</b> дн",
    ]
    await callback.message.answer("\n".join(settings_lines), parse_mode="HTML")

    # Сообщение 3 — статистика
    stat = await bls.get_statistics(bls_user_id, language_id)
    studied = stat.get("words_studied", 0)
    known = stat.get("words_known", 0)
    skipped = stat.get("words_skipped", 0)
    unknown = studied - known - skipped
    total = stat.get("total_words", 0)
    for_today = stat.get("words_for_today", 0)
    pct_total = stat.get("progress_percentage", 0)
    pct_known = round(known / studied * 100, 1) if studied > 0 else 0
    await callback.message.answer(
        f"📊 <b>Ваша статистика по этому языку:</b>\n"
        f"- Изучено слов: {studied}\n"
        f"- Пропущено слов: {skipped}\n"
        f"- Известно слов: {known}\n"
        f"- Неизвестно слов: {unknown}\n"
        f"- Слов на текущую сессию: {for_today}\n"
        f"- Всего слов: {total}\n"
        f"Прогресс изучено/всего: {pct_total:.1f}%\n"
        f"Прогресс известно/изучено: {pct_known:.1f}%",
        parse_mode="HTML",
    )

    # Сообщение 4 — действия с клавиатурой
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.button(text="📚 Начать заново",    callback_data=f"study_start:{language_id}")
    builder.button(text="⚙️ Настройки",       callback_data=f"nav:settings:{language_id}")
    builder.button(text="🌐 Другой язык",     callback_data="welcome:language")
    builder.button(text="📊 Статистика",      callback_data=f"nav:stats:{language_id}")
    builder.adjust(2, 2)
    await callback.message.answer(
        "Теперь вы можете:\n- Продолжить изучение: /study\n- Настроить процесс: /settings",
        reply_markup=builder.as_markup(),
    )

    await state.set_state(UserState.studying)


@router.callback_query(lambda c: c.data and c.data.startswith("nav:"))
async def nav_callback(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    parts = callback.data.split(":", 2)
    action = parts[1]
    lang_id = parts[2] if len(parts) > 2 else None
    await callback.answer()
    if action == "settings":
        if lang_id:
            await state.update_data(language_id=lang_id)
        from app.bot.handlers.settings import cmd_settings
        await cmd_settings(callback.message, state, bls_user_id)
    elif action == "stats":
        if lang_id:
            from app.bot.handlers.stats import cmd_stats_language
            await cmd_stats_language(callback.message, bls_user_id, lang_id)
        else:
            from app.bot.handlers.stats import cmd_stats
            await cmd_stats(callback.message, bls_user_id)


@router.callback_query(lambda c: c.data and c.data.startswith("study_start:"))
async def study_start(callback: CallbackQuery, state: FSMContext, bls_user_id: str) -> None:
    from app.bot.handlers.study import _display_card
    language_id = callback.data.split(":", 1)[1]
    await callback.answer()

    bls = get_bls_client()
    resp = await bls.start_session(bls_user_id, language_id)

    if resp is None:
        await callback.message.answer("Нет слов для изучения.")
        return

    card = resp.get("card")
    if card is None:
        await callback.message.answer("На сегодня всё изучено! 🎉")
        return

    await state.set_state(UserState.studying)
    await state.update_data(bls_user_id=bls_user_id, language_id=language_id)
    await _display_card(callback.message, card, language_id, bls, edit_mode=False)
