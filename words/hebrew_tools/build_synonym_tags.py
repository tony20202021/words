#!/usr/bin/env python3
"""Выводит теги-синонимы из словаря: разные слова с одним значением.

Чем это отличается от остальных тегов. Числительные и родственники курируются
вручную — состав и порядок задаёт человек. Синонимы курировать нельзя, их
слишком много, зато они выводятся механически: у двух записей совпадает первое
значение перевода.

Наивное сравнение даёт половину мусора, поэтому отсеиваются три вещи.

  Формы одного слова. אותו и אותה — не синонимы, а падежные формы, и
  однокоренные показывает свой блок. Сравниваем по леммам, по одному
  представителю на лемму.

  Род и лицо. «они (м)» и «они (ж)» — הם и הן — разные слова, а не синонимы.
  Поэтому пометы в скобках НЕ срезаются: они и различают такие пары.

  Варианты написания. דיוויד, דייויד, דיויד — одно имя, записанное по-разному
  (ktiv male). Отсеиваются похожие написания и все имена собственные.

Результат пишется в tags_synonyms.json рядом с ручным tags.json — файл
перегенерируется и просматривается глазами, а не собирается на лету.

Запуск:  python words/hebrew_tools/build_synonym_tags.py [--dry]
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data", "hebrew_freq"))
FULL = os.path.join(DATA, "hebrew_freq_10000_full.json")
OUT = os.path.join(DATA, "tags_synonyms.json")

LABEL = "🔗 То же значение"


def sense(translation: str) -> str:
    """Первое значение целиком, вместе с пометами: они и различают род и лицо."""
    return (translation or "").split(";")[0].strip().lower()


def lemma_of(row: dict) -> str:
    lemma = (row.get("lemma") or "").strip()
    if lemma:
        return lemma
    word = row.get("hebrew", "")
    # Определённый артикль ה превращает слово в «то же самое с артиклем».
    return word[1:] if word.startswith("ה") and len(word) > 2 else word


def same_spelling(a: str, b: str) -> bool:
    """Одно слово, записанное по-разному: ktiv male отличается вставкой вав/йод."""
    if abs(len(a) - len(b)) > 2:
        return False
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    it = iter(long)
    return all(ch in it for ch in short)


def build(rows: list) -> dict:
    by_sense = collections.defaultdict(list)
    for row in rows:
        if row.get("pos") == "имя":       # имена собственные синонимов не образуют
            continue
        key = sense(row.get("russian", ""))
        if len(key) > 1:
            by_sense[key].append(row)

    tags = {}
    for key, words in by_sense.items():
        per_lemma = {}
        for w in words:
            per_lemma.setdefault(lemma_of(w), w)
        kept = []
        for w in sorted(per_lemma.values(), key=lambda x: x["rank"]):
            if any(same_spelling(w["hebrew"], k["hebrew"]) for k in kept):
                continue
            kept.append(w)
        if len(kept) > 1:
            tags[f"синонимы: {key}"] = {
                "label": LABEL,
                "note": "по частотности: между синонимами естественного порядка нет",
                "sort": "ранг",
                "members": sorted(w["rank"] for w in kept),
                "also": [],
            }
    return tags


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--show", type=int, default=12, help="сколько групп показать")
    args = ap.parse_args()

    with open(FULL, encoding="utf-8") as fh:
        rows = json.load(fh)
    by_rank = {r["rank"]: r for r in rows}
    tags = build(rows)

    covered = {rk for spec in tags.values() for rk in spec["members"]}
    print(f"  групп синонимов: {len(tags)}, слов в них: {len(covered)}")
    shown = sorted(tags.items(), key=lambda kv: min(kv[1]["members"]))[:args.show]
    for name, spec in shown:
        forms = ", ".join(f"{by_rank[rk]['hebrew']}#{rk}" for rk in spec["members"])
        print(f"    {name[10:]:<26} {forms}")

    if args.dry:
        print("\n[--dry] не записано")
        return 0
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"_": ["Сгенерировано build_synonym_tags.py — правьте генератор, не файл."],
                   "tags": tags}, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)
    print(f"\nзаписано: {os.path.relpath(OUT, os.path.join(HERE, '..', '..'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
