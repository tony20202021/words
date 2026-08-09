#!/usr/bin/env python3
"""
Знак ударения внутри слогового начала — починка системной ошибки генератора.

Что не так
----------
В части записей знак ударения стоит ПОСЛЕ гортанной смычки: ʔˈet, ʔˈaʁba,
haʔˈaʁets. В IPA знак ставится перед началом ударного слога целиком, а не между
согласной и гласной внутри него, так что запись просто невалидна: ʔ и следующая
гласная принадлежат одному слогу.

Ошибка не разовая — она одинаковая у всех задетых слов, то есть родилась в
генераторе транскрипции, а не при ручной правке. Нашлась при сверке первой
тысячи с Викисловарём, но встречается по всему словарю.

Как чиним
---------
    многосложные   знак переносится перед смычкой:  ʔˈaʁba -> ˈʔaʁba
                   ударение подтверждается русской транслитерацией (Арба)
    односложные    знак снимается: в слове с одним гласным он не несёт
                   информации, а в ранней части словаря его и не ставят (ʔim,
                   ʔal, ʔaz)

Использование
-------------
    python fix_ipa_stress.py            # показать, что изменится
    python fix_ipa_stress.py --apply    # записать
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hebrew_freq")
FULL = os.path.join(HERE, "hebrew_freq_10000_full.json")

# Гортанные, после которых знак и оказывался: алеф/айин.
BAD = re.compile(r"([ʔʕ])ˈ")
VOWELS = "aeiouɛəɔæ"


def syllables(ipa: str) -> int:
    """Слогов примерно столько же, сколько гласных — для нашей записи этого хватает."""
    return sum(1 for c in ipa if c in VOWELS)


def fixed(ipa: str) -> str:
    without = BAD.sub(r"\1", ipa)
    if syllables(without) <= 1:
        return without
    # Перенести знак перед гортанной вместе со всем началом слога нельзя
    # механически, но для наших случаев началом слога является сама гортанная.
    return BAD.sub(r"ˈ\1", ipa)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="записать изменения")
    args = ap.parse_args()

    rows = json.load(open(FULL, encoding="utf-8"))
    hits = [r for r in rows if BAD.search(r.get("ipa") or "")]

    print(f"слов в словаре: {len(rows)}")
    print(f"знак ударения внутри слогового начала: {len(hits)}\n")
    for r in hits:
        new = fixed(r["ipa"])
        kind = "односложное, знак снят" if syllables(new) <= 1 else "знак перенесён"
        print(f"  №{r['rank']:5} {r['hebrew']:10} {r['ipa']!r:16} -> {new!r:16} "
              f"({kind}; транслитерация {r.get('translit_ru','')!r})")

    if not hits:
        return 0
    if not args.apply:
        print("\nпробный прогон. Чтобы записать — запустите с --apply")
        return 0

    shutil.copy2(FULL, FULL + ".bak")
    for r in hits:
        r["ipa"] = fixed(r["ipa"])
    with open(FULL, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2)
    print(f"\nисправлено: {len(hits)} (бэкап: .bak)")
    print("дальше: python sync_hebrew.py --apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
