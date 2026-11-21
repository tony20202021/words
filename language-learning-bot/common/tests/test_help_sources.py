"""Источники данных в справке.

Данные Викисловаря, wordfreq и FrequencyWords идут по лицензии CC BY-SA 4.0:
показывая их, нужно указать источник и лицензию. Отдельного «о программе» нет
ни в приложении, ни в боте, ни в вебе — есть «Помощь», общая для всех трёх.
Туда и ставим короткий перечень и ссылку на полный — DATA_SOURCES.md в
корне репозитория (владелец, 20.11.2026).
"""
from pathlib import Path

from common.help_text import DATA_SOURCES_URL, HELP_TEXT

REPO = Path(__file__).resolve().parents[3]
SOURCES = ("Викисловар", "wordfreq", "FrequencyWords", "ipa-dict", "piper-he-noa")


def test_help_names_every_source_and_its_license():
    for name in SOURCES:
        assert name in HELP_TEXT, f"в справке не назван источник {name}"
    assert "CC BY-SA 4.0" in HELP_TEXT
    assert "CC BY 4.0" in HELP_TEXT          # голос noa (Piper)
    assert "MIT" in HELP_TEXT


def test_help_links_to_the_sources_file_and_it_names_the_same_sources():
    assert DATA_SOURCES_URL in HELP_TEXT
    assert DATA_SOURCES_URL.endswith("/DATA_SOURCES.md")
    full = (REPO / "DATA_SOURCES.md").read_text(encoding="utf-8")
    for name in SOURCES:
        assert name in full, f"в DATA_SOURCES.md нет источника {name}"


def test_help_text_is_safe_for_telegram_html():
    """Бот шлёт справку с parse_mode=HTML: <, > и & там — разметка."""
    for ch in "<>&":
        assert ch not in HELP_TEXT, f"символ {ch!r} сломает справку в боте"
