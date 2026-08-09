"""
Тесты оснастки работы со словарём иврита.

Зачем
-----
Тринадцать скриптов, ноль тестов, и за одну неделю в них нашлись три тихих
дефекта — каждый портил данные, ничего не сообщая:

  build_hebrew_extras.py  затирал поле tones у всех записей, оставляя только
                          те 18, что строил сам;
  parse_sources.py        разбирал страницу русского Викисловаря целиком, и в
                          свидетельства об иврите подмешивались идиш и крымчакский;
  fetch_sources.py        кэшировал сорвавшийся запрос как «статьи нет», навсегда.

Все три нашёл человек вопросом «а точно всё в порядке», ни одного — проверка.
Здесь закреплены инварианты, нарушение которых и означало каждый из них.

Проверяется логика, а не сеть: ни один тест ничего не выкачивает.
"""

import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import apply_review          # noqa: E402
import build_hebrew_extras   # noqa: E402
import fetch_sources         # noqa: E402
import merge_reviews         # noqa: E402
import parse_sources         # noqa: E402


# ── огласовка не меняет буквенный состав ─────────────────────────────────────

class TestNiqqudInvariant:
    """
    Главный инвариант всей работы: огласовка — это ЗНАКИ над согласными, и снятие
    их обязано вернуть исходное слово. Именно эта проверка поймала предложение
    קלטת -> קַסֶּטֶת, где согласная ל заменена на ס: вместо огласовки подставлено
    другое слово. В списке из четырёхсот строк такое не видно.
    """

    def test_plain_vocalization_is_accepted(self):
        row = {"hebrew": "ספר"}
        ok, _ = apply_review.check(row, "niqqud", "סֵפֶר")
        assert ok

    def test_swapped_consonant_is_refused(self):
        row = {"hebrew": "קלטת"}
        ok, why = apply_review.check(row, "niqqud", "קַסֶּטֶת")
        assert not ok
        assert "согласные разошлись" in why

    def test_matres_lectionis_difference_is_allowed(self):
        """Полное и неполное написание отличаются вавом и йодом — это норма."""
        row = {"hebrew": "שלום"}
        ok, note = apply_review.check(row, "niqqud", "שָׁלֹם")
        assert ok, note

    def test_unvocalized_value_is_refused(self):
        ok, why = apply_review.check({"hebrew": "ספר"}, "niqqud", "ספר")
        assert not ok
        assert "огласовки нет" in why

    @pytest.mark.parametrize("field,value,fragment", [
        ("pos", "предлог", "вне набора"),
        ("ipa", "סֵפֶר", "ивритский текст"),
        ("russian", "סֵפֶר", "ивритский текст"),
        ("lemma", "סֵפֶר", "без огласовки"),
        ("lemma", "kniga", "без ивритских букв"),
        ("tones", "<b>x</b>: один вариант", "ивритского текста"),
    ])
    def test_field_specific_checks(self, field, value, fragment):
        ok, why = apply_review.check({"hebrew": "ספר"}, field, value)
        assert not ok
        assert fragment in why, why


# ── русское «й» — не огласовка ───────────────────────────────────────────────

class TestHasNiqqud:
    """
    NFD раскладывает русское «й» на «и» + бреве, а бреве — комбинирующий знак
    той же категории, что и огласовка. Из-за этого слова «свойства» и
    «Русско-ивритский» из библиографии Викисловаря проходили как огласованный
    иврит и попадали в свидетельства.
    """

    def test_vocalized_hebrew(self):
        assert parse_sources.has_niqqud("סֵפֶר")

    def test_bare_hebrew(self):
        assert not parse_sources.has_niqqud("ספר")

    @pytest.mark.parametrize("word", ["свойства", "Русско-ивритский", "мой"])
    def test_russian_with_short_i_is_not_niqqud(self, word):
        assert not parse_sources.has_niqqud(word)


# ── ivrit-раздел, а не вся страница ──────────────────────────────────────────

def test_only_the_hebrew_section_of_ru_wiktionary_is_read():
    """
    Одно написание описывается на странице и как иврит, и как идиш, и как
    крымчакский. Разбирая страницу целиком, мы показывали проверяющему
    крымчакские значения как русские значения ивритского слова.
    """
    page = (
        "= {{-he-}} =\n== {{з|(существительное)}} ==\n"
        "=== Произношение ===\n{{transcription|jeʃ}}\n"
        "=== Семантические свойства ===\n\n==== Значение ====\n# [[есть, имеется]]\n"
        "= {{-kdr-}} =\n== {{з|(существительное)}} ==\n"
        "=== Семантические свойства ===\n\n==== Значение ====\n# [[возраст]]\n"
    )
    senses = [s for e in parse_sources.parse_ru(page, "форма") for s in e["senses"]]
    assert "есть, имеется" in senses
    assert "возраст" not in senses, "крымчакское значение попало в иврит"


def test_page_without_a_hebrew_section_yields_nothing():
    assert parse_sources.parse_ru("= {{-yi-}} =\n==== Значение ====\n# [[идиш]]\n", "форма") == []


# ── сравнение произношения ───────────────────────────────────────────────────

class TestIpaComparison:
    """
    Расходятся не звуки, а соглашения записи: гортанную смычку пишут как ʔ, как
    (ʔ) или опускают, ударение — и ˈ, и апострофом. Сравнение строк давало 8
    ложных срабатываний на 30 словах.
    """

    @pytest.mark.parametrize("a,b", [
        ("ʔaˈni", "(ʔ)aˈni"),
        ("ʔaˈni", "aˈni"),
        ("beˈseder", "be'se.der"),
        ("ʔet", "/ʔet/"),
    ])
    def test_same_pronunciation_written_differently(self, a, b):
        assert parse_sources.ipa_variants(a) & parse_sources.ipa_variants(b), (a, b)

    def test_genuinely_different_pronunciations_do_not_match(self):
        assert not (parse_sources.ipa_variants("ʔim") & parse_sources.ipa_variants("ʔam"))

    def test_audio_file_name_is_not_a_transcription(self):
        assert parse_sources.is_audio("LL-Q9288 (heb)-Buffer-אני.wav")
        assert parse_sources.ipa_variants("LL-Q9288 (heb)-Buffer-אני.wav") == set()


# ── самые частотные переводы тоже надо сверять ───────────────────────────────

class TestOverlap:
    """
    Фильтр «слова длиннее двух букв» отсекал предлоги, но у самых частотных слов
    ВЕСЬ перевод такой: «я», «он», «но», «да». Возврат True при пустом множестве
    означал, что перевод 52 самых частотных слов не сверялся никогда.
    """

    def test_short_translations_are_compared(self):
        assert not parse_sources.overlap("я", "мы")
        assert not parse_sources.overlap("он", "нет")

    def test_identical_short_translations_agree(self):
        assert parse_sources.overlap("я", "я")

    def test_long_translations_still_work_by_shared_word(self):
        assert parse_sources.overlap("книга, том", "книга")
        assert not parse_sources.overlap("книга", "лошадь")


# ── число однокоренных считается до обрезки ──────────────────────────────────

def test_reference_count_is_taken_before_truncation():
    """
    Заголовок брал длину УЖЕ обрезанного списка, и 1433 карточки утверждали
    «слов с этой основой: 12» при реальных сорока девяти.
    """
    row = {"rank": 1, "lemma": "היה", "hebrew": "היה"}
    family = [{"rank": i, "hebrew": f"w{i}", "niqqud": f"w{i}", "ipa": "x", "russian": "y"}
              for i in range(1, 51)]
    text = build_hebrew_extras.build_references(row, family)
    head = text.split("\n")[0]
    assert "слов с этой основой: 49" in head, head
    assert "показаны первые" in head, "обрезка должна быть названа явно"
    assert len(text.split("\n")) - 1 == build_hebrew_extras.MAX_REFS


def test_reference_block_is_empty_for_a_lonely_word():
    assert build_hebrew_extras.build_references({"rank": 1, "lemma": "x", "hebrew": "x"},
                                                [{"rank": 1}]) == ""


# ── сбой запроса не то же, что «статьи нет» ──────────────────────────────────

class TestCacheDoesNotRememberFailures:
    """
    Оба исхода выглядели как None, и сорвавшийся запрос оседал на диске как
    «статьи нет» — навсегда, повторным прогоном не лечился. Так в кэше осело 65
    отрицательных ответов Викиданных, включая מים «вода».
    """

    @pytest.fixture(autouse=True)
    def cache_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fetch_sources, "CACHE", str(tmp_path))

    def test_missing_page_is_cached(self):
        calls = []

        def produce():
            calls.append(1)
            return None          # страницы нет — это ответ

        assert fetch_sources.cached("k1", produce) is None
        assert fetch_sources.cached("k1", produce) is None
        assert len(calls) == 1, "отрицательный ответ должен кэшироваться"

    def test_failed_request_is_not_cached(self):
        calls = []

        def produce():
            calls.append(1)
            raise fetch_sources.FetchFailed("исчерпаны попытки")

        assert fetch_sources.cached("k2", produce) is None
        assert fetch_sources.cached("k2", produce) is None
        assert len(calls) == 2, "сбой запомнился как ответ — это и был баг"


# ── слияние правок идемпотентно ──────────────────────────────────────────────

def test_skeleton_ignores_matres_lectionis():
    assert merge_reviews.skeleton("שָׁלוֹם") == merge_reviews.skeleton("שָׁלֹם")
    assert merge_reviews.skeleton("ספר") != merge_reviews.skeleton("סכר")


def test_niqqud_validation_matches_apply_review():
    """
    Один и тот же инвариант проверяют два скрипта. Разойдясь, они пропустили бы
    правку по очереди — поэтому сверяем их между собой на одних данных.
    """
    cases = [("ספר", "סֵפֶר"), ("קלטת", "קַסֶּטֶת"), ("שלום", "שָׁלֹם")]
    for hebrew, niqqud in cases:
        merged, _ = merge_reviews.niqqud_matches(hebrew, niqqud)
        applied, _ = apply_review.check({"hebrew": hebrew}, "niqqud", niqqud)
        assert merged == applied, (hebrew, niqqud, merged, applied)
