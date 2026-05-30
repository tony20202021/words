import asyncio
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from app.bls_client.client import get_bls_client

router = Router()

_TODAY_CHART_NAMES = ["words_for_today", "words_unknown", "check_interval"]
_MONTHLY_CHART_NAMES = ["words_studied", "words_new", "words_known",
                        "words_unknown_before", "words_unknown_after", "words_for_today"]

_CAPTION_MAP = {
    # today
    "words_for_today":      "📅 Слова на сегодня",
    "words_unknown":        "❓ Неизвестные слова",
    "check_interval":       "🔁 Интервалы повторения",
    # monthly
    "words_studied":        "📈 Изучено слов",
    "words_new":            "🆕 Новых слов в день",
    "words_known":          "✅ Известных слов",
    "words_unknown_before": "❌ Неизвестных (до завершения)",
    "words_unknown_after":  "❌ Неизвестных (после завершения)",
}


async def _send_charts(message: Message, bls, user_id: str, lang_id: str, lang_name: str) -> None:
    """Fetch all available charts for a language and send them as photos."""
    # Gather today-charts and monthly-charts concurrently
    today_tasks  = [bls.get_chart(user_id, lang_id, n)         for n in _TODAY_CHART_NAMES]
    monthly_tasks = [bls.get_monthly_chart(user_id, lang_id, n) for n in _MONTHLY_CHART_NAMES]
    today_results, monthly_results = await asyncio.gather(
        asyncio.gather(*today_tasks),
        asyncio.gather(*monthly_tasks),
    )

    charts: list[tuple[str, bytes]] = []
    for name, img in zip(_TODAY_CHART_NAMES, today_results):
        if img:
            charts.append((name, img))
    for name, img in zip(_MONTHLY_CHART_NAMES, monthly_results):
        if img:
            charts.append((name, img))

    if not charts:
        return

    for chart_name, img in charts:
        caption = f"{_CAPTION_MAP.get(chart_name, chart_name)} — {lang_name}"
        await message.answer_photo(
            BufferedInputFile(img, filename=f"{chart_name}.png"),
            caption=caption,
        )


@router.message(Command("stats"))
async def cmd_stats(message: Message, bls_user_id: str) -> None:
    bls = get_bls_client()
    languages = await bls.get_languages()

    if not languages:
        await message.answer("Нет доступных языков.")
        return

    # fetch all stats in parallel
    stats_list = await asyncio.gather(*[bls.get_statistics(bls_user_id, l["id"]) for l in languages])

    sections = ["📊 <b>Статистика</b>"]
    active_langs = []  # (lang, stats) for languages with data

    for lang, stats in zip(languages, stats_list):
        lang_name = lang.get("name_ru", lang.get("name_foreign", lang["id"]))

        total = stats.get("total_words", 0)
        studied = stats.get("words_studied", 0)
        if studied == 0 and total == 0:
            continue

        known = stats.get("words_known", 0)
        skipped = stats.get("words_skipped", 0)
        unknown = stats.get("words_unknown", studied - known - skipped)
        for_today = stats.get("words_for_today", 0)
        pct = stats.get("progress_percentage", 0)
        pct_known = round(known / studied * 100, 1) if studied > 0 else 0

        lines = [f"<b>{lang_name}</b>  {pct:.1f}%"]
        lines.append(f"Всего: {total} | Изучено: {studied}")
        if studied > 0:
            lines.append(f"✅ {known}  ❌ {unknown}  ⏭ {skipped}")
            lines.append(f"Известно/изучено: {pct_known}%")
        if for_today > 0:
            lines.append(f"🔔 К повторению: {for_today}")
        else:
            lines.append("✨ На сегодня готово!")

        sections.append("\n".join(lines))
        active_langs.append((lang, lang_name))

    if len(sections) == 1:
        sections.append("Нет данных — начните изучение.")

    await message.answer("\n\n".join(sections), parse_mode="HTML")


def _format_lang_stats(stats: dict, lang_name: str) -> str:
    """Format statistics for a single language into a text block."""
    studied    = stats.get("words_studied", 0)
    known      = stats.get("words_known", 0)
    skipped    = stats.get("words_skipped", 0)
    unknown    = stats.get("words_unknown", studied - known - skipped)
    total      = stats.get("total_words", 0)
    for_today  = stats.get("words_for_today", 0)
    pct_total  = stats.get("progress_percentage", 0)
    pct_known  = round(known / studied * 100, 1) if studied > 0 else 0

    lines = [f"📊 <b>Статистика: {lang_name}</b>"]
    lines.append(f"Всего слов: {total} | Изучено: {studied}")
    if studied > 0:
        lines.append(f"✅ Известно: {known}  ❌ Неизвестно: {unknown}  ⏭ Пропущено: {skipped}")
        lines.append(f"Прогресс изучено/всего: {pct_total:.1f}%")
        lines.append(f"Прогресс известно/изучено: {pct_known:.1f}%")
    if for_today > 0:
        lines.append(f"🔔 К повторению: {for_today}")
    else:
        lines.append("✨ На сегодня всё готово!")
    return "\n".join(lines)


async def cmd_stats_language(message: Message, bls_user_id: str, language_id: str) -> None:
    """Show statistics and all available charts for a single language."""
    bls = get_bls_client()

    languages = await bls.get_languages()
    lang = next((l for l in languages if l["id"] == language_id), None)
    lang_name = lang.get("name_ru", lang.get("name_foreign", language_id)) if lang else language_id

    stats = await bls.get_statistics(bls_user_id, language_id)
    await message.answer(_format_lang_stats(stats, lang_name), parse_mode="HTML")

    await _send_charts(message, bls, bls_user_id, language_id, lang_name)
