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


# ── порядок внутри тегов ──────────────────────────────────────────────────────

def test_every_tag_declares_how_it_is_sorted():
    """
    Порядок показа обязан быть объявлен, а не подразумеваться. Ручной ставится
    только там, где он очевиден читателю — числа по значению, лица по парадигме;
    остальным по рангу, потому что выдуманная последовательность хуже
    отсутствия: в ней ищут смысл, которого нет.
    """
    from tag_defs import load_tags, SORTS
    import json
    import os

    raw = json.load(open(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "..", "data", "hebrew_freq", "tags.json"), encoding="utf-8"))["tags"]
    for tag, spec in raw.items():
        assert spec.get("sort") in SORTS, f"{tag}: порядок не объявлен"
        assert spec.get("note"), f"{tag}: порядок не объяснён"


def test_rank_sorted_tags_come_out_in_rank_order():
    from tag_defs import load_tags
    defs = load_tags()
    for tag, spec in defs.items():
        if spec["sort"] != "ранг":
            continue
        members = spec["members"]
        assert members == sorted(members), f"{tag}: ранги не по возрастанию"


def test_manual_order_is_preserved_verbatim():
    """Ручной порядок нельзя молча пересортировать — в нём весь смысл."""
    from tag_defs import load_tags
    defs = load_tags()
    nums = defs["числительные"]["members"]
    # «один» частотнее «десяти», но идёт первым не поэтому, а по значению.
    assert nums[0] == 40 and nums[-1] == 781
    assert nums != sorted(nums), "числительные не должны идти по рангу"


def test_both_scripts_would_see_the_same_order():
    """
    Порядок читают два скрипта: apply_tags пишет его в слово, build_tag_groups
    раскладывает по нему строки. Расходиться они не должны — общий загрузчик
    для того и заведён.
    """
    import apply_tags
    import build_tag_groups
    from tag_defs import load_tags

    assert apply_tags.load_tags is load_tags
    assert build_tag_groups.load_tags is load_tags


# ── синонимы, выведенные из словаря ───────────────────────────────────────────

def test_forms_of_one_word_are_not_synonyms():
    """אותו и אותה — падежные формы, а не синонимы; однокоренные показывает свой блок."""
    from build_synonym_tags import lemma_of
    assert lemma_of({"hebrew": "הילד", "lemma": ""}) == "ילד"
    assert lemma_of({"hebrew": "ילד", "lemma": "ילד"}) == "ילד"


def test_gender_marks_keep_words_apart():
    """«они (м)» и «они (ж)» — הם и הן — разные слова, а не синонимический ряд."""
    from build_synonym_tags import sense
    assert sense("они (м)") != sense("они (ж)")


def test_a_comma_ends_the_meaning_just_like_a_semicolon():
    """
    Раньше здесь стояло sense("сейчас, теперь; ныне") == "сейчас, теперь":
    значение кончалось только на «;». Из-за этого «как» (#44) и «как,
    подобно» (#47) попадали в разные ключи, и ряд не собирался — хотя
    meanings_of() в quiz_service режет и по запятой и давно считает их одним
    значением. Два места понимали «значение» по-разному.

    Владелец заметил это на своих словах: «komo и eih — хорошо бы объединить
    в общий тег». Теперь разделителя два, и ключ — только первое значение.
    """
    from build_synonym_tags import sense
    assert sense("сейчас, теперь; ныне") == "сейчас"
    assert sense("как") == sense("как, подобно") == sense("как, каким образом")


def test_a_comma_inside_a_note_is_not_a_separator():
    """
    Пометы в скобках различают пары вроде «они (м)» и «они (ж)», и резать их
    нельзя. Запятая внутри скобок — часть пометы, а не конец значения.
    """
    from build_synonym_tags import sense
    assert sense("тут (чаще в речи, не на письме)") == "тут (чаще в речи, не на письме)"
    assert sense("тут (в речи), здесь") == "тут (в речи)"


def test_a_derived_synonym_row_is_marked_interchangeable():
    """
    Ряд собран по совпадению значения — значит его участники годятся друг за
    друга как ответ. Пометку читает бот: в пик-режиме такие слова нельзя
    подставлять вариантами одного вопроса.
    """
    from build_synonym_tags import build
    rows = [
        {"rank": 44, "hebrew": "איך", "lemma": "איך", "russian": "как"},
        {"rank": 993, "hebrew": "כיצד", "lemma": "כיצד", "russian": "как, каким образом"},
    ]
    tags = build(rows, curated={})
    assert tags, "ряд не собрался — проверка стала пустой"
    for spec in tags.values():
        assert spec["взаимозаменяемы"] is True


def test_spelling_variants_are_not_synonyms():
    """
    Ktiv male отличается вставленными вав и йод: עסקה и עיסקה — одно слово.
    Ловится как подпоследовательность.

    Перестановку букв (דיוויד против דייויד) это правило не ловит — такие пары
    отсеиваются другим условием, фильтром имён собственных, см. тест ниже.
    """
    from build_synonym_tags import same_spelling, skeleton
    # Матери чтения א,ה,ו,י пишутся или нет по традиции — костяк у вариантов один.
    assert skeleton("מאלה") == skeleton("מאלו")
    assert same_spelling("עסקה", "עיסקה")
    assert same_spelling("אימא", "האמא")     # то же слово с артиклем
    assert same_spelling("בשני", "בשתי")     # мужской и женский род, не синонимы
    # А это настоящие пары, и разойтись они не должны.
    assert not same_spelling("כאן", "פה")
    assert not same_spelling("בלי", "ללא")   # костяки «בל» и «לל» — разные слова


def test_short_skeletons_are_judged_strictly():
    """
    У двухбуквенного костяка расхождение в букву — половина слова. בלי и ללא
    дают «בל» и «לל»: по расстоянию это описка, по смыслу — два разных слова,
    оба «без». Поэтому послабление в одну букву только от трёх букв.
    """
    from build_synonym_tags import same_spelling
    assert not same_spelling("בלי", "ללא")
    assert same_spelling("בשני", "בשתי")


def test_proper_names_are_found_by_the_capital_letter():
    """
    Значения pos="имя" в словаре нет вовсе — у имён стоит «сущ», и прежний
    фильтр по части речи был мёртвым кодом. Заглавная буква в переводе
    отличает их надёжно: все остальные переводы строчные.
    """
    from build_synonym_tags import is_proper_name
    assert is_proper_name("Том")
    assert is_proper_name("Говард")
    assert not is_proper_name("только, лишь")


def test_proper_names_never_form_a_group():
    """Четыре написания имени «Дэвид» — не синонимический ряд."""
    from build_synonym_tags import build
    rows = [
        {"rank": 1, "hebrew": "דיוויד", "russian": "дэвид", "pos": "имя", "lemma": ""},
        {"rank": 2, "hebrew": "דייויד", "russian": "дэвид", "pos": "имя", "lemma": ""},
        {"rank": 3, "hebrew": "כאן", "russian": "здесь", "pos": "нареч", "lemma": ""},
        {"rank": 4, "hebrew": "פה", "russian": "здесь", "pos": "нареч", "lemma": ""},
    ]
    tags = build(rows)
    assert list(tags) == ["синонимы: здесь"], tags


def test_generated_groups_hold_at_least_two_lemmas():
    import json
    import os
    from build_synonym_tags import build
    data = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "..", "data", "hebrew_freq", "hebrew_freq_10000_full.json")
    tags = build(json.load(open(data, encoding="utf-8")))
    assert tags, "ни одной группы синонимов не выведено"
    for name, spec in tags.items():
        assert len(spec["members"]) >= 2, name
        assert len(set(spec["members"])) == len(spec["members"]), f"{name}: повтор ранга"
        assert spec["sort"] == "ранг", name


def test_manual_and_generated_tags_do_not_collide():
    """Совпадение имён тегов молча перетёрло бы курированную группу."""
    from tag_defs import load_tags
    defs = load_tags()
    manual = {k for k in defs if not k.startswith("синонимы:")}
    auto = {k for k in defs if k.startswith("синонимы:")}
    assert manual and auto
    assert not (manual & auto)


def test_gender_pairs_of_one_verb_are_not_synonyms():
    """
    כּוֹאֵב и כּוֹאֶבֶת — «болит» в мужском и женском роде, а русский перевод рода
    не различает. По лемме такое не поймать: у женской формы леммой записана
    мужская, а не корень — несогласованность в самих данных.
    """
    from build_synonym_tags import same_spelling
    assert same_spelling("כואב", "כואבת")
    assert not same_spelling("בלי", "ללא")


def test_a_group_already_covered_by_a_manual_tag_is_dropped():
    """
    Если все участники и так стоят рядом в ручной группе, синонимический ряд
    добавляет на карточку второй блок с тем же содержимым. Так было у «здесь»,
    «сюда», «отсюда» — все они лежат в «Здесь, сюда, отсюда».
    """
    from build_synonym_tags import build
    rows = [
        {"rank": 1, "hebrew": "כאן", "russian": "здесь", "pos": "нареч", "lemma": ""},
        {"rank": 2, "hebrew": "פה", "russian": "здесь", "pos": "нареч", "lemma": ""},
    ]
    assert build(rows, curated={}) , "без ручных групп ряд обязан остаться"
    assert build(rows, curated={1: {"где-то"}, 2: {"где-то"}}) == {}


def test_partial_overlap_keeps_the_group():
    """Один участник в ручной группе, другой нет — ряд ещё нужен: он и добавляет второго."""
    from build_synonym_tags import build
    rows = [
        {"rank": 1, "hebrew": "איפה", "russian": "где", "pos": "нареч", "lemma": ""},
        {"rank": 2, "hebrew": "היכן", "russian": "где", "pos": "нареч", "lemma": ""},
    ]
    assert build(rows, curated={1: {"вопросительные слова"}})


# ── огласовка против транскрипции ─────────────────────────────────────────────

# Обрывки иностранных имён: в них гласные передаются вольно, и сверка по
# гласным для них не работает по устройству, а не по ошибке.
NIQQUD_IPA_EXPECTED = {
    615,   # ורג — часть имени «Верг»
    690,   # מייקל — Майкл
    911,   # יימס — Джеймс
}


def test_vocalization_agrees_with_transcription_in_the_first_thousand():
    """
    Огласовка и IPA получены независимо, и гласные обязаны совпадать. Скрипт
    check_niqqud_vs_ipa это считает, но его надо было запустить и открыть отчёт
    — а расхождение по словам 69 и 669 пролежало в нём непрочитанным, пока
    владелец не заметил его глазами на карточке.

    Поэтому теперь это тест: находка не может остаться незамеченной, а новый
    обрывок имени придётся внести в список осознанно.
    """
    import json
    import os
    import sys

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, here)
    from check_niqqud_vs_ipa import niqqud_pattern, ipa_vowels

    data = os.path.join(here, "..", "data", "hebrew_freq", "hebrew_freq_10000_full.json")
    rows = [r for r in json.load(open(data, encoding="utf-8")) if r["rank"] <= 1000]
    # Не «ровно тысяча»: из частотного списка убраны дубликаты — одно и то же
    # слово, записанное с вав и без (ktiv male), стояло в нём дважды. Пропуск
    # в нумерации законен, а вот дыра размером в десяток слов означала бы, что
    # словарь обрезали по ошибке.
    assert len(rows) >= 990, f"первая тысяча поредела: осталось {len(rows)}"

    # Сравнение — регулярным выражением, а не строкой: у камаца два чтения
    # («a» или «o»), у шва и хатафов гласная может и не звучать, и шаблон это
    # выражает. Сначала я сравнил как строки и получил 200 «расхождений» на
    # ровном месте.
    import re
    mismatched = []
    for row in rows:
        niqqud, ipa = row.get("niqqud") or "", row.get("ipa") or ""
        if not niqqud or not ipa:
            continue
        pattern, vowels = niqqud_pattern(niqqud), ipa_vowels(ipa)
        if not pattern and not vowels:
            continue
        if not re.fullmatch(pattern, vowels) and row["rank"] not in NIQQUD_IPA_EXPECTED:
            mismatched.append((row["rank"], row["niqqud"], ipa, pattern, vowels))

    assert not mismatched, "огласовка расходится с транскрипцией:\n" + "\n".join(
        f"  #{r} {n} [{i}] огласовка даёт {w!r}, транскрипция {g!r}" for r, n, i, w, g in mismatched)


def _modal_fixture():
    """Тег с представителем и его же формой женского рода в also."""
    rows = [
        {"rank": 19, "hebrew": "רוצה", "niqqud": "רוֹצֶה", "lemma": "רצה",
         "ipa": "ʁoˈtse", "russian": "хочу, хочет",
         "tags": [{"tag": "модальные", "order": 1, "shown": True}]},
        {"rank": 29, "hebrew": "יכול", "niqqud": "יָכוֹל", "lemma": "יכל",
         "ipa": "jaˈχol", "russian": "могу, может (м)",
         "tags": [{"tag": "модальные", "order": 2, "shown": True}]},
        {"rank": 43, "hebrew": "צריך", "niqqud": "צָרִיךְ", "lemma": "צרך",
         "ipa": "tsaˈʁiχ", "russian": "нужно, надо",
         "tags": [{"tag": "модальные", "order": 3, "shown": True}]},
        {"rank": 80, "hebrew": "יכולה", "niqqud": "יְכוֹלָה", "lemma": "יכל",
         "ipa": "jeχoˈla", "russian": "могу, может (ж)",
         "tags": [{"tag": "модальные", "order": 0, "shown": False}]},
    ]
    defs = {"модальные": {"label": "🔑 Модальные слова", "sort": "ранг",
                          "members": [19, 29, 43], "also": [80]}}
    return rows, defs


def _group_of(rows, rank):
    return next(r for r in rows if r["rank"] == rank)["tag_groups"][0]["rows"]


def test_a_word_outside_the_group_still_finds_itself_in_it():
    """
    Слово из "also" получает тег и видит группу, но в состав не входит — иначе
    родственники содержали бы «ребёнок» трижды. Из-за этого в собственной
    таблице слова не было ни одной строки с self: открыв слово 80 «могу (ж)»,
    человек не находил в модальных самого себя. Своя строка обязана быть всегда.
    """
    import build_tag_groups
    rows, defs = _modal_fixture()
    build_tag_groups.build(rows, defs)

    own = _group_of(rows, 80)
    assert [r["rank"] for r in own if r["self"]] == [80]
    assert any(r["rank"] == 80 for r in own)


def test_own_row_stands_next_to_its_lemma_not_by_rank():
    """
    Место строки задаёт лемма, а не ранг. По рангу «могу (ж)» (80) встала бы
    после «нужно» (43) и оторвалась бы от «могу (м)» (29), с которым он и
    составляет пару.
    """
    import build_tag_groups
    rows, defs = _modal_fixture()
    build_tag_groups.build(rows, defs)

    ranks = [r["rank"] for r in _group_of(rows, 80)]
    assert ranks == [19, 29, 80, 43], ranks


def test_words_inside_the_group_get_no_extra_row():
    """Представителю добавлять нечего: он и так в составе, с ним ничего не меняется."""
    import build_tag_groups
    rows, defs = _modal_fixture()
    build_tag_groups.build(rows, defs)

    own = _group_of(rows, 29)
    assert [r["rank"] for r in own] == [19, 29, 43]
    assert [r["rank"] for r in own if r["self"]] == [29]


# ── Где в таблице группы встаёт строка самого слова ──────────────────────────

def _rows(*specs):
    """Строки таблицы: (ранг, перевод) — лемму держим отдельно, как в словаре."""
    return [{"rank": r, "ru": ru, "ipa": "", "foreign": "", "self": False}
            for r, ru in specs]


def test_own_row_joins_its_namesakes_not_the_last_same_root():
    """
    «эти הָאֵלֶּה» встаёт за «эти אֵלֶּה», а не за «такие כָּאֵלֶּה».

    У леммы אלה в указательных местоимениях две строки с разным смыслом —
    «эти» и «такие», — и поиск с конца таблицы находил вторую. Своя строка
    уезжала в самый хвост, под «такая», и таблица отвечала на вопрос «где тут
    я» неправдой: будто это слово из ряда «такой/такая/такие».
    """
    import build_tag_groups
    rows = _rows((3, "это, этот"), (264, "эти"), (620, "такие"))
    by_rank = {3: {"lemma": "זה"}, 264: {"lemma": "אלה"}, 620: {"lemma": "אלה"}}
    own = {"rank": 147, "ru": "эти", "ipa": "", "foreign": "", "self": True}
    out = build_tag_groups.insert_own(rows, own, by_rank, "אלה", "ручной")
    assert [r["rank"] for r in out] == [3, 264, 147, 620]


def test_own_row_joins_the_same_root_when_the_translation_differs():
    """«могу (ж)» идёт за «могу (м)»: та же лемма, перевод другой."""
    import build_tag_groups
    rows = _rows((29, "могу (м)"), (43, "нужно"))
    by_rank = {29: {"lemma": "יכול"}, 43: {"lemma": "צריך"}}
    own = {"rank": 80, "ru": "могу (ж)", "ipa": "", "foreign": "", "self": True}
    out = build_tag_groups.insert_own(rows, own, by_rank, "יכול", "ручной")
    assert [r["rank"] for r in out] == [29, 80, 43]


def test_the_base_form_keeps_its_place_at_the_tail_of_its_row():
    """
    «для, ради בִּשְׁבִיל» — основа всей парадигмы, своего значения среди
    «для меня / для тебя» у неё нет. Такая строка остаётся в хвосте своего
    ряда и не вклинивается между «для меня בִּשְׁבִילִי» и «для меня עֲבוּרִי».
    """
    import build_tag_groups
    rows = _rows((402, "для меня"), (1103, "для меня"), (5121, "для них"))
    by_rank = {402: {"lemma": "בשביל"}, 1103: {"lemma": "עבור"}, 5121: {"lemma": "בשביל"}}
    own = {"rank": 185, "ru": "для, ради", "ipa": "", "foreign": "", "self": True}
    out = build_tag_groups.insert_own(rows, own, by_rank, "בשביל", "ручной")
    assert [r["rank"] for r in out] == [402, 1103, 5121, 185]


def test_gender_mark_does_not_hide_the_shared_meaning():
    """«этот (м) הַזֶּה» встаёт за «это, этот זֶה»: пометка рода — не значение."""
    import build_tag_groups
    rows = _rows((3, "это, этот"), (60, "это, эта (ж)"), (181, "такой"))
    by_rank = {3: {"lemma": "זה"}, 60: {"lemma": "זה"}, 181: {"lemma": "זה"}}
    own = {"rank": 34, "ru": "этот (м)", "ipa": "", "foreign": "", "self": True}
    out = build_tag_groups.insert_own(rows, own, by_rank, "זה", "ручной")
    assert [r["rank"] for r in out] == [3, 34, 60, 181]


def test_own_row_goes_after_the_whole_block_of_its_kin():
    """
    Своя строка встаёт ЗА блоком однокоренных, а не внутрь него.

    У числительных «три (м)» и «три (ж)» идут подряд; вклиниваться между ними
    нельзя — порядок внутри значения задан вручную (сначала мужской род).
    """
    import build_tag_groups
    rows = _rows((532, "три (м)"), (417, "три (ж)"), (1235, "четыре (м)"))
    by_rank = {532: {"lemma": "שלוש"}, 417: {"lemma": "שלוש"}, 1235: {"lemma": "ארבע"}}
    own = {"rank": 9999, "ru": "три (разг.)", "ipa": "", "foreign": "", "self": True}
    out = build_tag_groups.insert_own(rows, own, by_rank, "שלוש", "ручной")
    assert [r["rank"] for r in out] == [532, 417, 9999, 1235]


def test_own_row_finds_its_namesakes_even_with_another_root():
    """
    Книжное «эти הַלָּלוּ» (лемма הללו) родни по лемме в таблице не имеет, но
    место его очевидно — среди остальных «эти», а не в конце под «такие».
    """
    import build_tag_groups
    rows = _rows((3, "это, этот"), (264, "эти"), (620, "такие"))
    by_rank = {3: {"lemma": "זה"}, 264: {"lemma": "אלה"}, 620: {"lemma": "אלה"}}
    own = {"rank": 773, "ru": "эти", "ipa": "", "foreign": "", "self": True}
    out = build_tag_groups.insert_own(rows, own, by_rank, "הללו", "ручной")
    assert [r["rank"] for r in out] == [3, 264, 773, 620]


def test_the_demonstratives_table_has_no_repeated_translations():
    """
    В таблице группы не должно быть двух строк с одним переводом.

    Жалоба владельца: «слова эти — 4 раза и не подряд, почему?». В состав
    указательных местоимений попали и формы с артиклем ה, и варианты (זו, אלו,
    האלו, הללו) — пять строк «эти» вперемешку с «тот» и «такой». По правилу
    самого словаря формы с артиклем в состав не входят: они получают тег и
    показывают группу, но своей строки не имеют (иначе «родственники»
    содержали бы «ребёнок» трижды).
    """
    from tag_defs import load_tags
    import json
    import os

    data = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "..", "data", "hebrew_freq", "hebrew_freq_10000_full.json")
    by_rank = {r["rank"]: r for r in json.load(open(data, encoding="utf-8"))}
    members = load_tags()["указательные местоимения"]["members"]
    seen = {}
    for rank in members:
        ru = by_rank[rank]["russian"].split(";")[0].strip()
        assert ru not in seen, (
            f"в составе две строки «{ru}»: #{seen[ru]} и #{rank}; "
            "форму с артиклем или вариант переносят в also")
        seen[ru] = rank


def test_russian_transcription_agrees_with_the_ipa_about_kaf():
    """
    Буква כ без дагеша звучит «х», и русская запись обязана говорить то же.

    Жалоба владельца про слово 196: «в транскрипции варианты К и х — как же
    правильно?». Правильно «х»: לְכָאן — это ל с шва плюс כ без дагеша, и IPA
    честно писал leˈχan, а русская строка рядом — «лэкАн». Человек видит на
    одной карточке два разных ответа и не знает, какому верить.

    Проверяем по самому надёжному признаку: если в IPA есть χ, в русской
    записи на его месте должно стоять «х», а не «к».
    """
    import json
    import os

    data = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "..", "data", "hebrew_freq", "hebrew_freq_10000_full.json")
    wrong = []
    for r in json.load(open(data, encoding="utf-8")):
        ipa, ru = r.get("ipa", ""), (r.get("translit_ru") or "").lower()
        n_khaf = ipa.count("χ")
        if n_khaf and ru.count("х") != n_khaf and ru.count("к") >= n_khaf:
            wrong.append(f"#{r['rank']} {r['niqqud']} [{ipa}] {r['translit_ru']}")
    assert not wrong, "русская запись спорит с IPA про כ:\n  " + "\n  ".join(wrong)


def test_no_two_words_share_a_vocalised_form():
    """
    Огласованная форма — это то, что видит человек на карточке, и она обязана
    быть у каждого слова своя.

    Как всплыло: синхронизация словаря в базу молча не доносила три слова —
    №421 הַכֹּל, №4494 רוֹזִי, №9225 לְהִיפָּגֵשׁ. У базы на эту форму стоит
    запрет повторов, и он отвергал вторую запись. В частотном списке это одно
    и то же слово, записанное двумя способами — с вав и без (ktiv male), — и
    попавшее в список дважды. Решение владельца: из пары оставлять меньший
    ранг, он же и частотнее.
    """
    import collections
    import json
    import os

    data = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "..", "data", "hebrew_freq", "hebrew_freq_10000_full.json")
    seen = collections.defaultdict(list)
    for r in json.load(open(data, encoding="utf-8")):
        form = (r.get("niqqud") or "").strip()
        if form:
            seen[form].append(r["rank"])
    doubles = {form: ranks for form, ranks in seen.items() if len(ranks) > 1}
    assert not doubles, "одна огласованная форма у разных номеров:\n  " + "\n  ".join(
        f"{form}: {ranks}" for form, ranks in doubles.items())


def test_a_prefix_table_shows_the_free_standing_word_and_marks_it():
    """
    В таблице приставки есть строка «то же отдельным словом», и она помечена.

    Вопрос владельца: «а есть ли такие приставки как отдельные слова, или они
    только в составе других?». Сами буквы — только в составе: однобуквенных
    записей в словаре нет ни одной. Но у пяти из семи есть свободные
    соответствия (מִן при מ, כְּמוֹ при כ, אֲשֶׁר при ש), и им место в той же
    таблице — с пометкой, иначе их не отличить от приставочных форм.
    """
    from tag_defs import load_tags
    import json
    import os

    data = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "..", "data", "hebrew_freq", "hebrew_freq_10000_full.json")
    by_rank = {r["rank"]: r for r in json.load(open(data, encoding="utf-8"))}
    defs = load_tags()

    # מִן — полная форма приставки מ, а не синоним: пометка у него своя.
    mem = defs["приставка מ"]
    assert 895 in mem["members"], "מִן не попал в таблицу приставки מ"
    assert mem["row_notes"]["895"] == "та же приставка целиком"
    assert by_rank[895]["hebrew"] == "מן"

    # У артикля ה и союза ו свободной формы нет — и выдумывать её нельзя.
    for letter in ("ה", "ו"):
        assert not defs[f"приставка {letter}"].get("row_notes"), (
            f"у приставки {letter} появилось «отдельное слово», которого в языке нет")

    # Помеченное слово не должно быть приставочной формой — иначе пометка
    # врала бы. Проверяем тем же правилом, каким формы и находятся: буква
    # плюс слово из словаря при общей лемме. По одной лишь первой букве судить
    # нельзя: בְּתוֹךְ «внутри» начинается с ב, но это самостоятельный предлог,
    # а не ב, приставленное к слову תוך.
    import build_prefix_tags

    found = build_prefix_tags.prefixed_forms(list(by_rank.values()))
    for letter in ("ש", "ב", "ל", "מ", "כ"):
        spec = defs[f"приставка {letter}"]
        assert spec.get("row_notes"), f"у приставки {letter} нет отдельного слова"
        mechanical = {r["rank"] for r, _ in found[letter]}
        for rank in spec["row_notes"]:
            assert int(rank) not in mechanical, (
                f"#{rank} {by_rank[int(rank)]['hebrew']} помечено как отдельное слово, "
                "но это приставочная форма")


def test_the_note_reaches_the_row_of_the_table():
    """Пометка должна доехать до строки, а не остаться в определении тега."""
    import build_tag_groups

    rows = [
        {"rank": 175, "hebrew": "מזה", "niqqud": "מִזֶּה", "ipa": "miˈze",
         "russian": "из этого", "lemma": "זה",
         "tags": [{"tag": "приставка מ", "order": 1, "shown": True}]},
        {"rank": 895, "hebrew": "מן", "niqqud": "מִן", "ipa": "min",
         "russian": "из, от", "lemma": "מן",
         "tags": [{"tag": "приставка מ", "order": 2, "shown": True}]},
    ]
    defs = {"приставка מ": {
        "label": "🔤 Приставка מ — «из, от»", "note": "по частотности", "sort": "ранг",
        "members": [175, 895], "also": [], "row_notes": {"895": "та же приставка целиком"},
    }}
    build_tag_groups.build(rows, defs)
    table = {r["rank"]: r["ru"] for r in rows[0]["tag_groups"][0]["rows"]}
    assert table[175] == "из этого", "пометка прилипла не к той строке"
    assert table[895] == "из, от — та же приставка целиком"


def test_homographs_are_voiced_from_the_vocalised_form():
    """
    Омографы озвучиваются по огласовке, а не по голым согласным.

    Жалоба владельца про слово 233: транскрипция «бэхА», а голоса говорят
    «бах», «бех», «бех». Причина — все звуки делались из поля `hebrew`, то
    есть из написания без огласовки, а у 108 записей оно читается двумя
    способами. Движок выбирал чтение сам и для בך брал женское בָּךְ.
    Проверено на слух: из огласованной בְּךָ выходит «беха» — верно.

    Проверяем само правило: для слова с вариантами огласовки на озвучку
    обязана идти огласованная форма.
    """
    import os
    import sys

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, here)
    import regen_homograph_sounds as regen

    rows = [
        {"rank": 233, "hebrew": "בך", "niqqud": "בְּךָ", "russian": "в тебе",
         "tones": "<b>בך</b>: <i>вариантов огласовки: 2</i>\n - ..."},
        {"rank": 68, "hebrew": "דבר", "niqqud": "דָּבָר", "russian": "вещь", "tones": ""},
    ]
    targets = regen.homographs(rows)
    assert [r["rank"] for r in targets] == [233], "омограф опознан неверно"
    # На озвучку идёт огласованная форма — ровно та, которую подтвердили на слух.
    assert targets[0]["niqqud"] == "בְּךָ"
    assert targets[0]["niqqud"] != targets[0]["hebrew"]


def test_the_new_sound_gets_a_new_path():
    """
    Переозвученный файл обязан называться иначе.

    Телефон кеширует звуки по пути: тот же путь — тот же файл, и
    перезаписанный на сервере до него уже не доедет. Новое имя заодно
    оставляет прежние файлы на месте, так что откат — это вернуть старые пути.
    """
    import os
    import sys

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, here)
    import regen_homograph_sounds as regen

    assert regen.SUFFIX, "суффикс пути пуст — новый файл затрёт старый"
    for folder, _ in regen.VOICES:
        path = f"sounds/he/{folder}/233{regen.SUFFIX}.mp3"
        assert path != f"sounds/he/{folder}/233.mp3"


def test_the_superlative_is_tied_to_the_word_it_is_made_from():
    """
    «Самый» и «больше» связаны: בְּיוֹתֵר — это ב + יוֹתֵר.

    Жалоба владельца: «слово 32 "больше", есть ещё "самый" — отличаются
    только приставкой», а на карточке они ничем не связаны. Причина: у №193
    лемма стояла своя собственная (ביותר), тогда как у всех четырёх собратьев
    по той же основе — יותר. Словарь спорил сам с собой, и №193 выпадал и из
    группы приставки ב, и из списка однокоренных слова №32.

    Общего правила тут нет: ש и מ в начале слова бывают и приставкой, и частью
    самого слова — שָׁכֵן «сосед» не из ש+כן, מָרָק «суп» не из מ+רק. Поэтому
    проверяется семья, в которой связь установлена, а не догадка про все.
    """
    import json
    import os

    data = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "..", "data", "hebrew_freq", "hebrew_freq_10000_full.json")
    by_rank = {r["rank"]: r for r in json.load(open(data, encoding="utf-8"))}

    assert by_rank[193]["lemma"] == "יותר", "превосходная степень снова оторвана от основы"
    family = {rank for rank, r in by_rank.items() if r.get("lemma") == "יותר"}
    assert {32, 193, 2612, 2848, 3776, 6703} <= family, sorted(family)

    # И это должно быть видно на карточке самого слова «больше».
    refs = by_rank[32].get("references") or ""
    assert "[#193]" in refs, "на карточке «больше» не видно «самый»"


# ── пометка «взаимозаменяемы»: от определения тега до записи слова ───────────

def _defs_file(tmp_path, spec):
    path = tmp_path / "tags.json"
    path.write_text(json.dumps({"tags": {"проба": spec}}, ensure_ascii=False),
                    encoding="utf-8")
    return str(path)


def test_the_interchangeable_mark_reaches_the_word(tmp_path):
    """
    Пометка нужна боту, а он живёт в другом репозитории и tags.json не видит.
    Единственный путь к нему — сама запись слова.
    """
    import apply_tags
    from tag_defs import load_tags

    defs = load_tags(_defs_file(tmp_path, {
        "label": "проба", "sort": "ранг", "взаимозаменяемы": True,
        "members": [1, 2], "also": [3]}), auto=None, forms=None, prefixes=None)
    rows = [{"rank": n, "hebrew": "x", "russian": "y"} for n in (1, 2, 3)]
    apply_tags.apply(rows, defs)

    for row in rows:
        assert row["tags"][0]["взаимозаменяемы"] is True, row
    # Форма из "also" в списке группы не показывается, но пометку наследует:
    # הנכון рядом с נכון — это выбор между словом и им же с артиклем.
    assert rows[2]["tags"][0]["shown"] is False


def test_an_unmarked_tag_leaves_the_word_record_alone(tmp_path):
    """Помечен не всякий тег. У 465 тегов лишнее поле в каждой записи — вес без смысла."""
    import apply_tags
    from tag_defs import load_tags

    defs = load_tags(_defs_file(tmp_path, {
        "label": "проба", "sort": "ранг", "members": [1]}),
        auto=None, forms=None, prefixes=None)
    rows = [{"rank": 1, "hebrew": "x", "russian": "y"}]
    apply_tags.apply(rows, defs)

    assert "взаимозаменяемы" not in rows[0]["tags"][0]


def test_a_misspelled_field_in_a_tag_definition_is_refused(tmp_path):
    """
    Опечатка в имени поля не делает ничего и ничего не говорит — а выглядит
    как сделанная работа. Ровно так ведёт себя «взаимозаменяемый» вместо
    «взаимозаменяемы».
    """
    from tag_defs import load_tags

    path = _defs_file(tmp_path, {
        "label": "проба", "sort": "ранг", "members": [1],
        "взаимозаменяемый": True})
    with pytest.raises(ValueError, match="неизвестные поля"):
        load_tags(path, auto=None, forms=None, prefixes=None)


def test_the_interchangeable_field_must_be_a_boolean(tmp_path):
    """«взаимозаменяемы»: "да" — строка, она истинна всегда, в том числе "нет"."""
    from tag_defs import load_tags

    path = _defs_file(tmp_path, {
        "label": "проба", "sort": "ранг", "members": [1],
        "взаимозаменяемы": "нет"})
    with pytest.raises(ValueError, match="взаимозаменяемы"):
        load_tags(path, auto=None, forms=None, prefixes=None)
