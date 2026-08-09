#!/usr/bin/env python3
"""
Слова с несколькими чтениями: показывать все варианты, а не выбирать один.

Проблема, которую это решает
----------------------------
Неогласованное письмо иврита порождает омографы: יצר это и יֵצֶר «инстинкт»,
и יָצַר «создал». В словаре такая запись одна, и получалось хуже всего:
карточка показывала ОДНУ огласовку, а перевод перечислял значения от ОБОИХ
чтений. Учащийся видел יֵצֶר и читал «инстинкт, влечение; создал», хотя יֵצֶר
не значит «создал».

Выбрать одно чтение — значит выбросить второе слово из словаря. Для изучения
правильнее показать оба: омографы это реальная черта языка, и знать их надо.

Как устроено
------------
Основное чтение занимает word_foreign, transcription и перевод — карточка
внутренне непротиворечива. Остальные чтения живут в поле tones, каждое со своей
огласовкой, транскрипцией и значением; заполняет его build_hebrew_extras.py.

Схему БД менять не потребовалось: tones уже есть — оно заводилось под китайский,
где хранит варианты одной транскрипции с разными тонами. У иврита ту же роль
играет огласовка при одинаковых согласных, так что поле подходит по смыслу, а не
только по типу. Все три клиента показывают его как отдельный блок карточки.

Использование
-------------
    python apply_homographs.py           # показать, что изменится
    python apply_homographs.py --apply   # записать в словарь
"""

from __future__ import annotations

import argparse
import json
import os
import shutil

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hebrew_freq")
FULL = os.path.join(HERE, "hebrew_freq_10000_full.json")
# Таблица лежит рядом со скриптом, а не в data/: data/ в gitignore,
# и таблица, собранная руками, туда бы просто не попала в репозиторий.
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "homographs.json")


def build_translation(readings: list[dict]) -> str:
    """
    Перевод только основного чтения.

    Раньше остальные чтения дописывались сюда же строкой с пометкой. Теперь для
    них есть подходящее поле — tones: в китайском оно хранит варианты одной
    транскрипции с разными тонами, а у иврита ту же роль играет огласовка при
    одинаковых согласных. Там они и структурированы, и попадают в отдельный
    блок карточки, и не мешают вариантам ответа в пик-режиме.
    Заполняет его build_hebrew_extras.py.
    """
    return readings[0]["sense"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="записать изменения")
    args = ap.parse_args()

    homographs = json.load(open(SRC, encoding="utf-8"))
    rows = json.load(open(FULL, encoding="utf-8"))
    by_rank = {r["rank"]: r for r in rows}

    changed = missing = mismatch = 0
    for h in homographs:
        row = by_rank.get(h["rank"])
        if row is None:
            print(f"  ⛔ ранга {h['rank']} нет в словаре")
            missing += 1
            continue
        if row["hebrew"] != h["hebrew"]:
            print(f"  ⛔ ранг {h['rank']}: в словаре {row['hebrew']}, в таблице {h['hebrew']}")
            mismatch += 1
            continue

        main = h["readings"][0]
        want_translation = build_translation(h["readings"])
        diffs = []
        if row.get("niqqud") != main["niqqud"]:
            diffs.append(f"огласовка {row.get('niqqud')} -> {main['niqqud']}")
        if row.get("ipa") != main["ipa"]:
            diffs.append(f"ipa {row.get('ipa')} -> {main['ipa']}")
        # Транслитерацию блок --apply пишет, но в diffs её не было: правка,
        # затрагивающая ТОЛЬКО транслитерацию, давала пустой diffs, срабатывал
        # continue, и до записи дело не доходило — молча, без строки в выводе.
        if row.get("translit_ru") != main["translit_ru"]:
            diffs.append(f"транслитерация {row.get('translit_ru')} -> {main['translit_ru']}")
        if (row.get("russian") or "") != want_translation:
            diffs.append(f"перевод: +{len(h['readings']) - 1} вариант(ов)")

        if not diffs:
            continue
        changed += 1
        print(f"  {h['rank']:5} {h['hebrew']:12} " + "; ".join(diffs))

        if args.apply:
            row["niqqud"] = main["niqqud"]
            row["ipa"] = main["ipa"]
            row["translit_ru"] = main["translit_ru"]
            row["russian"] = want_translation

    print(f"\nзаписей с несколькими чтениями: {len(homographs)}")
    print(f"  будет изменено: {changed}")
    if missing or mismatch:
        print(f"  пропущено: нет ранга {missing}, слово не совпало {mismatch}")

    if not args.apply:
        print("\nпробный прогон. Чтобы записать — запустите с --apply")
        return 0

    if changed:
        shutil.copy2(FULL, FULL + ".bak")
        with open(FULL, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=2)
        print(f"\nзаписано в {os.path.basename(FULL)} (бэкап: .bak)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
