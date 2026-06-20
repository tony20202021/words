"""Chart sections and captions — single source for BLS and all frontends."""

from typing import Any, Dict, List

MONTHLY_CHART_NAMES = [
    "words_studied",
    "words_new",
    "words_known",
    "words_unknown_before",
    "words_unknown_first_finish",
    "words_unknown_last_finish",
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
    "words_unknown_before":       "❌ Неизвестных (до завершения)",
    "words_unknown_first_finish": "❌ Неизвестных (1-й финиш за день)",
    "words_unknown_last_finish":  "❌ Неизвестных (последний финиш)",
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
