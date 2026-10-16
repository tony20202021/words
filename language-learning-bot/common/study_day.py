"""
Учебные сутки: когда для этого человека начинается новый день.

Зачем это одним местом
----------------------
Границ суток в системе было четыре, и все разные:

  BLS, статистика      полночь UTC — для Рима это 02:00 по-местному
  BLS, сброс сессии    6 часов UTC — то есть 08:00 по-местному
  бэкенд, «на сегодня» полночь UTC
  телефон, офлайн-счёт местная полночь устройства

Ни одна не спрашивала человека, и две из них спорили между собой: занятие в
полпервого ночи телефон относил к новому дню, а сервер — ещё ко вчерашнему.

Теперь граница одна и задаётся двумя настройками: часовой пояс и час начала
учебных суток. Значения по умолчанию (UTC, 0) повторяют прежнее поведение —
переход на новые настройки ничего не сдвигает, пока человек их не задаст.

Почему пояс — названием, а не числом
------------------------------------
«Europe/Rome» переживает перевод часов сам. Числом пришлось бы править дважды
в год, и забытая правка на полгода сдвигала бы границу суток на час.
"""

from datetime import date, datetime, time, timedelta, timezone as _tz
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "UTC"
DEFAULT_DAY_START_HOUR = 0


def zone(name: str) -> ZoneInfo:
    """Пояс по названию; неизвестное название не валит занятие, а даёт UTC."""
    try:
        return ZoneInfo(name or DEFAULT_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return ZoneInfo(DEFAULT_TIMEZONE)


def settings_of(settings: dict | None) -> tuple[str, int]:
    """Пояс и час начала суток из настроек, с умолчаниями."""
    s = settings or {}
    name = s.get("timezone") or DEFAULT_TIMEZONE
    hour = s.get("day_start_hour")
    hour = DEFAULT_DAY_START_HOUR if hour is None else int(hour)
    return name, max(0, min(23, hour))


def study_day(
    now_utc: datetime | None = None,
    timezone: str = DEFAULT_TIMEZONE,
    day_start_hour: int = DEFAULT_DAY_START_HOUR,
) -> date:
    """
    Какие сейчас учебные сутки.

    Занятие до часа начала относится к предыдущим суткам: в полпервого ночи
    человек досиживает вчерашнее занятие, а не начинает сегодняшнее.
    """
    now_utc = now_utc or datetime.utcnow()
    local = now_utc.replace(tzinfo=_tz.utc).astimezone(zone(timezone))
    return (local - timedelta(hours=day_start_hour)).date()


def day_started_utc(
    day: date,
    timezone: str = DEFAULT_TIMEZONE,
    day_start_hour: int = DEFAULT_DAY_START_HOUR,
) -> datetime:
    """
    Момент UTC, когда начались эти учебные сутки, — без tzinfo.

    Нужен для дат следующей проверки: они хранятся в UTC, и если класть их
    ровно на границу суток человека, то обычное сравнение «пора ли повторять»
    остаётся сравнением с текущим моментом и ничего не знает про пояса.
    """
    local = datetime.combine(day, time(hour=day_start_hour), tzinfo=zone(timezone))
    return local.astimezone(_tz.utc).replace(tzinfo=None)


def day_in_days(
    days: int,
    now_utc: datetime | None = None,
    timezone: str = DEFAULT_TIMEZONE,
    day_start_hour: int = DEFAULT_DAY_START_HOUR,
) -> datetime:
    """Начало учебных суток через [days] дней, в UTC — для next_check_date."""
    today = study_day(now_utc, timezone, day_start_hour)
    return day_started_utc(today + timedelta(days=days), timezone, day_start_hour)


def same_study_day(
    a_utc: datetime,
    b_utc: datetime,
    timezone: str = DEFAULT_TIMEZONE,
    day_start_hour: int = DEFAULT_DAY_START_HOUR,
) -> bool:
    """Те же ли это учебные сутки — по ним решается сброс сессии."""
    return (study_day(a_utc, timezone, day_start_hour)
            == study_day(b_utc, timezone, day_start_hour))


def timezone_catalog() -> list[dict]:
    """
    Пояса, сгруппированные по смещению: сначала смещение, внутри — города.

    Владелец: «491 пояс — это многовато, и они повторяются по времени,
    различаются только городами; может, выбор в два шага — сначала смещение в
    часах, их немного, потом внутри смещения город-страну?». Так и сделано:
    смещений около сорока, и человек почти всегда знает своё.

    Берётся не весь перечень IANA — в нём около шестисот названий, половина
    устаревшие синонимы вроде «US/Pacific». Оставляем те, что годятся в
    обычный список настроек: материк/город, без исторических псевдонимов,
    плюс сам UTC.
    """
    from zoneinfo import available_timezones

    now = datetime.now(_tz.utc)
    by_offset: dict[int, list[dict]] = {}
    for name in available_timezones():
        if name != "UTC" and "/" not in name:
            continue                      # EST, MST7MDT и прочие сокращения
        if name.split("/")[0] in _NOT_A_REGION:
            continue
        offset = now.astimezone(zone(name)).utcoffset() or timedelta(0)
        minutes = int(offset.total_seconds() // 60)
        by_offset.setdefault(minutes, []).append({"name": name, "label": _place(name)})

    out = []
    for minutes in sorted(by_offset):
        zones = sorted(by_offset[minutes], key=lambda z: z["label"])
        out.append({"minutes": minutes, "label": _offset_label(minutes), "zones": zones})
    return out


def _offset_label(minutes: int) -> str:
    sign = "+" if minutes >= 0 else "-"
    return f"UTC{sign}{abs(minutes) // 60:02d}:{abs(minutes) % 60:02d}"


def _place(name: str) -> str:
    """«Europe/Rome» → «Rome · Europe»; город первым, его и ищут глазами."""
    if "/" not in name:
        return name
    area, _, city = name.partition("/")
    return f"{city.replace('_', ' ')} · {area.replace('_', ' ')}"


# Не регионы, а наследие: синонимы и устаревшие группы в базе IANA.
_NOT_A_REGION = {"Etc", "US", "Canada", "Brazil", "Mexico", "Chile", "SystemV"}
