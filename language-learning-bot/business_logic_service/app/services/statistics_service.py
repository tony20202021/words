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

EMPTY_PROGRESS: Dict[str, Any] = {
    "words_studied": 0,
    "words_known": 0,
    "words_skipped": 0,
    "total_words": 0,
    "words_for_today": 0,
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
    progress: Dict[str, Any],
    api_client,
) -> bool:
    """Upsert daily statistics record. Returns True on success."""
    response = await api_client.get_daily_statistics(user_id, language_id, action_date)
    if (
        not response["success"]
        or response.get("status") == 404
        or response["result"] is None
    ):
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


async def update_daily_first_finish_statistics(
    user_id: str,
    language_id: str,
    action_date: date,
    progress: Dict[str, Any],
    api_client,
) -> bool:
    """Record first real session completion. Backend ignores if real data already exists."""
    update_response = await api_client.update_daily_first_finish_statistics(
        user_id, language_id, action_date, {**progress, "is_seeded": False}
    )
    if not update_response["success"]:
        logger.error(
            f"Failed to update first-finish statistics user={user_id} lang={language_id}: "
            f"{update_response.get('error')}"
        )
        return False
    return True


async def update_daily_last_finish_statistics(
    user_id: str,
    language_id: str,
    action_date: date,
    progress: Dict[str, Any],
    api_client,
) -> bool:
    """Always overwrites last-finish record with most recent session completion data."""
    update_response = await api_client.update_daily_last_finish_statistics(
        user_id, language_id, action_date, progress
    )
    if not update_response["success"]:
        logger.error(
            f"Failed to update last-finish statistics user={user_id} lang={language_id}: "
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
    await api_client.update_daily_first_finish_statistics(
        user_id, language_id, action_date, {"max_word_number": word_number}
    )


async def create_first_finish_if_missing(
    user_id: str,
    language_id: str,
    action_date: date,
    progress: Dict[str, Any],
    api_client,
) -> bool:
    """Create first-finish record only if one doesn't exist yet today.
    Called from _bg_update_daily so the chart always has a daily entry
    even when the user never exhausts all session batches."""
    response = await api_client.get_daily_first_finish_statistics(user_id, language_id, action_date)
    if (
        not response["success"]
        or response.get("status") == 404
        or response["result"] is None
    ):
        update_response = await api_client.update_daily_first_finish_statistics(
            user_id, language_id, action_date, {**progress, "is_seeded": True}
        )
        if not update_response["success"]:
            logger.error(
                f"Failed to create first-finish snapshot user={user_id} lang={language_id}: "
                f"{update_response.get('error')}"
            )
            return False
    return True


async def get_monthly_statistics(
    user_id: str,
    language_id: str,
    action_date: date,
    api_client,
    show_all: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Fetch and annotate monthly statistics.
    Returns (all_days_stats, first_finish_stats, last_finish_stats) with computed fields.
    """
    if show_all:
        response = await api_client.get_all_monthly_statistics(user_id, language_id, action_date)
    else:
        response = await api_client.get_monthly_statistics(user_id, language_id, action_date)

    if not response["success"] or response.get("status") == 404 or response["result"] is None:
        logger.error(f"No monthly statistics user={user_id} lang={language_id}")
        return [], [], []

    monthly = response["result"]
    all_days: List[Dict[str, Any]] = []
    prev_studied = None
    for day in monthly.get("daily_stats", []):
        day["words_unknown"] = day["words_studied"] - day["words_known"] - day["words_skipped"]
        if prev_studied is None:
            day["words_new"] = None
        else:
            delta = day["words_studied"] - prev_studied
            day["words_new"] = delta if delta >= 0 else None
        prev_studied = day["words_studied"]
        all_days.append(day)

    def _annotate_finish(raw_response) -> List[Dict[str, Any]]:
        if not raw_response["success"] or raw_response.get("status") == 404 or raw_response["result"] is None:
            return []
        result = []
        for day in raw_response["result"].get("daily_stats", []):
            day["words_unknown"] = day["words_studied"] - day["words_known"] - day["words_skipped"]
            result.append(day)
        return result

    if show_all:
        ff_resp, lf_resp = await asyncio.gather(
            api_client.get_all_monthly_first_finish_statistics(user_id, language_id, action_date),
            api_client.get_all_monthly_last_finish_statistics(user_id, language_id, action_date),
        )
    else:
        ff_resp, lf_resp = await asyncio.gather(
            api_client.get_monthly_first_finish_statistics(user_id, language_id, action_date),
            api_client.get_monthly_last_finish_statistics(user_id, language_id, action_date),
        )

    return all_days, _annotate_finish(ff_resp), _annotate_finish(lf_resp)


def generate_monthly_charts(
    all_days_stats: List[Dict[str, Any]],
    first_finish_stats: List[Dict[str, Any]],
    last_finish_stats: List[Dict[str, Any]],
    show_all: bool = False,
) -> Dict[str, bytes]:
    """Build monthly-view charts. Returns mapping of chart name → PNG bytes."""
    if not all_days_stats:
        return {}

    generator = ProgressChartGenerator()
    y_limits = "zero_max" if show_all else "min_max"
    charts: Dict[str, bytes] = {}

    specs = [
        (all_days_stats,    "words_studied",            "words_studied",   "last"),
        (all_days_stats,    "words_new",                "words_new",       "max"),
        (all_days_stats,    "words_known",              "words_known",     "last"),
        (all_days_stats,    "words_unknown_before",     "words_unknown",   "max"),
        (first_finish_stats,"words_unknown_first_finish","words_unknown",  "max"),
        (last_finish_stats, "words_unknown_last_finish", "words_unknown",  "max"),
        (all_days_stats,    "words_for_today",          "words_for_today", "max"),
        (all_days_stats,    "max_word_number",          "max_word_number", "max"),
    ]

    for data, chart_key, field, title_value in specs:
        if data:
            charts[chart_key] = generator.create_counts_plot(
                data,
                field,
                title=chart_key.replace("_", " ").capitalize(),
                title_value=title_value,
                y_axis_limits=y_limits,
            ).getvalue()

    return charts
