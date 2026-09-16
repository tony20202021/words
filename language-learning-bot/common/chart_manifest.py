"""Chart sections and captions — single source for BLS and all frontends."""

from typing import Any, Dict, List

MONTHLY_CHART_NAMES = [
    "words_studied",
    "words_new",
    "words_known",
    # Два счётчика недоученного на утро вместо прежнего «до завершения». Тот
    # считал изучено−известно−пропущено, то есть ровно слова со статусом «не
    # знаю»: первый из этих двух его продолжает и историю унаследовал. Новое
    # здесь второе — просроченные по дате проверки, их прежде не считал никто.
    "words_unknown_morning",
    "words_overdue_morning",
    "words_unknown_first_finish",
    "words_for_today",
]

TODAY_CHART_NAMES = ["words_for_today", "words_unknown", "check_interval"]

CHART_CAPTIONS: Dict[str, str] = {
    "words_for_today":            "📅 Слова на сегодня",
    "words_unknown":              "❓ Неизвестные слова",
    "check_interval":             "🔁 Интервалы повторения",
    "words_studied":              "📈 Изучено слов",
    "words_new":                  "🆕 Новых слов в день",
    "words_known":                "✅ Известных слов",
    "words_unknown_morning":      "❌ Осталось «не знаю» со вчера",
    "words_overdue_morning":      "⏳ Недопройдено со вчера",
    # «Объективная» оценка: первое завершение сессии за день, на почти новом
    # наборе слов. Пишется один раз в сутки, значение берётся из базы.
    "words_unknown_first_finish": "🎯 Не знал на первом финише",
}

# type: today | monthly_recent | monthly_all
CHART_SECTIONS: List[Dict[str, Any]] = [
    {
        "header": "📅 Распределение слов",
        "charts": TODAY_CHART_NAMES,
        "type": "today",
    },
    {
        "header": "📆 Прогресс за месяц",
        "charts": MONTHLY_CHART_NAMES,
        "type": "monthly_recent",
    },
    {
        "header": "📊 Прогресс за всё время",
        "charts": MONTHLY_CHART_NAMES,
        "type": "monthly_all",
    },
]
