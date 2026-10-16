"""
Учебные сутки: одна граница на всю систему, заданная человеком.

Раньше границ было четыре и все разные — полночь UTC для статистики, 6 часов
UTC для сброса сессии, полночь UTC в бэкенде и местная полночь устройства на
телефоне. Две из них спорили: занятие в полпервого ночи телефон относил к
новому дню, а сервер ещё ко вчерашнему.
"""
from datetime import date, datetime

from common.study_day import (
    DEFAULT_DAY_START_HOUR,
    DEFAULT_TIMEZONE,
    day_in_days,
    day_started_utc,
    same_study_day,
    settings_of,
    study_day,
)

ROME = "Europe/Rome"


def test_defaults_keep_the_old_behaviour():
    """Пустые настройки — полночь UTC, как было до появления этих настроек."""
    assert settings_of(None) == (DEFAULT_TIMEZONE, DEFAULT_DAY_START_HOUR)
    assert settings_of({}) == (DEFAULT_TIMEZONE, DEFAULT_DAY_START_HOUR)
    moment = datetime(2026, 10, 9, 23, 30)
    assert study_day(moment) == date(2026, 10, 9)
    assert study_day(datetime(2026, 10, 10, 0, 1)) == date(2026, 10, 10)


def test_the_night_before_the_start_hour_belongs_to_the_day_before():
    """
    Полвторого ночи по Риму при начале суток в 4 — ещё вчерашнее занятие.

    Ради этого всё и затевалось: человек досиживает вчерашний день, а не
    начинает сегодняшний, и статистика обязана считать так же.
    """
    # 01:30 по Риму летом — это 23:30 UTC предыдущего дня.
    assert study_day(datetime(2026, 10, 9, 23, 30), ROME, 4) == date(2026, 10, 9)
    # 03:59 по Риму — всё ещё 9-е.
    assert study_day(datetime(2026, 10, 10, 1, 59), ROME, 4) == date(2026, 10, 9)
    # 04:01 — уже 10-е.
    assert study_day(datetime(2026, 10, 10, 2, 1), ROME, 4) == date(2026, 10, 10)


def test_the_boundary_survives_the_change_to_winter_time():
    """
    Пояс названием, а не числом, — чтобы перевод часов учитывался сам.

    В Риме 25.10.2026 переходят с +02:00 на +01:00. Начало суток в 4 утра
    должно остаться 4 утра по-местному, то есть сдвинуться в UTC.
    """
    summer = day_started_utc(date(2026, 10, 20), ROME, 4)
    winter = day_started_utc(date(2026, 10, 30), ROME, 4)
    assert summer.hour == 2, f"летом 04:00 Рима это 02:00 UTC, вышло {summer}"
    assert winter.hour == 3, f"зимой 04:00 Рима это 03:00 UTC, вышло {winter}"


def test_the_next_check_date_lands_on_the_boundary():
    """
    Дата следующей проверки кладётся ровно на границу суток человека.

    Тогда «пора ли повторять» остаётся сравнением с текущим моментом, и ни
    бэкенд, ни запрос в Mongo про пояса знать не обязаны.
    """
    now = datetime(2026, 10, 9, 12, 0)
    tomorrow = day_in_days(1, now, ROME, 4)
    assert tomorrow == datetime(2026, 10, 10, 2, 0)
    # Через день — ровно на сутки позже, пока перевода часов нет.
    assert day_in_days(2, now, ROME, 4) == datetime(2026, 10, 11, 2, 0)


def test_the_session_survives_the_night_but_not_the_morning():
    """Сброс сессии теперь по той же границе, что и статистика."""
    evening = datetime(2026, 10, 9, 21, 0)       # 23:00 по Риму
    deep_night = datetime(2026, 10, 10, 1, 0)    # 03:00 по Риму — те же сутки
    morning = datetime(2026, 10, 10, 6, 0)       # 08:00 по Риму — уже новые
    assert same_study_day(evening, deep_night, ROME, 4)
    assert not same_study_day(evening, morning, ROME, 4)


def test_an_unknown_zone_does_not_break_the_lesson():
    """Опечатка в настройке не должна ронять занятие — откатываемся на UTC."""
    assert study_day(datetime(2026, 10, 9, 23, 30), "Нет/Такого", 0) == date(2026, 10, 9)
    assert settings_of({"timezone": "", "day_start_hour": None}) == ("UTC", 0)


def test_the_start_hour_is_kept_within_the_day():
    """Час вне 0–23 — это опечатка; зажимаем, а не падаем."""
    assert settings_of({"day_start_hour": 99})[1] == 23
    assert settings_of({"day_start_hour": -5})[1] == 0


def test_the_catalogue_is_grouped_by_offset_not_a_flat_list():
    """
    Владелец: «491 пояс — многовато, и они повторяются по времени, различаются
    только городами». Поэтому справочник приходит группами: сначала смещение
    (их около сорока), внутри — города.
    """
    from common.study_day import timezone_catalog

    groups = timezone_catalog()
    assert 20 <= len(groups) <= 50, f"групп смещений {len(groups)} — похоже на плоский список"
    assert sum(len(g["zones"]) for g in groups) > 300, "поясов подозрительно мало"

    minutes = [g["minutes"] for g in groups]
    assert minutes == sorted(minutes), "смещения не по порядку — искать своё неудобно"
    assert len(set(minutes)) == len(minutes), "одно смещение встречается дважды"

    by_label = {g["label"]: g for g in groups}
    assert "UTC+00:00" in by_label and "UTC-11:00" in by_label, sorted(by_label)

    names = {z["name"] for g in groups for z in g["zones"]}
    assert "Europe/Rome" in names and "UTC" in names
    assert not any("/" not in n and n != "UTC" for n in names), "попали сокращения вроде EST"
    assert not any(n.startswith(("Etc/", "US/", "SystemV/")) for n in names), "попали псевдонимы"


def test_a_zone_is_shown_by_its_city():
    """В списке ищут город, а не материк, — поэтому город первым."""
    from common.study_day import timezone_catalog

    rome = next(z for g in timezone_catalog() for z in g["zones"] if z["name"] == "Europe/Rome")
    assert rome["label"] == "Rome · Europe"
    # Подчёркивания в названиях IANA человеку показывать незачем.
    assert not any("_" in z["label"] for g in timezone_catalog() for z in g["zones"])
