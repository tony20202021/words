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
    assert sense("сейчас, теперь; ныне") == "сейчас, теперь"


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
    assert len(rows) == 1000, "первая тысяча неполна"

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
