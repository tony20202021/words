#!/usr/bin/env python3
"""Заполняет word_foreign_simple — форму без огласовки, как пишут в жизни.

ЗАЧЕМ ОТДЕЛЬНОЕ ПОЛЕ, А НЕ ЗАМЕНА. Владелец: «реальные тексты без огласовок,
нужен промежуточный этап — огласовка включается нажатием». Значит на карточке
нужны ОБЕ формы, и вопрос лишь в том, какая где лежит.

word_foreign остаётся огласованной, и это не осторожность, а необходимость: на
(language_id, word_foreign) стоит УНИКАЛЬНЫЙ индекс, а огласовка — единственное,
что различает омографы. Без неё слипаются לְךָ/לָךְ (№11 и №9514) и דֶּן/דָּן
(№1620 и №7518): запись упёрлась бы в индекс, а он отказывает молча — ровно так
08.11.2026 «успешно» не загрузился словарь английского. Скрипт эти две пары
проверяет и печатает: если слипшихся пар станет больше, это видно сразу.

ПОЛЕ ОБЩЕЕ ДЛЯ ЯЗЫКОВ. Общее тут не «огласовка», а уровень подсказки в
написании: иврит огласовка -> без огласовки, арабский харакат -> без харакат,
японский фуригана -> голые кандзи. Для английского поле остаётся пустым, и
иконки переключения на карточке просто не будет.

Запуск:  python words/hebrew_tools/fill_simple_form.py [--apply]
"""
import argparse
import asyncio
import collections
import os
import re
import sys
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

URL = os.getenv("MONGODB_URL", "mongodb://localhost:8527")
DB_NAME = os.getenv("MONGODB_DB_NAME", "language_learning_bot")
NAME_RU = "Иврит"

# Диакритика иврита: огласовки (U+05B0–U+05BD, U+05C1…) и знаки кантилляции.
ОГЛАСОВКИ = re.compile("[֑-ׇ]")

# Пары, которые различаются ТОЛЬКО огласовкой. Их и печатаем: пока их две,
# замена word_foreign на неогласованную форму ломает ровно две записи, и это
# знание должно быть видно глазами, а не выводиться заново каждый раз.
ИЗВЕСТНЫЕ_ОМОГРАФЫ = [(11, 9514), (1620, 7518)]


def без_огласовок(текст: str) -> str:
    return ОГЛАСОВКИ.sub("", текст or "").strip()


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="записать изменения")
    ap.add_argument("--language", default=NAME_RU)
    args = ap.parse_args()

    db = AsyncIOMotorClient(URL)[DB_NAME]
    lang = await db.languages.find_one({"name_ru": args.language})
    if not lang:
        print(f"языка {args.language!r} в базе нет")
        return 1

    слова = await db.words.find(
        {"language_id": lang["_id"]},
        {"word_number": 1, "word_foreign": 1, "word_foreign_simple": 1},
    ).to_list(length=None)
    слова.sort(key=lambda w: w.get("word_number", 0))
    print(f"слов в языке: {len(слова)}")

    по_номеру = {w.get("word_number"): w for w in слова}
    простые = collections.defaultdict(list)
    к_записи = []
    без_изменений = совпадает = 0

    for w in слова:
        простая = без_огласовок(w.get("word_foreign", ""))
        if not простая:
            continue
        простые[простая].append(w.get("word_number"))
        if простая == (w.get("word_foreign") or "").strip():
            # Огласовки в слове нет вовсе — формы совпадают. Поле всё равно
            # заполняем: пустое поле клиент не отличит от «языку это не нужно».
            совпадает += 1
        if w.get("word_foreign_simple") == простая:
            без_изменений += 1
            continue
        к_записи.append((w["_id"], простая))

    слипшиеся = {ф: ns for ф, ns in простые.items() if len(ns) > 1}
    print(f"у формы без огласовки совпадений: {len(слипшиеся)} написаний "
          f"на {sum(len(ns) for ns in слипшиеся.values())} слов")
    print("  ПОЭТОМУ word_foreign и остаётся огласованным: вот эти слова "
          "различает только огласовка")
    for ф, ns in sorted(слипшиеся.items(), key=lambda kv: kv[1][0])[:20]:
        формы = ", ".join(f"{по_номеру[n]['word_foreign']}#{n}" for n in ns)
        print(f"    {ф:<12} -> {формы}")

    for a, b in ИЗВЕСТНЫЕ_ОМОГРАФЫ:
        wa, wb = по_номеру.get(a), по_номеру.get(b)
        если = "ОК" if wa and wb else "НЕТ В БАЗЕ"
        if wa and wb:
            одна = без_огласовок(wa["word_foreign"]) == без_огласовок(wb["word_foreign"])
            если = "сливаются" if одна else "РАЗОШЛИСЬ — проверьте"
        print(f"  известная пара #{a}/#{b}: {если}")

    print(f"формы совпадают с огласованной: {совпадает}")
    print(f"уже заполнено верно: {без_изменений}")
    print(f"к записи: {len(к_записи)}")
    for _id, простая in к_записи[:5]:
        print(f"    пример: {простая}")

    if not args.apply:
        print("\n[без --apply] не записано")
        return 0

    from pymongo import UpdateOne
    сейчас = datetime.now(timezone.utc)
    пачка = [UpdateOne({"_id": _id},
                       {"$set": {"word_foreign_simple": простая, "updated_at": сейчас}})
             for _id, простая in к_записи]
    if пачка:
        итог = await db.words.bulk_write(пачка, ordered=False)
        print(f"\nзаписано: {итог.modified_count}")
    else:
        print("\nнечего записывать")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
