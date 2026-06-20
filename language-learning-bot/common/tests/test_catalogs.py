"""Tests for shared catalog modules."""

from common.hint_catalog import HINT_ORDER, hint_types_ordered, setting_key_for
from common.chart_manifest import CHART_SECTIONS, CHART_CAPTIONS, TODAY_CHART_NAMES


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
