"""
Генератор реальных графиков для статистики изучения слов.
Создает PNG-изображения гистограмм и диаграмм.

All chart functions use the object-oriented matplotlib Figure API (no pyplot global
state) so they are safe to call from multiple threads concurrently via run_in_executor.
"""

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams['axes.unicode_minus'] = False

from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from collections import Counter
from io import BytesIO
from typing import List, Dict, Tuple
import numpy as np
import datetime
from app.logger import setup_logger


logger = setup_logger(__name__)


def _save_fig(fig: Figure) -> BytesIO:
    """Save figure to PNG BytesIO without touching pyplot global state."""
    buffer = BytesIO()
    fig.savefig(buffer, format='PNG', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    buffer.seek(0)
    return buffer


class ProgressChartGenerator:
    """Генератор графиков прогресса изучения."""

    @staticmethod
    def create_word_distribution_chart(progress: Dict) -> BytesIO:
        words_known = progress.get('words_known', 0)
        words_unknown = progress.get('words_studied', 0) - words_known - progress.get('words_skipped', 0)
        words_skipped = progress.get('words_skipped', 0)

        sizes = [words_known, words_unknown, words_skipped]
        labels = [f'Выучено\n{words_known}', f'Неизвестно\n{words_unknown}', f'Пропущено\n{words_skipped}']
        colors = ['#4CAF50', '#FF9800', '#9E9E9E']
        explode = (0.05, 0, 0)

        fig = Figure(figsize=(10, 8))
        ax = fig.subplots()

        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=colors, explode=explode,
            autopct='%1.1f%%', startangle=90, textprops={'fontsize': 12}
        )
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(11)

        total_studied = sum(sizes)
        ax.set_title(f'Распределение изученных слов\nВсего изучено: {total_studied}',
                     fontsize=16, fontweight='bold', pad=20)
        ax.axis('equal')
        fig.tight_layout()
        return _save_fig(fig)

    @staticmethod
    def create_words_for_today_histogram(
        word_numbers_for_today: List[int],
        words_studied: int,
        x_axis_limits: str = "one_max"
    ) -> BytesIO:
        fig = Figure(figsize=(6, 5))
        ax = fig.subplots()

        max_word = max(
            max(word_numbers_for_today) if word_numbers_for_today else 0,
            words_studied
        )
        bin_count = min(20, max_word)
        bins = np.linspace(0, max_word, bin_count + 1)

        if word_numbers_for_today:
            ax.hist(word_numbers_for_today, bins=bins, color='#2196F3', alpha=0.7, edgecolor='black')
            ax.set_title(f'Слова для повторения сегодня \n ({len(word_numbers_for_today)} слов)',
                         fontsize=20, fontweight='bold')
        else:
            ax.text(0.5, 0.5, 'Нет слов для повторения сегодня!',
                    transform=ax.transAxes, ha='center', va='center',
                    fontsize=14, fontweight='bold', color='#4CAF50')
            ax.set_title('Слова для повторения сегодня', fontsize=14, fontweight='bold')

        if x_axis_limits == "one_max":
            ax.set_xlim(1, max_word)
        ax.set_xlabel('Номер слова')
        ax.set_ylabel('Количество слов')
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return _save_fig(fig)

    @staticmethod
    def create_unknown_words_histogram(
        word_numbers_unknown: List[int],
        words_studied: int,
        x_axis_limits: str = "one_max"
    ) -> BytesIO:
        fig = Figure(figsize=(6, 5))
        ax = fig.subplots()

        max_word = max(
            max(word_numbers_unknown) if word_numbers_unknown else 0,
            words_studied
        )
        bin_count = min(20, max_word)
        bins = np.linspace(0, max_word, bin_count + 1)

        if word_numbers_unknown:
            ax.hist(word_numbers_unknown, bins=bins, color='#FF5722', alpha=0.7, edgecolor='black')
            ax.set_title(f'Неизвестные слова \n ({len(word_numbers_unknown)} слов)',
                         fontsize=20, fontweight='bold')
        else:
            ax.text(0.5, 0.5, 'Все изученные слова выучены!',
                    transform=ax.transAxes, ha='center', va='center',
                    fontsize=14, fontweight='bold', color='#4CAF50')
            ax.set_title('Неизвестные слова', fontsize=14, fontweight='bold')

        if x_axis_limits == "one_max":
            ax.set_xlim(1, max_word)
        ax.set_xlabel('Номер слова')
        ax.set_ylabel('Количество слов')
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return _save_fig(fig)

    @staticmethod
    def create_check_interval_histogram(
        word_check_interval: List[Tuple[int, int]],
        words_studied: int,
        x_axis_limits: str = "one_max"
    ) -> BytesIO:
        fig = Figure(figsize=(6, 5))
        ax = fig.subplots()

        max_word = max(
            max([x[0] for x in word_check_interval]) if word_check_interval else 0,
            words_studied
        )

        BIN_LEN = 20
        bins = []
        for bin_start in range(0, max_word, BIN_LEN):
            bin_end = bin_start + BIN_LEN
            bin_values = [x[1] for x in word_check_interval if bin_start <= x[0] < bin_end]
            bin_values_counts = Counter(bin_values)
            for value, count in bin_values_counts.items():
                bins.append({
                    "x": bin_start, "y": value,
                    "alpha": count / BIN_LEN, "size": count * 3,
                })

        if word_check_interval:
            x = [b["x"] for b in bins]
            y = [b["y"] for b in bins]
            alpha = [b["alpha"] for b in bins]
            size = [b["size"] for b in bins]
            ax.scatter(x, y, color='blue', alpha=alpha, edgecolor='blue', marker='o', s=size)
            ax.set_title(f'Интервалы повторения слов \n ({len(word_check_interval)} интервалов)',
                         fontsize=20, fontweight='bold')
        else:
            ax.text(0.5, 0.5, 'Нет интервалов повторения слов!',
                    transform=ax.transAxes, ha='center', va='center',
                    fontsize=14, fontweight='bold', color='#4CAF50')
            ax.set_title('Интервалы повторения слов', fontsize=14, fontweight='bold')

        if x_axis_limits == "one_max":
            ax.set_xlim(1, max_word)
        ax.set_xlabel('Номер слова')
        ax.set_ylabel('Интервал повторения')
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return _save_fig(fig)

    @staticmethod
    def create_counts_plot(
        daily_stats: List[Dict],
        field_name: str,
        title: str,
        title_value: str,
        y_axis_limits: str = "min_max"
    ) -> BytesIO:
        dates = [datetime.datetime.fromisoformat(s["date"]).date().isoformat()
                 for s in daily_stats if s[field_name] is not None]
        counts = [s[field_name] for s in daily_stats if s[field_name] is not None]

        fig = Figure(figsize=(6, 5))
        ax = fig.subplots()

        ax.plot(dates, counts, color='#FF5722', alpha=0.7, linewidth=2, marker='o', markersize=5)
        if title_value == "last":
            ax.set_title(f'{title}\n{len(counts)} записей \n last={counts[-1] if counts else "None"}',
                         fontsize=20, fontweight='bold')
        elif title_value == "max":
            ax.set_title(f'{title}\n{len(counts)} записей \n max={max(counts) if counts else "None"}',
                         fontsize=20, fontweight='bold')

        ax.set_xlabel('Дата')
        step = max(1, len(dates) // 10)
        tick_indices = range(0, len(dates), step)
        ax.set_xticks(tick_indices)
        ax.set_xticklabels([dates[i] for i in tick_indices], rotation=45, ha='right')

        ax.set_ylabel('Количество слов')
        ax.yaxis.set_major_locator(MaxNLocator(integer=True, prune='both'))
        if y_axis_limits == "min_max":
            y_min, y_max = ax.get_ylim()
            ax.set_ylim(int(y_min), int(y_max) + 1)
        elif y_axis_limits == "zero_max" and counts:
            ax.set_ylim(0, int(max(counts)) + 1)

        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return _save_fig(fig)
