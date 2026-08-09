#!/usr/bin/env python3
"""
Заполняет для иврита поля tones и references — по смыслу, а не по названию.

Почему эти поля подходят
------------------------
Оба поля заводились под китайский, но задачи, которые они решают, у иврита ровно
те же — меняется только чем именно письмо неоднозначно.

  tones       В китайском одна и та же транскрипция с разными тонами это разные
              слова: ma -> mā «мама», mǎ «лошадь». В иврите то же самое делает
              огласовка при одинаковых согласных: יצר -> יֵצֶר «инстинкт»,
              יָצַר «создал». В обоих случаях письмо не различает слова, а
              диакритика различает.

  references  В китайском это слова из тех же иероглифов. Организующий принцип
              иврита — трёхбуквенный корень, и слова одного корня связаны и по
              смыслу, и по written form. Берём их по общей лемме, которая уже
              посчитана отдельной стадией конвейера для всех слов.

Формат повторяет китайский, чтобы карточка и фильтрация [#N] работали как есть.
Разметка [#N] важна: card_builder прячет ссылки на слова, до которых учащийся
ещё не дошёл, — иначе подсказка забегала бы вперёд.

Использование
-------------
    python build_hebrew_extras.py            # показать, что получится
    python build_hebrew_extras.py --apply    # записать в словарь
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import shutil
import unicodedata

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hebrew_freq")
FULL = os.path.join(HERE, "hebrew_freq_10000_full.json")
HOMOGRAPHS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "homographs.json")

# Сколько однокоренных показывать максимум — длинный список на карточке бесполезен.
MAX_REFS = 12


def strip_niqqud(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text or "")
                   if unicodedata.category(c) != "Mn")


def build_tones(entry: dict) -> str:
    """Варианты огласовки одних и тех же согласных — аналог тонов."""
    readings = entry["readings"]
    lines = [f"<b>{entry['hebrew']}</b>: <i>вариантов огласовки: {len(readings)}</i>"]
    for r in readings:
        lines.append(f" - <b>{r['niqqud']}</b> [{r['ipa']}]: {r['sense']}")
    return "\n".join(lines)


def build_references(row: dict, family: list[dict]) -> str:
    """Слова того же корня, кроме самого слова."""
    others = [w for w in family if w["rank"] != row["rank"]][:MAX_REFS]
    if not others:
        return ""
    lines = [f"<b>{row['lemma']}</b>: <i>слов с этой основой: {len(others)}</i>"]
    for w in others:
        form = (w.get("niqqud") or "").strip() or w["hebrew"]
        sense = (w.get("russian") or "").split("\n")[0]
        lines.append(f"<i>[#{w['rank']}]</i>{form} [{w.get('ipa','')}] {sense}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="записать в словарь")
    args = ap.parse_args()

    rows = json.load(open(FULL, encoding="utf-8"))
    by_rank = {r["rank"]: r for r in rows}
    homographs = json.load(open(HOMOGRAPHS, encoding="utf-8"))

    # ── tones: варианты огласовки ────────────────────────────────────────────
    tones_set = 0
    for entry in homographs:
        row = by_rank.get(entry["rank"])
        if row is None or row["hebrew"] != entry["hebrew"]:
            continue
        row["_tones"] = build_tones(entry)
        tones_set += 1

    # ── references: однокоренные по лемме ────────────────────────────────────
    families: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        lemma = (r.get("lemma") or "").strip()
        if lemma:
            families[lemma].append(r)

    refs_set = 0
    for r in rows:
        lemma = (r.get("lemma") or "").strip()
        fam = families.get(lemma, [])
        if len(fam) < 2:
            continue
        text = build_references(r, sorted(fam, key=lambda w: w["rank"]))
        if text:
            r["_references"] = text
            refs_set += 1

    sizes = collections.Counter(len(v) for v in families.values() if len(v) > 1)
    print(f"слов в словаре: {len(rows)}")
    print(f"  варианты огласовки (tones):      {tones_set}")
    print(f"  однокоренные (references):       {refs_set}")
    print(f"  семей с общей основой:           {sum(1 for v in families.values() if len(v) > 1)}")
    print(f"  крупнейшие семьи: {sorted(sizes.items(), reverse=True)[:5]}")

    example = next((r for r in rows if r.get("_references")), None)
    if example:
        print(f"\nпример однокоренных для {example['hebrew']} (основа {example['lemma']}):")
        for line in example["_references"].split("\n")[:5]:
            print("   ", line)
    example_t = next((r for r in rows if r.get("_tones")), None)
    if example_t:
        print(f"\nпример вариантов огласовки для {example_t['hebrew']}:")
        for line in example_t["_tones"].split("\n"):
            print("   ", line)

    if not args.apply:
        print("\nпробный прогон. Чтобы записать — запустите с --apply")
        return 0

    shutil.copy2(FULL, FULL + ".bak")
    for r in rows:
        r["tones"] = r.pop("_tones", "")
        r["references"] = r.pop("_references", "")
    with open(FULL, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2)
    print(f"\nзаписано в {os.path.basename(FULL)} (бэкап: .bak)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
