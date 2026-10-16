"""
Горизонтальная ось графиков — пропорциональна датам.

Жалоба владельца: «по горизонтальной оси точки идут на одинаковом расстоянии
даже если даты между ними неравномерны».

Так и было: в ось передавались СТРОКИ дат, и matplotlib ставил их как названия
категорий — промежутки одинаковые. На графике «не знал на первом проходе», где
записи шли с пропусками, провал в месяц выглядел тем же шагом, что соседние
дни: по такому графику динамику не прочесть, а именно за ней на него и смотрят.

Проверяется положение точек в экранных координатах — то есть ровно то, что
видит глаз, а не то, что я передал в библиотеку.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from app.chart_generator import ProgressChartGenerator  # noqa: E402

FIELD = "words_unknown_first_finish"


def _stats(*dates_and_values):
    return [{"date": f"{d}T00:00:00", FIELD: v} for d, v in dates_and_values]


def _screen_x(stats):
    """Где точки окажутся на картинке по горизонтали."""
    fig = ProgressChartGenerator.counts_figure(stats, FIELD, "т", "max")
    ax = fig.axes[0]
    line = ax.lines[0]
    # orig=False — уже переведённые в координаты оси значения; именно по ним
    # библиотека и расставляет точки.
    xs, ys = line.get_xdata(orig=False), line.get_ydata(orig=False)
    return [ax.transData.transform((x, y))[0] for x, y in zip(xs, ys)]


def test_a_ten_day_gap_is_ten_times_a_one_day_gap():
    """Три точки: 1-е, 2-е и 12-е. Второй промежуток в десять раз длиннее."""
    xs = _screen_x(_stats(("2026-10-01", 5), ("2026-10-02", 6), ("2026-10-12", 7)))
    first, second = xs[1] - xs[0], xs[2] - xs[1]
    assert first > 0 and second > 0
    assert second / first == pytest.approx(10, rel=0.02), (
        f"промежутки на экране {first:.1f} и {second:.1f} — "
        "ось не пропорциональна датам")


def test_equal_gaps_stay_equal():
    """Опора: на ровном ряду ничего не поехало."""
    xs = _screen_x(_stats(("2026-10-01", 1), ("2026-10-02", 2), ("2026-10-03", 3)))
    assert xs[1] - xs[0] == pytest.approx(xs[2] - xs[1], rel=0.01)


def test_the_owner_series_shows_the_month_long_hole():
    """
    Настоящий ряд владельца: 17–20 сентября, потом пропуск до 16 октября.
    Пропуск обязан занять почти всю ширину — в нём 26 дней из 29.
    """
    xs = _screen_x(_stats(("2026-09-17", 3), ("2026-09-18", 5), ("2026-09-19", 3),
                          ("2026-09-20", 6), ("2026-10-16", 16)))
    width = xs[-1] - xs[0]
    hole = xs[4] - xs[3]
    assert hole / width == pytest.approx(26 / 29, rel=0.02), (
        f"пропуск занял {hole / width:.0%} ширины вместо 90%")


def test_dates_are_dates_and_not_labels():
    """
    Корень той ошибки: строки вместо дат. Если он вернётся, расстояния снова
    станут равными — эта проверка ловит причину, а не только следствие.
    """
    fig = ProgressChartGenerator.counts_figure(
        _stats(("2026-10-01", 1), ("2026-10-12", 2)), FIELD, "т", "max")
    line = fig.axes[0].lines[0]
    assert not isinstance(line.get_xdata()[0], str), "в ось снова передали строку"
    # Разница в координатах оси — одиннадцать суток, а не «одна категория».
    numeric = line.get_xdata(orig=False)
    assert float(numeric[1]) - float(numeric[0]) == pytest.approx(11.0, abs=1e-6)


def test_one_point_does_not_collapse_the_axis():
    """Одна запись за месяц — ось не должна вырождаться в нулевую ширину."""
    fig = ProgressChartGenerator.counts_figure(
        _stats(("2026-10-16", 16)), FIELD, "т", "max")
    left, right = fig.axes[0].get_xlim()
    assert right > left


def test_the_labels_stay_readable_dates():
    """Подписи остаются датами, а не числами matplotlib."""
    fig = ProgressChartGenerator.counts_figure(
        _stats(("2026-09-17", 3), ("2026-10-16", 16)), FIELD, "т", "max")
    fig.canvas.draw()
    labels = [t.get_text() for t in fig.axes[0].get_xticklabels() if t.get_text()]
    assert labels, "ось осталась без подписей"
    assert all(len(l) == 10 and l[4] == "-" for l in labels), labels


def test_the_picture_still_renders():
    """Опора: картинка по-прежнему собирается и остаётся PNG."""
    data = ProgressChartGenerator.create_counts_plot(
        _stats(("2026-09-17", 3), ("2026-10-16", 16)), FIELD, "т", "max").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
