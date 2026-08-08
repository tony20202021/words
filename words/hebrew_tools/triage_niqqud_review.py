#!/usr/bin/env python3
"""
Разбор слов, где огласовка разошлась с транскрипцией.

check_niqqud_vs_ipa.py находит расхождения, но «260 слов на проверку» — это
не результат. Здесь они раскладываются по ПРИЧИНЕ расхождения, потому что
причины разные и требуют разного:

  ipa_corrupt   транскрипция явно испорчена — удвоенные слоги (maʔaʔaʁiˈtsim),
                удвоенные согласные (lannaˈχot), обрывки. Огласовка вернее,
                менять её нельзя.
  proper_noun   имя или фамилия. Огласовка — условная транслитерация на иврит,
                транскрипция идёт от языка-источника. Оба варианта законны.
  source_junk   обрывок слова или аббревиатура из частотного списка. Огласовывать
                нечего, и сверять тоже.
  prefix_vowel  приставка ב/ל/כ/ה перед словом: неогласованное בכסף читается и
                be-kesef, и ba-kesef. Оба — существующие слова, выбор зависит от
                определённости, которую в списке никто не фиксировал.
  verb_person   форма 2-го лица: ברחת это и baraχta (м.р.), и baraχt (ж.р.).
                Согласные одни и те же, различие только в огласовке.
  needs_human   всё остальное — настоящий предмет для носителя или словаря.

Использование
-------------
    python triage_niqqud_review.py            # сводка
    python triage_niqqud_review.py --show needs_human
    python triage_niqqud_review.py --write    # разложить по файлам
"""

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hebrew_freq")
SRC = os.path.join(HERE, "niqqud_needs_review.json")

PREFIXES = "בלכהומש"


def has_doubled_syllable(ipa: str) -> bool:
    """Удвоенный слог с гортанной смычкой: maʔaʔaʁitsim, ʔavaʔada, mezaʔazeʔa."""
    return bool(re.search(r"ʔ[aeiou]ʔ[aeiou]", ipa))


def has_doubled_consonant(ipa: str) -> bool:
    """Удвоенная согласная — в иврите на слух не различается, в IPA признак сбоя."""
    return bool(re.search(r"([bdfɡklmnpʁstvzχʃʒ])\1", ipa))


def is_proper_noun(russian: str) -> bool:
    if re.search(r"\((имя|фамилия)\)", russian):
        return True
    # Одиночное слово с заглавной буквы и без пояснений — тоже имя.
    head = russian.split(";")[0].split(",")[0].strip()
    return bool(head) and head[0].isupper() and " " not in head


def is_source_junk(russian: str) -> bool:
    return bool(re.search(r"\((обрывок|сокр\.?)", russian))


def strip_marks(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn")


def _atoms(pattern: str) -> list[str]:
    """Разбить шаблон на элементы: [ao], e?, a, i…"""
    return re.findall(r"\[[^\]]+\]\??|.\?|.", pattern)


def differs_only_in_first_vowel(niqqud: str, ipa: str) -> bool:
    """
    Совпадёт ли шаблон, если разрешить любой первый гласный.

    Сравнивать длины напрямую нельзя: немая шва в шаблоне необязательна, из-за
    неё число гласных в огласовке и транскрипции законно расходится.
    """
    from check_niqqud_vs_ipa import ipa_vowels, niqqud_pattern
    iv = ipa_vowels(ipa)
    atoms = _atoms(niqqud_pattern(niqqud))
    if not atoms or len(iv) < 2:
        return False
    relaxed = "[aeiou]?" + "".join(atoms[1:])
    return bool(re.fullmatch(relaxed, iv))


def looks_like_prefix(hebrew: str, niqqud: str, ipa: str) -> bool:
    """
    Приставка ב/ל/כ/ה перед словом: неогласованное בכסף читается и be-kesef
    (в деньгах), и ba-kesef (за деньги — с определённым артиклем). Согласные
    одни и те же, спор только о первом гласном.
    """
    return (len(hebrew) > 2 and hebrew[0] in PREFIXES
            and differs_only_in_first_vowel(niqqud, ipa))


def is_second_person_form(hebrew: str, russian: str) -> bool:
    """
    Форма 2-го лица: род различает только огласовка.
      глагол на ת   — ברחת это baraχta (м.) и baraχt (ж.)
      суффикс ך     — אימך это imχa (твоя мать, к мужчине) и imeχ (к женщине)
    """
    if hebrew.endswith("ת") and re.search(r"\bты\b", russian):
        return True
    return hebrew.endswith("ך") and bool(re.search(r"тво|тебя|тебе", russian))


def classify(rec: dict) -> str:
    ipa, ru, heb, niq = rec["ipa"], rec["russian"], rec["hebrew"], rec["niqqud"]
    if is_source_junk(ru):
        return "source_junk"
    if has_doubled_syllable(ipa) or has_doubled_consonant(ipa):
        return "ipa_corrupt"
    if is_proper_noun(ru):
        return "proper_noun"
    if is_second_person_form(heb, ru):
        return "verb_person"
    if looks_like_prefix(heb, niq, ipa):
        return "prefix_vowel"
    return "needs_human"


ORDER = ["ipa_corrupt", "proper_noun", "source_junk", "prefix_vowel",
         "verb_person", "needs_human"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--show", help="напечатать одну категорию целиком")
    ap.add_argument("--write", action="store_true", help="разложить по файлам")
    args = ap.parse_args()

    recs = json.load(open(SRC, encoding="utf-8"))
    buckets: dict[str, list[dict]] = {k: [] for k in ORDER}
    for r in recs:
        buckets[classify(r)].append(r)

    print(f"расхождений всего: {len(recs)}\n")
    for k in ORDER:
        print(f"  {k:14} {len(buckets[k]):4}")

    if args.show:
        rows = buckets.get(args.show, [])
        print(f"\n{args.show} — {len(rows)}:")
        for r in rows:
            print(f"  {r['rank']:5} {r['hebrew']:14} {r['niqqud']:18} {r['ipa']:16} {r['russian']}")

    if args.write:
        for k in ORDER:
            path = os.path.join(HERE, f"review_{k}.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(buckets[k], fh, ensure_ascii=False, indent=2)
            print(f"  записано {os.path.basename(path)}: {len(buckets[k])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
