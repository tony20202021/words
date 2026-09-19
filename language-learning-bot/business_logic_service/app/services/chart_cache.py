"""Кеш картинок статистики: пересчёт — только когда меняются данные.

Прежде кеш жил 60 секунд. Графики открывают изредка, поэтому почти каждое
открытие попадало на холодный кеш, и сервер перерисовывал всё заново: 6,5 с на
экран, из них две группы месячных графиков по ~2,8 с. При этом данные месячных
графиков за день меняются два-три раза — утренней записью и первым финишем.

Теперь ключ — отпечаток данных, которые идут на картинку. Пока они те же,
картинка отдаётся готовой, сколько бы времени ни прошло; поменялись — рисуется
заново. Устаревшую картинку так получить нельзя: другие данные — другой ключ.

Отпечаток снимается только с отрисовываемых полей. В записи дня есть
max_word_number и время обновления, которые меняются на каждом ответе, —
учитывай их, кеш сбрасывался бы от каждого слова.

Заранее — после учёбы, а не во время. Отрисовка держит процессор секунды, и во
время занятия отнимала бы его у карточек. Поэтому перерисовка откладывается на
две минуты после последнего ответа и только тем, кто открывал графики в
последние две недели: остальным она не нужна.
"""

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from functools import partial
from typing import Any, Callable, Dict, Hashable, Tuple

from app.logger import setup_logger
from app import chart_generator
from app.services import statistics_service

logger = setup_logger(__name__)

_MAX_ENTRIES = 256
WARM_DELAY_SECONDS = 120.0
VIEWERS_WINDOW_SECONDS = 14 * 24 * 3600

# Два варианта картинки: для экрана — быстро заполнить страницу, для
# увеличения — подкачать фоном. Кешируются раздельно.
VARIANTS = {"screen": chart_generator._DPI, "zoom": chart_generator.ZOOM_DPI}

_cache: "OrderedDict[str, Dict[str, bytes]]" = OrderedDict()
_current: Dict[Hashable, str] = {}           # что сейчас лежит для графика → ключ
_locks: Dict[str, asyncio.Lock] = {}
_viewed: Dict[Tuple[str, str], float] = {}  # (пользователь, язык) → когда смотрел
_pending: Dict[Tuple[str, str], asyncio.Task] = {}


def _fingerprint(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha1(raw.encode()).hexdigest()


def _monthly_payload(all_days, first_finish, show_all: bool) -> Dict[str, Any]:
    def fields(source):
        return sorted({f for src, _, f, _ in statistics_service.MONTHLY_SPECS if src == source})
    day_fields, ff_fields = fields("days"), fields("first_finish")
    return {
        "show_all": show_all,
        "days": [[d.get("date")] + [d.get(f) for f in day_fields] for d in all_days],
        "first_finish": [[d.get("date")] + [d.get(f) for f in ff_fields] for d in first_finish],
    }


def _today_payload(progress: Dict[str, Any]) -> Dict[str, Any]:
    return {k: progress.get(k) for k in (
        "word_numbers_for_today", "word_numbers_unknown",
        "word_check_interval", "words_studied")}


async def _cached(slot: Hashable, fingerprint: str,
                  generator: Callable[[], Dict[str, bytes]]) -> Dict[str, bytes]:
    key = f"{slot}|{fingerprint}"
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:                     # одна отрисовка на ключ, сколько бы ни просили
        if key in _cache:
            return _cache[key]
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, generator)
        previous = _current.get(slot)
        if previous and previous != key:
            _cache.pop(previous, None)   # прежние данные этого графика больше не нужны
            _locks.pop(previous, None)
        _cache[key] = data
        _current[slot] = key
        while len(_cache) > _MAX_ENTRIES:
            old, _ = _cache.popitem(last=False)
            _locks.pop(old, None)
        return data


def _at(variant: str, generator: Callable[[], Dict[str, bytes]]) -> Callable[[], Dict[str, bytes]]:
    """Отрисовка в разрешении варианта. Выполняется в потоке исполнителя."""
    dpi = VARIANTS[variant]

    def run():
        with chart_generator.render_dpi(dpi):
            return generator()
    return run


async def monthly_charts(user_id: str, language_id: str, show_all: bool,
                         api_client, variant: str = "screen") -> Dict[str, bytes]:
    all_days, first_finish = await statistics_service.get_monthly_statistics(
        user_id, language_id, statistics_service.study_day(), api_client, show_all=show_all)
    return await _cached(
        ("monthly", user_id, language_id, show_all, variant),
        _fingerprint(_monthly_payload(all_days, first_finish, show_all)),
        _at(variant, partial(statistics_service.generate_monthly_charts, all_days,
                             first_finish, show_all=show_all)))


async def today_charts(user_id: str, language_id: str, api_client,
                       variant: str = "screen") -> Dict[str, bytes]:
    progress = await statistics_service.get_user_progress(user_id, language_id, api_client)
    return await _cached(
        ("today", user_id, language_id, variant),
        _fingerprint(_today_payload(progress)),
        _at(variant, lambda: statistics_service.generate_today_charts(progress)))


def note_view(user_id: str, language_id: str) -> None:
    """Человек открыл графики — значит, их стоит готовить ему заранее."""
    _viewed[(user_id, language_id)] = time.time()


def schedule_warm(user_id: str, language_id: str, api_client) -> None:
    """Перерисовать месячные графики, когда человек закончит заниматься.

    Каждый ответ отодвигает перерисовку ещё на WARM_DELAY_SECONDS: пока идёт
    учёба, процессор отдан карточкам.
    """
    slot = (user_id, language_id)
    seen = _viewed.get(slot)
    if seen is None or time.time() - seen > VIEWERS_WINDOW_SECONDS:
        return
    previous = _pending.pop(slot, None)
    if previous and not previous.done():
        previous.cancel()
    _pending[slot] = asyncio.get_running_loop().create_task(
        _warm_later(user_id, language_id, api_client))


async def _warm_later(user_id: str, language_id: str, api_client) -> None:
    slot = (user_id, language_id)
    try:
        await asyncio.sleep(WARM_DELAY_SECONDS)
        started = time.perf_counter()
        # Сначала экранные — они нужны первыми; потом для увеличения.
        for variant in ("screen", "zoom"):
            for show_all in (False, True):
                await monthly_charts(user_id, language_id, show_all, api_client, variant)
        logger.info(f"Charts warmed user={user_id} lang={language_id} "
                    f"in {time.perf_counter() - started:.1f}s")
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.warning(f"Chart warm failed user={user_id} lang={language_id}: {e}")
    finally:
        if _pending.get(slot) is asyncio.current_task():
            _pending.pop(slot, None)
