#!/usr/bin/env python3
"""Собирает по проставленным тегам готовые к показу группы — поле tag_groups.

Зачем отдельным проходом. Тег на слове говорит только «оно из этой группы».
Чтобы показать группу на карточке, нужен весь её состав в нужном порядке, а он
разбросан по словарю: «один» на 40-м месте, «десять» на 890-м. Собирать это на
каждый показ — лишняя работа сервера, а собирать в трёх клиентах — три копии
знания. Поэтому группа складывается здесь, один раз.

В запись кладётся:
    "tag_groups": [{"tag": "...", "label": "...", "rows": [
        {"rank": 40, "ru": "один", "ipa": "ʔeˈχad", "foreign": "אֶחָד", "self": false}]}]

Строки с shown=false в состав не входят: формы с артиклем ה и притяжательные
получают тег и показывают группу, но сами в ней не значатся — иначе
«родственники» содержали бы «ребёнок» трижды.

Запуск:  python words/hebrew_tools/build_tag_groups.py [--dry]
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


def primary(translation: str) -> str:
    """Первое значение: в колонке таблицы длинному перечислению не место."""
    head = (translation or "").split(";")[0].strip()
    return head or (translation or "").strip()


def build(rows, defs):
    by_rank = {r["rank"]: r for r in rows}

    # Состав каждой группы — один раз на все слова.
    composition = {}
    for tag, spec in defs.items():
        composition[tag] = [{
            "rank": rank,
            "ru": primary(by_rank[rank].get("russian", "")),
            "ipa": by_rank[rank].get("ipa", ""),
            "foreign": by_rank[rank].get("niqqud") or by_rank[rank].get("hebrew", ""),
        } for rank in spec.get("members", [])]

    built = 0
    for r in rows:
        r.pop("tag_groups", None)
        tags = r.get("tags") or []
        if not tags:
            continue
        groups = []
        for t in sorted(tags, key=lambda x: x["tag"]):
            rows_out = [dict(row, self=(row["rank"] == r["rank"]))
                        for row in composition[t["tag"]]]
            groups.append({
                "tag": t["tag"],
                "label": defs[t["tag"]]["label"],
                "rows": rows_out,
            })
        if groups:
            r["tag_groups"] = groups
            built += 1
    return built, composition


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    with open(FULL, encoding="utf-8") as fh:
        rows = json.load(fh)
    defs = load_tags(TAGS)

    built, composition = build(rows, defs)

    for tag, comp in composition.items():
        print(f"  {defs[tag]['label']:<30} строк в группе: {len(comp)}")
    print(f"\nслов с собранными группами: {built}")

    example = next((r for r in rows if r["rank"] == 417), None)
    if example and example.get("tag_groups"):
        g = example["tag_groups"][0]
        print(f"\nпример — слово #417 {example['hebrew']} ({example['russian']}), группа «{g['tag']}»:")
        for row in g["rows"][:6]:
            mark = " ←" if row["self"] else ""
            print(f"    #{row['rank']:<5} {row['ru']:<14} [{row['ipa']}]  {row['foreign']}{mark}")
        print(f"    … всего строк: {len(g['rows'])}")

    if args.dry:
        print("\n[--dry] не записано")
        return 0
    tmp = FULL + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, FULL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
