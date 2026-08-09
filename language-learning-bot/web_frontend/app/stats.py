"""
Сбор статистики сразу по всем языкам.

Собирали её в двух местах и по-разному: /stats через asyncio.gather, а
/languages — циклом, по одному запросу к BLS на язык. При восьми языках это
восемь последовательных HTTP-запросов на первом же экране после входа. Одна
реализация на оба места убирает и расхождение, и лишнее ожидание.
"""

import asyncio
from typing import Any, Dict, List


async def fetch_stats_for_languages(bls, user_id: str, languages: List[dict]) -> Dict[str, Any]:
    """{language_id: статистика} — запросы к BLS уходят параллельно."""
    if not languages:
        return {}
    results = await asyncio.gather(
        *[bls.get_statistics(user_id, lang["id"]) for lang in languages]
    )
    return {lang["id"]: stats for lang, stats in zip(languages, results)}
