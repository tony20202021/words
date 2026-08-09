"""Tests for shared catalog modules."""

from common.hint_catalog import HINT_ORDER, hint_types_ordered, setting_key_for
from common.chart_manifest import CHART_SECTIONS, CHART_CAPTIONS, TODAY_CHART_NAMES, MONTHLY_CHART_NAMES


def test_hint_order_matches_catalog():
    types = hint_types_ordered()
    assert list(types.keys()) == HINT_ORDER


def test_setting_key_for_meaning():
    assert setting_key_for("meaning") == "show_hint_meaning"


def test_chart_sections_have_three_groups():
    assert len(CHART_SECTIONS) == 3
    types = [s["type"] for s in CHART_SECTIONS]
    assert types == ["today", "monthly_recent", "monthly_all"]


def test_today_charts_have_captions():
    for name in TODAY_CHART_NAMES:
        assert name in CHART_CAPTIONS


def test_monthly_charts_have_captions():
    """
    Проверка была только для дневных графиков, а месячных семь из десяти —
    то есть большая часть каталога не проверялась вовсе, и график без подписи
    попал бы на экран незамеченным.
    """
    for name in MONTHLY_CHART_NAMES:
        assert name in CHART_CAPTIONS, f"у графика {name} нет подписи"


def test_every_named_chart_has_a_caption():
    """Ловит и график, добавленный в новый, ещё не перечисленный здесь список."""
    named = set(TODAY_CHART_NAMES) | set(MONTHLY_CHART_NAMES)
    missing = named - set(CHART_CAPTIONS)
    assert not missing, missing
