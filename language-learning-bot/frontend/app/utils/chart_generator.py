"""
Генератор реальных графиков для статистики изучения слов.
Создает PNG-изображения гистограмм и диаграмм.
"""

import matplotlib.pyplot as plt
from collections import Counter
from io import BytesIO
from typing import List, Dict, Tuple
import numpy as np
import datetime
from app.utils.logger import setup_logger


logger = setup_logger(__name__)

# Настройка matplotlib для русского языка
# plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False


class ProgressChartGenerator:
    """Генератор графиков прогресса изучения."""
    
    @staticmethod
    def create_word_distribution_chart(progress: Dict) -> BytesIO:
        """
        Создает круговую диаграмму распределения слов.
        
        Args:
            progress: Словарь с данными прогресса
            
        Returns:
            BytesIO с PNG изображением
        """
        words_known = progress.get('words_known', 0)
        words_unknown = progress.get('words_studied', 0) - words_known - progress.get('words_skipped', 0)
        words_skipped = progress.get('words_skipped', 0)
        
        # Данные для диаграммы
        sizes = [words_known, words_unknown, words_skipped]
        labels = [f'Выучено\n{words_known}', f'Неизвестно\n{words_unknown}', f'Пропущено\n{words_skipped}']
        colors = ['#4CAF50', '#FF9800', '#9E9E9E']  # Зеленый, Оранжевый, Серый
        explode = (0.05, 0, 0)  # Выделяем "выученные" слова
        
        # Создаем фигуру
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Круговая диаграмма
        wedges, texts, autotexts = ax.pie(
            sizes, 
            labels=labels, 
            colors=colors, 
            explode=explode,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 12}
        )
        
        # Настройка текста
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(11)
        
        # Заголовок
        total_studied = sum(sizes)
        ax.set_title(f'Распределение изученных слов\nВсего изучено: {total_studied}', 
                    fontsize=16, fontweight='bold', pad=20)
        
        # Равные пропорции
        ax.axis('equal')
        
        # Сохраняем в BytesIO
        buffer = BytesIO()
        plt.savefig(buffer, format='PNG', dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        plt.close(fig)
        
        return buffer

    @staticmethod 
    def create_words_for_today_histogram(
        word_numbers_for_today: List[int], 
        words_studied: int,
        x_axis_limits: str = "one_max"
    ) -> BytesIO:
        """
        Создает гистограмму слов для повторения сегодня
        
        Args:
            word_numbers_for_today: Номера слов для повторения
            words_studied: Общее количество слов в языке
            
        Returns:
            BytesIO с PNG изображением
        """
        fig, (ax1) = plt.subplots(1, 1, figsize=(6, 5))
        
        # Определяем диапазон для гистограммы
        max_word = max(
            max(word_numbers_for_today) if word_numbers_for_today else 0,
            words_studied
        )
        
        # bins для гистограммы
        bin_count = min(20, max_word)
        bins = np.linspace(0, max_word, bin_count + 1)
        
        # 1. Гистограмма слов для повторения сегодня
        if word_numbers_for_today:
            ax1.hist(word_numbers_for_today, bins=bins, color='#2196F3', alpha=0.7, edgecolor='black')
            ax1.set_title(f'Слова для повторения сегодня \n ({len(word_numbers_for_today)} слов)', 
                         fontsize=20, fontweight='bold')
        else:
            ax1.text(0.5, 0.5, 'Нет слов для повторения сегодня!', 
                    transform=ax1.transAxes, ha='center', va='center',
                    fontsize=14, fontweight='bold', color='#4CAF50')
            ax1.set_title('Слова для повторения сегодня', fontsize=14, fontweight='bold')
        
        if x_axis_limits == "one_max":
            ax1.set_xlim(1, max_word)
            
        ax1.set_xlabel('Номер слова')
        ax1.set_ylabel('Количество слов')
        ax1.yaxis.set_major_locator(plt.MaxNLocator(integer=True))  # Только целые значения
        ax1.grid(True, alpha=0.3)
        
        # Компактное расположение
        plt.tight_layout()
        
        # Сохраняем в BytesIO
        buffer = BytesIO()
        plt.savefig(buffer, format='PNG', dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        plt.close(fig)
        
        return buffer

    @staticmethod 
    def create_unknown_words_histogram(
        word_numbers_unknown: List[int],
        words_studied: int,
        x_axis_limits: str = "one_max"
    ) -> BytesIO:
        """
        Создает гистограмму слов для повторения сегодня и неизвестных слов.
        
        Args:
            word_numbers_unknown: Номера неизвестных слов
            words_studied: Общее количество слов в языке
            
        Returns:
            BytesIO с PNG изображением
        """
        fig, (ax2) = plt.subplots(1, 1, figsize=(6, 5))
        
        # Определяем диапазон для гистограммы
        max_word = max(
            max(word_numbers_unknown) if word_numbers_unknown else 0,
            words_studied
        )
        
        # bins для гистограммы
        bin_count = min(20, max_word)
        bins = np.linspace(0, max_word, bin_count + 1)
        
        # Гистограмма неизвестных слов
        if word_numbers_unknown:
            ax2.hist(word_numbers_unknown, bins=bins, color='#FF5722', alpha=0.7, edgecolor='black')
            ax2.set_title(f'Неизвестные слова \n ({len(word_numbers_unknown)} слов)', 
                         fontsize=20, fontweight='bold')
        else:
            ax2.text(0.5, 0.5, 'Все изученные слова выучены!', 
                    transform=ax2.transAxes, ha='center', va='center',
                    fontsize=14, fontweight='bold', color='#4CAF50')
            ax2.set_title('Неизвестные слова', fontsize=14, fontweight='bold')
        
        if x_axis_limits == "one_max":
            ax2.set_xlim(1, max_word)
            
        ax2.set_xlabel('Номер слова')
        ax2.set_ylabel('Количество слов')
        ax2.yaxis.set_major_locator(plt.MaxNLocator(integer=True))  # Только целые значения
        ax2.grid(True, alpha=0.3)

        # Компактное расположение
        plt.tight_layout()
        
        # Сохраняем в BytesIO
        buffer = BytesIO()
        plt.savefig(buffer, format='PNG', dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        plt.close(fig)
        
        return buffer

    @staticmethod 
    def create_check_interval_histogram(
        word_check_interval: List[Tuple[int, int]],
        words_studied: int,
        x_axis_limits: str = "one_max"
    ) -> BytesIO:
        """
        Создает точечную диаграмму интервалов повторения слов.
        
        Args:
            word_check_interval: интервалы повторения слов
            words_studied: Общее количество слов изученных пользователем
            
        Returns:
            BytesIO с PNG изображением
        """

        fig, (ax3) = plt.subplots(1, 1, figsize=(6, 5))
        
        max_word = max(
            max([x[0] for x in word_check_interval]) if word_check_interval else 0,
            words_studied
        )

        # Точечная диаграмма интервалов повторения слов
        BIN_LEN = 20
        bins = []
        for bin_start in range(0, max_word, BIN_LEN):
            bin_end = bin_start + BIN_LEN
            bin_values = [x[1] for x in word_check_interval if x[0] >= bin_start and x[0] < bin_end]
            bin_values_counts = Counter(bin_values)
            for value, count in bin_values_counts.items():
                bin = {
                    "x": bin_start,
                    "y": value,
                    "alpha": count / BIN_LEN,
                    "size": count * 3,
                    "color": 'blue',
                    "marker": 'o',
                }
                bins.append(bin)

        x = []
        y = []
        alpha = []
        size = []
        for bin in bins:
            x.append(bin["x"])
            y.append(bin["y"])
            alpha.append(bin["alpha"])
            size.append(bin["size"])

        if word_check_interval:
            ax3.scatter(x, y, color='blue', alpha=alpha, edgecolor='blue', marker='o', s=size)
            ax3.set_title(f'Интервалы повторения слов \n ({len(word_check_interval)} интервалов)', 
                         fontsize=20, fontweight='bold')
        else:
            ax3.text(0.5, 0.5, 'Нет интервалов повторения слов!', 
                    transform=ax3.transAxes, ha='center', va='center',
                    fontsize=14, fontweight='bold', color='#4CAF50')
            ax3.set_title('Интервалы повторения слов', fontsize=14, fontweight='bold')

        if x_axis_limits == "one_max":
            ax3.set_xlim(1, max_word)
            
        ax3.set_xlabel('Номер слова')
        ax3.set_ylabel('Интервал повторения')
        ax3.yaxis.set_major_locator(plt.MaxNLocator(integer=True))  # Только целые значения
        ax3.grid(True, alpha=0.3)
        
        # Компактное расположение
        plt.tight_layout()
        
        # Сохраняем в BytesIO
        buffer = BytesIO()
        plt.savefig(buffer, format='PNG', dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        plt.close(fig)

        return buffer

    @staticmethod
    def create_counts_plot(
        daily_stats: List[Dict], 
        field_name: str, 
        title: str, 
        title_value: str,
        y_axis_limits: str = "min_max"
    ) -> BytesIO:
        """
        Создает график по датам
        """
        dates = [datetime.datetime.fromisoformat(s["date"]).date().isoformat() for s in daily_stats if s[field_name] is not None]
        counts = [s[field_name] for s in daily_stats if s[field_name] is not None]
        
        fig, (ax2) = plt.subplots(1, 1, figsize=(6, 5))
        
        ax2.plot(dates, counts, color='#FF5722', alpha=0.7, linewidth=2, marker='o', markersize=5)
        if title_value == "last":
            ax2.set_title(f'{title}\n{len(counts)} записей \n last={counts[-1] if len(counts) > 0 else "None"}', fontsize=20, fontweight='bold')
        elif title_value == "max":
            ax2.set_title(f'{title}\n{len(counts)} записей \n max={max(counts) if len(counts) > 0 else "None"}', fontsize=20, fontweight='bold')
        
        ax2.set_xlabel('Дата')
        step = max(1, len(dates) // 10)
        tick_indices = range(0, len(dates), step)
        ax2.set_xticks(tick_indices)  # Сначала позиции
        ax2.set_xticklabels([dates[i] for i in tick_indices], rotation=45, ha='right')  # Потом метки для этих позиций

        # logger.info(f"dates: {dates}")
        # logger.info(f"counts: {counts}")
        
        ax2.set_ylabel('Количество слов')
        ax2.yaxis.set_major_locator(plt.MaxNLocator(integer=True, prune='both'))        
        if y_axis_limits == "min_max":
            y_min, y_max = ax2.get_ylim()
            ax2.set_ylim(int(y_min), int(y_max) + 1)
        elif y_axis_limits == "zero_max":
            ax2.set_ylim(0, int(max(counts)) + 1)
            
        ax2.grid(True, alpha=0.3)

        # Компактное расположение
        plt.tight_layout()
        
        # Сохраняем в BytesIO
        buffer = BytesIO()
        plt.savefig(buffer, format='PNG', dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        plt.close(fig)
        
        return buffer

