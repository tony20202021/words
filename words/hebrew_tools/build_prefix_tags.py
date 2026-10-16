#!/usr/bin/env python3
"""Выводит теги-приставки: одна буква спереди — много разных слов.

Что было не так у первой версии. Группа «Буквы-приставки» была одна на все
семь букв, и в ней стояло по одному слову на букву: הַדָּבָר, וְלֹא, שֶׁלֹּא,
בַּבַּיִת… Владелец: «странный набор — разные приставки и разные основы; надо
либо одну приставку с разными словами, либо одну основу с разными приставками».
Он прав: когда меняется и буква, и основа, сравнивать не с чем и правила не
видно.

Выбрана первая: ОДНА приставка, разные слова. Вторую — одну основу с разными
приставками — уже показывает блок однокоренных: он собран по лемме, а
приставочные формы лемму основы и сохраняют. А вот «что делает вот эта буква»
не отвечал никто, хотя вопрос возникает на каждой второй карточке.

Что считается приставочной формой — два признака, оба механические:

  Написание. Неогласованная форма — это буква плюс слово, которое в словаре
  есть: הדבר = ה + דבר.

  Лемма. У формы и у основы она одна. Без этого правило ловило הָיָה «был» как
  ה + יה и מָקוֹם «место» как מ + קום.

Отсеиваются глагольные формы на ל и מ: לִהְיוֹת «быть» — это инфинитив, а
מְנַסֶּה «пытаюсь» — причастие. Буква там есть, но она не предлог, и в таблицу
про «к, для» и «из, от» им не место.

В состав группы идут восемь самых частых примеров — таблица на карточке должна
читаться, а не прокручиваться. Остальные формы получают тег и видят группу:
своя строка добавляется к ним отдельно, по рангу.

Результат пишется в tags_prefixes.json рядом с ручным tags.json — файл
перегенерируется и просматривается глазами, а не собирается на лету.

Запуск:  python words/hebrew_tools/build_prefix_tags.py [--dry]
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data", "hebrew_freq"))
FULL = os.path.join(DATA, "hebrew_freq_10000_full.json")
OUT = os.path.join(DATA, "tags_prefixes.json")

# Буква, что она значит, и что написать в заголовке группы.
PREFIXES = {
    "ה": ("артикль", "🔤 Приставка ה — «тот самый»"),
    "ו": ("и", "🔤 Приставка ו — «и, а»"),
    "ש": ("что, который", "🔤 Приставка ש — «что, который»"),
    "ב": ("в", "🔤 Приставка ב — «в»"),
    "ל": ("к, для", "🔤 Приставка ל — «к, для»"),
    "מ": ("из, от", "🔤 Приставка מ — «из, от»"),
    "כ": ("как", "🔤 Приставка כ — «как»"),
}

# На ל и מ держатся ещё и глагольные формы — инфинитив и причастие. Буква та
# же, смысл другой, и в таблицу про предлог они не идут.
VERB_PREFIXES = ("ל", "מ")

SHOWN = 8

# Отдельные слова с тем же смыслом, что у приставки.
#
# Вопрос владельца: «а есть ли такие приставки как отдельные слова, или они
# только в составе других?». Сами буквы — только в составе: однобуквенных
# записей в словаре нет ни одной, מש"ה וכל"ב всегда пишутся слитно. Но у пяти
# из семи есть свободные соответствия, и в таблице им место — иначе человек
# так и не узнает, что то же самое умеет говориться отдельным словом.
#
# מִן стоит особняком: это не синоним, а полная форма той же приставки —
# מ- и есть сокращённое מן. Поэтому у него пометка другая.
FREE_WORDS = {
    "ש": {871: "то же отдельным словом"},        # אֲשֶׁר который, что
    "ב": {473: "то же отдельным словом"},        # בְּתוֹךְ внутри, в
    "ל": {64: "то же отдельным словом",          # אֶל к, в (направление)
          185: "то же отдельным словом"},        # בִּשְׁבִיל для, ради
    "מ": {895: "та же приставка целиком"},       # מִן из, от
    "כ": {47: "то же отдельным словом"},         # כְּמוֹ как, подобно
    # У артикля ה и союза ו свободной формы нет совсем: они существуют
    # только приклеенными.
}


def prefixed_forms(rows):
    """{буква: [(форма, основа)]}, от частого к редкому."""
    by_hebrew = {}
    for r in rows:
        by_hebrew.setdefault(r["hebrew"], r)

    found = collections.defaultdict(list)
    for r in sorted(rows, key=lambda r: r["rank"]):
        word = r["hebrew"]
        if len(word) < 3:
            continue
        letter, rest = word[0], word[1:]
        if letter not in PREFIXES:
            continue
        base = by_hebrew.get(rest)
        if base is None or not r.get("lemma") or r["lemma"] != base.get("lemma"):
            continue
        if letter in VERB_PREFIXES and r.get("pos") == "глаг":
            continue
        found[letter].append((r, base))
    return found


def build(rows):
    tags = {}
    for letter, forms in prefixed_forms(rows).items():
        if len(forms) < 2:
            continue
        meaning, label = PREFIXES[letter]
        ranks = [r["rank"] for r, _ in forms]
        free = FREE_WORDS.get(letter, {})
        members = sorted(set(ranks[:SHOWN]) | set(free))
        tags[f"приставка {letter}"] = {
            "label": label,
            "note": (f"по частотности: одна и та же приставка {letter} ({meaning}) "
                     f"на разных словах — видно, что она делает; отдельной строкой "
                     f"то же самое отдельным словом, если оно есть"),
            "sort": "ранг",
            "members": members,
            "also": sorted(r for r in ranks[SHOWN:] if r not in free),
            "row_notes": {str(rank): note for rank, note in free.items()},
        }
    return tags


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    with open(FULL, encoding="utf-8") as fh:
        rows = json.load(fh)
    by_rank = {r["rank"]: r for r in rows}
    tags = build(rows)

    covered = {rk for spec in tags.values()
               for rk in spec["members"] + spec["also"]}
    print(f"  групп приставок: {len(tags)}, слов в них: {len(covered)}")
    for name, spec in tags.items():
        shown = ", ".join(
            f"{by_rank[rk]['hebrew']}#{rk} {by_rank[rk]['russian'][:18]}"
            for rk in spec["members"])
        print(f"    {name:<14} ({len(spec['also']):>4} ещё) {shown}")

    if args.dry:
        print("\n[--dry] не записано")
        return 0
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"_": ["Сгенерировано build_prefix_tags.py — правьте генератор, не файл."],
                   "tags": tags}, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)
    print(f"\nзаписано: {os.path.relpath(OUT, os.path.join(HERE, '..', '..'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
