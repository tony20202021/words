from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from app.bls_client.client import get_bls_client

router = Router()


@router.message(Command("stats"))
async def cmd_stats(message: Message, state: FSMContext, bls_user_id: str) -> None:
    data = await state.get_data()
    language_id = data.get("language_id")

    if not language_id:
        await message.answer("Сначала выберите язык — /language")
        return

    bls = get_bls_client()
    languages = await bls.get_languages()
    lang_name = next((l.get("name_ru", l.get("name_foreign", language_id))
                      for l in languages if l.get("id") == language_id), language_id)

    stats = await bls.get_statistics(bls_user_id, language_id)

    total = stats.get("total_words", 0)
    studied = stats.get("words_studied", 0)
    known = stats.get("words_known", 0)
    skipped = stats.get("words_skipped", 0)
    unknown = stats.get("words_unknown", studied - known - skipped)
    for_today = stats.get("words_for_today", 0)
    pct = stats.get("progress_percentage", 0)

    text = (
        f"📊 <b>Статистика: {lang_name}</b>\n\n"
        f"Всего слов: {total}\n"
        f"Изучено: {studied} ({pct:.1f}%)\n"
        f"  ✅ Знаю: {known}\n"
        f"  ❌ Не знаю: {unknown}\n"
        f"  ⏭ Пропущено: {skipped}\n"
    )
    if for_today > 0:
        text += f"\n🔔 К повторению сегодня: {for_today}"
    else:
        text += "\n✨ На сегодня всё готово!"

    await message.answer(text, parse_mode="HTML")
