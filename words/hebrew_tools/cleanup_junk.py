#!/usr/bin/env python3
"""
Чистка мусора частотного списка: починить испорченное, удалить не-слова.

Откуда мусор
------------
Список he_50k.txt собран автоматически из субтитров, и в него попали куски слов
и артефакты разбора. В словаре они выглядят как обычные записи, но словами не
являются: учащемуся показывают «иль (обрывок слова)» и просят оценить, знает он
это или нет. В интервальном повторении такая запись — чистая потеря времени.

Две разные ситуации
-------------------
FIX     слово настоящее, но потеряна конечная буква: לכ вместо לך, דנ вместо דן.
        В иврите пять букв имеют особую конечную форму, и при нарезке текста их
        легко потерять. Такие записи восстанавливаются.
DELETE  слова нет вовсе: обрывок (יל, הצ, מצ, וצ) или строка задом наперёд (ןכ
        вместо כן). Восстанавливать нечего.

Удаление обратимо: словарь целиком лежит в hebrew_freq_10000_full.json и в git,
а перед записью делается .bak. Перед удалением скрипт проверяет, что запись
никем не изучалась — если по слову есть прогресс, оно не трогается.

Использование
-------------
    python cleanup_junk.py            # показать, что произойдёт
    python cleanup_junk.py --apply    # выполнить
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil

from motor.motor_asyncio import AsyncIOMotorClient

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hebrew_freq")
FULL = os.path.join(HERE, "hebrew_freq_10000_full.json")
URL = os.getenv("MONGODB_URL", "mongodb://localhost:8527")
DB_NAME = os.getenv("MONGODB_DB_NAME", "language_learning_bot")
NAME_RU = "Иврит"

# Потеряна конечная форма буквы — восстанавливаем слово целиком.
FIX = {
    9514: {"hebrew": "לך", "niqqud": "לָךְ", "ipa": "laχ", "translit_ru": "лах",
           "russian": "тебе (ж.р.)", "why": "было לכ — потеряна конечная כ→ך"},
    7518: {"hebrew": "דן", "niqqud": "דָּן", "ipa": "dan", "translit_ru": "дан",
           "russian": "Дэн (имя); судил, обсуждал", "why": "было דנ — потеряна конечная נ→ן"},
}

# Не слова — удаляем.
DELETE = {
    1911: "обрывок слова",
    1977: "обрывок слова",
    6095: "обрывок слова",
    5231: "обрывок от וצא",
    9630: "כן записано задом наперёд",
}


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="выполнить изменения")
    args = ap.parse_args()

    rows = json.load(open(FULL, encoding="utf-8"))
    by_rank = {r["rank"]: r for r in rows}

    db = AsyncIOMotorClient(URL)[DB_NAME]
    lang = await db.languages.find_one({"name_ru": NAME_RU})
    if not lang:
        print(f"язык «{NAME_RU}» не найден")
        return 1
    lang_id = lang["_id"]

    print(f"словарь: {len(rows)} слов\n")

    print("ПОЧИНИТЬ:")
    for rank, fix in FIX.items():
        row = by_rank.get(rank)
        if row is None:
            print(f"  ⛔ ранга {rank} нет в словаре")
            continue
        print(f"  {rank:5} {row['hebrew']:8} -> {fix['hebrew']:8} {fix['niqqud']:10} — {fix['why']}")
        if args.apply:
            row.update({k: v for k, v in fix.items() if k != "why"})

    print("\nУДАЛИТЬ:")
    removable: list[int] = []
    for rank, why in DELETE.items():
        row = by_rank.get(rank)
        if row is None:
            print(f"  ⛔ ранга {rank} нет в словаре")
            continue
        doc = await db.words.find_one({"language_id": lang_id, "word_number": rank})
        studied = 0
        if doc:
            studied = await db.user_statistics.count_documents({"word_id": str(doc["_id"])})
        if studied:
            print(f"  ⏭ {rank:5} {row['hebrew']:8} — изучалось ({studied} записей прогресса), НЕ трогаем")
            continue
        removable.append(rank)
        print(f"  {rank:5} {row['hebrew']:8} — {why}")

    print(f"\nитого: починить {len(FIX)}, удалить {len(removable)}")
    print(f"слов станет: {len(rows) - len(removable)}")

    if not args.apply:
        print("\nпробный прогон. Чтобы выполнить — запустите с --apply")
        return 0

    # Словарь
    shutil.copy2(FULL, FULL + ".bak")
    kept = [r for r in rows if r["rank"] not in removable]
    with open(FULL, "w", encoding="utf-8") as fh:
        json.dump(kept, fh, ensure_ascii=False, indent=2)
    print(f"\nсловарь: {len(kept)} слов (бэкап: .bak)")

    # База: удаление. Починку доводит sync_hebrew.py — он сверяет всё поле целиком.
    res = await db.words.delete_many(
        {"language_id": lang_id, "word_number": {"$in": removable}})
    print(f"удалено из базы: {res.deleted_count}")
    total = await db.words.count_documents({"language_id": lang_id})
    print(f"слов в базе теперь: {total}")
    print("\nдальше: python sync_hebrew.py --apply — донесёт починенные записи")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
