#!/usr/bin/env python3
"""Проставляет словам теги по определениям из tags.json.

Тег — группа слов, которые полезно повторять вместе: числительные, родственники,
части тела. Частотный список к таким группам безразличен — «один» стоит на 40-м
месте, «десять» на 890-м, — поэтому порядок показа задаётся в определениях
вручную, а здесь только переносится в записи словаря.

В запись слова кладётся:
    "tags": [{"tag": "числительные", "order": 3, "shown": true}]

order — место в группе. shown=false у форм с артиклем ה и притяжательных: тег
они получают (и группу на карточке показывают), но сами в списке не значатся,
иначе «родственники» содержали бы «ребёнок» трижды.

Запуск:  python words/hebrew_tools/apply_tags.py [--dry]
"""
import argparse
import json
import os
import sys

from tag_defs import load_tags

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data", "hebrew_freq"))
FULL = os.path.join(DATA, "hebrew_freq_10000_full.json")
TAGS = os.path.join(DATA, "tags.json")


def load():
    with open(FULL, encoding="utf-8") as fh:
        rows = json.load(fh)
    # Порядок участников считает общий модуль: его же читает build_tag_groups.
    # Пока правило жило в двух местах, оно могло разъехаться молча.
    return rows, load_tags(TAGS)


def validate(rows, defs):
    """Ранг, указанный мимо, молча пометит чужое слово. Проверяем до записи."""
    by_rank = {r["rank"]: r for r in rows}
    problems = []
    for tag, spec in defs.items():
        members = spec.get("members", [])
        also = spec.get("also", [])
        seen = set()
        for rank in members + also:
            if rank not in by_rank:
                problems.append(f"{tag}: ранга {rank} нет в словаре")
            if rank in seen:
                problems.append(f"{tag}: ранг {rank} указан дважды")
            seen.add(rank)
    return problems


def _entry(tag: str, spec: dict, order: int, shown: bool) -> dict:
    """Запись тега в слове.

    Пометка «взаимозаменяемы» переносится в каждое слово, а не остаётся в
    определениях, потому что читать её будет бот: у него есть слово целиком и
    нет доступа к tags.json — он живёт в другом репозитории. Ставим её только
    когда она истинна: у 465 тегов на 5236 слов лишнее поле в каждой записи
    ничего не объясняет, а место занимает.
    """
    entry = {"tag": tag, "order": order, "shown": shown}
    if spec.get("взаимозаменяемы"):
        entry["взаимозаменяемы"] = True
    return entry


def apply(rows, defs):
    by_rank = {r["rank"]: r for r in rows}
    for r in rows:
        r.pop("tags", None)
    for tag, spec in defs.items():
        for order, rank in enumerate(spec.get("members", []), start=1):
            by_rank[rank].setdefault("tags", []).append(
                _entry(tag, spec, order, True))
        # Формы с артиклем и притяжательные в списке не показываются, но как
        # варианты ответа они путают сильнее самих слов: הַנָּכוֹן рядом с
        # נָכוֹן — выбор между словом и им же с артиклем. Пометку наследуют.
        for rank in spec.get("also", []):
            by_rank[rank].setdefault("tags", []).append(
                _entry(tag, spec, 0, False))
    return sum(1 for r in rows if r.get("tags"))


def report(rows, defs):
    """Печатаем группы целиком: разметку проверяют глазами, а не пересчётом."""
    by_rank = {r["rank"]: r for r in rows}
    for tag, spec in defs.items():
        print(f"\n=== {spec['label']}  ({tag})")
        if spec.get("note"):
            print(f"    порядок: {spec['note']}")
        for order, rank in enumerate(spec.get("members", []), start=1):
            r = by_rank[rank]
            print(f"    {order:>2}. #{rank:<5} {(r['niqqud'] or r['hebrew']):<16} "
                  f"{r['ipa']:<14} {r['russian'][:38]}")
        if spec.get("also"):
            forms = ", ".join(f"#{k}" for k in spec["also"])
            print(f"    также помечены (в списке не показываются): {forms}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="показать и не записывать")
    args = ap.parse_args()

    rows, defs = load()
    problems = validate(rows, defs)
    if problems:
        print("остановлено, определения тегов неверны:")
        for p in problems:
            print(f"  {p}")
        return 1

    tagged = apply(rows, defs)
    report(rows, defs)

    if args.dry:
        print(f"\n[--dry] помечено было бы слов: {tagged}")
        return 0

    tmp = FULL + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, FULL)
    print(f"\nпомечено слов: {tagged}, тегов: {len(defs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
