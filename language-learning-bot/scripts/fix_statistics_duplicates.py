#!/usr/bin/env python
"""
Лишние записи статистики: показать и, по отдельной команде, убрать.

Откуда они. Телефон отправляет накопленное офлайн пачкой, и отправок уходит
две сразу. BLS на каждую сначала читал запись, не находил её и просил создать —
обе создавали. 30.09 так появилось несколько десятков лишних записей за одну
секунду. Они врут в счётчиках («слов в корзине» больше, чем слов) и ломали
график интервалов повторения.

Само раздвоение закрыто в backend: создание стало одной операцией
«вставить, если нет», и у коллекции появился индекс единственности пары
«человек + слово». Но индекс не встанет, пока в данных остаются дубли, —
поэтому их надо вычистить один раз.

Что оставляем: запись с самой свежей updated_at (при равенстве — с самым
поздним _id). В ней последнее состояние слова: счёт, интервал, дата проверки.

Без аргументов — только показать. Удаляет только с --apply.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:8527")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "language_learning_bot")


async def find_duplicates(db):
    """Группы «человек + слово», где записей больше одной."""
    pipeline = [
        {"$group": {
            "_id": {"user_id": "$user_id", "word_id": "$word_id"},
            "count": {"$sum": 1},
            "ids": {"$push": "$_id"},
        }},
        {"$match": {"count": {"$gt": 1}}},
    ]
    return [g async for g in db.user_statistics.aggregate(pipeline)]


def _key(doc):
    """Чем свежее запись, тем больше ключ."""
    return (doc.get("updated_at") or doc.get("created_at") or 0, str(doc["_id"]))


async def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="действительно удалить лишние записи")
    ap.add_argument("--index", action="store_true",
                    help="после чистки поставить индекс единственности")
    args = ap.parse_args()

    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGODB_DB_NAME]

    groups = await find_duplicates(db)
    if not groups:
        print("Лишних записей нет.")
    else:
        extra = sum(g["count"] - 1 for g in groups)
        print(f"Слов с лишними записями: {len(groups)}; лишних записей: {extra}\n")

    to_delete = []
    for g in groups:
        docs = [d async for d in db.user_statistics.find({"_id": {"$in": g["ids"]}})]
        docs.sort(key=_key)
        keep, drop = docs[-1], docs[:-1]
        to_delete += [d["_id"] for d in drop]
        print(f"человек {g['_id']['user_id']}  слово {g['_id']['word_id']}")
        for d in docs:
            mark = "ОСТАВИТЬ" if d["_id"] == keep["_id"] else "убрать  "
            print(f"   {mark} _id={d['_id']}  счёт={d.get('score')} "
                  f"интервал={d.get('check_interval')} "
                  f"проверка={d.get('next_check_date')} "
                  f"создана={d.get('created_at')} изменена={d.get('updated_at')}")
        print()

    if to_delete and args.apply:
        # Копия перед удалением: решение «какую запись считать главной»
        # принимает этот скрипт, и если оно окажется неверным, вернуть данные
        # должно быть откуда.
        backup_dir = Path(__file__).parent.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        all_ids = [i for g in groups for i in g["ids"]]
        dump = [d async for d in db.user_statistics.find({"_id": {"$in": all_ids}})]
        path = backup_dir / (
            "user_statistics_duplicates_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        path.write_text(json.dumps(dump, default=str, ensure_ascii=False, indent=1))
        print(f"Копия всех {len(dump)} записей этих слов: {path}\n")

    if to_delete and not args.apply:
        print(f"Это только показ. Удалить {len(to_delete)} записей: "
              f"повторить с --apply")
    elif to_delete:
        res = await db.user_statistics.delete_many({"_id": {"$in": to_delete}})
        print(f"Удалено записей: {res.deleted_count}")
        left = await find_duplicates(db)
        print("Лишних записей осталось:", sum(g["count"] - 1 for g in left))

    if args.index:
        try:
            name = await db.user_statistics.create_index(
                [("user_id", 1), ("word_id", 1)],
                name="user_word_unique_idx", unique=True, background=True)
            print("Индекс единственности поставлен:", name)
        except Exception as e:
            print("Индекс не встал (скорее всего, дубли ещё остались):", e)

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
