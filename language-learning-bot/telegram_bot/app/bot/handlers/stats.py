import asyncio
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from app.bls_client.client import get_bls_client

router = Router()


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

    if len(sections) == 1:
        sections.append("Нет данных — начните изучение.")

    await message.answer("\n\n".join(sections), parse_mode="HTML")
