"""
Statistics business logic — no aiogram dependencies.
Charts returned as bytes, not sent directly.
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
from app.logger import setup_logger
from app.chart_generator import ProgressChartGenerator

logger = setup_logger(__name__)


def study_day(now: Optional[datetime] = None) -> date:
    """
    Учебные сутки: смена в полночь по Гринвичу.

    Занятие после полуночи по местному времени — это ещё вчерашняя сессия, и
    относить его к новой дате неверно. По Москве граница приходится на 3 часа
    ночи, что и требовалось.

    Раньше BLS брал date.today() — локальную дату СЕРВЕРА, а агрегация бэкенда
    считала «сегодня» по UTC. Две разные точки смены суток в одной системе:
    дневной снимок мог попасть в один день, а счётчик «слов на сегодня» в нём —
    относиться к другому.
    """
    return (now or datetime.utcnow()).date()

EMPTY_PROGRESS: Dict[str, Any] = {
    "words_studied": 0,
    "words_known": 0,
    "words_skipped": 0,
    "total_words": 0,
    "words_for_today": 0,
    "words_unknown_now": 0,
    "words_overdue": 0,
    "progress_percentage": 0,
    "word_numbers_for_today": [],
    "word_numbers_unknown": [],
    "word_check_interval": [],
}


async def get_user_progress(user_id: str, language_id: str, api_client) -> Dict[str, Any]:
    """Fetch current user progress; returns empty progress on 404."""
    response = await api_client.get_user_progress(user_id, language_id)
    if not response["success"] and response.get("status") == 404:
        return EMPTY_PROGRESS.copy()
    return response["result"] or EMPTY_PROGRESS.copy()


def compute_statistics_summary(progress: Dict[str, Any]) -> Dict[str, Any]:
    """Pure computation — derive summary fields from raw progress dict."""
    words_studied = progress.get("words_studied", 0)
    words_known = progress.get("words_known", 0)
    words_skipped = progress.get("words_skipped", 0)
    return {
        **progress,
        "words_unknown": words_studied - words_known - words_skipped,
    }


def generate_today_charts(progress: Dict[str, Any]) -> Dict[str, bytes]:
    """
    Build today-view charts from progress data.
    Returns mapping of chart name → PNG bytes.
    """
    generator = ProgressChartGenerator()
    charts: Dict[str, bytes] = {}

    word_numbers_for_today = progress.get("word_numbers_for_today", [])
    word_numbers_unknown = progress.get("word_numbers_unknown", [])
    word_check_interval = progress.get("word_check_interval", [])
    words_studied = progress.get("words_studied", 0)

    if word_numbers_for_today:
        charts["words_for_today"] = generator.create_words_for_today_histogram(
            word_numbers_for_today, words_studied, x_axis_limits="one_max"
        ).getvalue()

    if word_numbers_unknown:
        charts["words_unknown"] = generator.create_unknown_words_histogram(
            word_numbers_unknown, words_studied, x_axis_limits="one_max"
        ).getvalue()

    if word_check_interval:
        charts["check_interval"] = generator.create_check_interval_histogram(
            word_check_interval, words_studied, x_axis_limits="one_max"
        ).getvalue()

    return charts


async def update_daily_statistics(
    user_id: str,
    language_id: str,
    action_date: date,
    progress: Any,
    api_client,
) -> bool:
    """
    Upsert daily statistics record. Returns True on success.

    progress — либо готовый словарь прогресса, либо функция без аргументов,
    возвращающая корутину с ним. Второй вариант нужен вызывающим, которые сами
    прогресс не используют: снимок пишется только при создании дневной записи,
    то есть раз в сутки, а тянуть ради этого полный прогресс (массивы номеров
    слов на тысячи элементов) на каждое оценённое слово незачем.
    """
    response = await api_client.get_daily_statistics(user_id, language_id, action_date)
    if (
        not response["success"]
        or response.get("status") == 404
        or response["result"] is None
    ):
        if callable(progress):
            progress = await progress()
        update_response = await api_client.update_daily_statistics(
            user_id, language_id, action_date, progress
        )
        if not update_response["success"]:
            logger.error(
                f"Failed to update daily statistics user={user_id} lang={language_id}: "
                f"{update_response.get('error')}"
            )
            return False
    return True


async def write_first_finish_if_missing(
    user_id: str,
    language_id: str,
    action_date: date,
    words_unknown: int,
    api_client,
) -> bool:
    """
    Записать «первый финиш за день» — ровно один раз в сутки.

    Смысл величины: сколько слов человек не знал, впервые дойдя до конца дневной
    порции. Набор слов каждый день почти новый, поэтому число сравнимо изо дня в
    день — это и есть объективная оценка знаний.

    С 10 июня по 16 сентября здесь было другое: запись шла на КАЖДОЕ «не знаю»,
    а значением был счётчик ошибок сессии. Он считал ответы, а не слова (одно
    слово, отвеченное неверно дважды, давало два), жил внутри сессии, а сессия
    за день начинается заново от двух до десяти раз. В итоге график показывал
    максимум ошибок одной сессии вместо незнания на первом проходе.
    """
    existing = await api_client.get_daily_first_finish_statistics(user_id, language_id, action_date)
    already = (
        existing["success"]
        and existing.get("status") != 404
        and existing["result"] is not None
    )
    if already:
        return True

    update_response = await api_client.update_daily_first_finish_statistics(
        user_id, language_id, action_date, {"words_unknown": words_unknown}
    )
    if not update_response["success"]:
        logger.error(
            f"Failed to write first-finish statistics user={user_id} lang={language_id}: "
            f"{update_response.get('error')}"
        )
        return False
    return True


async def update_daily_max_word_number(
    user_id: str,
    language_id: str,
    action_date: date,
    word_number: int,
    api_client,
) -> None:
    """Update max_word_number in today's daily record (uses $max on backend — always safe to call)."""
    if not word_number:
        return
    await api_client.update_daily_statistics(
        user_id, language_id, action_date, {"max_word_number": word_number}
    )




async def get_monthly_statistics(
    user_id: str,
    language_id: str,
    action_date: date,
    api_client,
    show_all: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Fetch and annotate monthly statistics.
    Returns (all_days_stats, first_finish_stats) with computed fields.

    «Последний финиш» больше не запрашивается: график убран как избыточный —
    сколько слов осталось после последней сессии, видно в утреннем счётчике
    следующего дня. Лишний запрос на каждую картинку тоже ни к чему.
    """
    if show_all:
        response = await api_client.get_all_monthly_statistics(user_id, language_id, action_date)
    else:
        response = await api_client.get_monthly_statistics(user_id, language_id, action_date)

    if not response["success"] or response.get("status") == 404 or response["result"] is None:
        logger.error(f"No monthly statistics user={user_id} lang={language_id}")
        return [], []

    monthly = response["result"]
    all_days: List[Dict[str, Any]] = list(monthly.get("daily_stats", []))
    # «Новых слов в день».
    #
    # Снимок words_studied за день пишется ОДИН раз — на первом ответе дня, до
    # того как выучены новые слова: update_daily_statistics создаёт запись и
    # больше её не обновляет. Значит снимок дня D — это итог дня D−1, и разница
    # двух соседних снимков описывает слова, выученные в более РАННИЙ из дней.
    #
    # Раньше её относили к более позднему, и весь график ехал на сутки. Нули
    # переезжали туда, где новые слова точно были: 13.08 новых не было, 14.08
    # выучено пять — а график ставил ноль на 14.08. По 56 парам соседних дней
    # разница совпала с датами создания слов в 55 случаях именно при таком
    # отнесении и лишь в 16 — при прежнем.
    #
    # У последнего дня следующего снимка ещё нет, и точки у него не будет, пока
    # завтрашний первый ответ его не создаст. Отсутствующая точка лучше неверной,
    # а тянуть ради неё полный прогресс на каждую картинку незачем.
    #
    # Утренние счётчики недоученного при этом не трогаются: они и так снимаются
    # с состояния базы на первом ответе дня, то есть по вчерашнему итогу.
    for i, day in enumerate(all_days):
        if i + 1 >= len(all_days):
            day["words_new"] = None
            continue
        delta = all_days[i + 1]["words_studied"] - day["words_studied"]
        day["words_new"] = delta if delta >= 0 else None

    def _annotate_finish(raw_response) -> List[Dict[str, Any]]:
        if not raw_response["success"] or raw_response.get("status") == 404 or raw_response["result"] is None:
            return []
        result = []
        for day in raw_response["result"].get("daily_stats", []):
            # New records store words_unknown directly; legacy records fall back to computation.
            if day.get("words_unknown") is None:
                day["words_unknown"] = day["words_studied"] - day["words_known"] - day["words_skipped"]
            result.append(day)
        return result

    if show_all:
        ff_resp = await api_client.get_all_monthly_first_finish_statistics(
            user_id, language_id, action_date)
    else:
        ff_resp = await api_client.get_monthly_first_finish_statistics(
            user_id, language_id, action_date)

    return all_days, _annotate_finish(ff_resp)


# Месячные графики: (источник, имя графика, поле, что писать в заголовке).
# Константа модуля, а не список внутри функции: по этим же полям кеш картинок
# снимает отпечаток данных (app/services/chart_cache.py) — одно место правды.
#
# max_word_number здесь больше нет: его не показывает ни один клиент, а
# рисовался он на каждый пересчёт, восьмым из восьми.
MONTHLY_SPECS = [
    ("days",         "words_studied",              "words_studied",     "last"),
    ("days",         "words_new",                  "words_new",         "max"),
    ("days",         "words_known",                "words_known",       "last"),
    # Первый счётчик — продолжение прежнего «до завершения»: та же величина,
    # но взятая из базы, а не пересчитанная из трёх полей. Второй считает
    # просроченные по дате проверки — этого прежде не было вовсе.
    ("days",         "words_unknown_morning",      "words_unknown_now", "max"),
    ("days",         "words_overdue_morning",      "words_overdue",     "max"),
    ("first_finish", "words_unknown_first_finish", "words_unknown",     "max"),
    ("days",         "words_for_today",            "words_for_today",   "max"),
]


def generate_monthly_charts(
    all_days_stats: List[Dict[str, Any]],
    first_finish_stats: List[Dict[str, Any]],
    show_all: bool = False,
) -> Dict[str, bytes]:
    """Build monthly-view charts. Returns mapping of chart name → PNG bytes."""
    if not all_days_stats:
        return {}

    generator = ProgressChartGenerator()
    y_limits = "zero_max" if show_all else "min_max"
    charts: Dict[str, bytes] = {}

    # Ось от нуля обязательна там, где величина — счётчик за день: «слов на
    # сегодня» колеблется от 13 до 33, и без нуля это выглядит как размах в разы.
    # Накопительным (изучено, известно) нуль, наоборот, вреден: они прижмутся к
    # верхнему краю и перестанут показывать движение.
    ZERO_BASED_CHARTS = {"words_for_today"}

    sources = {"days": all_days_stats, "first_finish": first_finish_stats}

    for source, chart_key, field, title_value in MONTHLY_SPECS:
        data = sources[source]
        if data:
            charts[chart_key] = generator.create_counts_plot(
                data,
                field,
                title=chart_key.replace("_", " ").capitalize(),
                title_value=title_value,
                y_axis_limits="zero_max" if chart_key in ZERO_BASED_CHARTS else y_limits,
            ).getvalue()

    return charts
