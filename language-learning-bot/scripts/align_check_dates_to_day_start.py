#!/usr/bin/env python
"""
Сдвигает даты следующей проверки на границу учебных суток человека.

Откуда взялось
--------------
09.10.2026 границу суток вынесли в настройки, и новые даты следующей проверки
стали ложиться на неё: у владельца Europe/Moscow и начало суток в 4 утра,
то есть 01:00 UTC. А уже накопленные даты остались на полуночи UTC — так их
писал прежний код.

Чем это кончилось. Полночь UTC — это 03:00 по Москве, то есть ПОСЛЕДНИЙ час
предыдущих учебных суток. Слово со старой датой становилось нужным в три часа
ночи и через час, с началом новых суток, объявлялось просроченным. Наутро
владелец видел «53 слова недопройдено», пройдя накануне всё.

Что делает
----------
Старое значение «полночь UTC дня D» означало «повторить в день D». Новое
значение того же — «начало учебных суток дня D» по настройкам этого человека.
Этот скрипт так и пересчитывает, для каждого человека по его настройкам.

Записи, уже лежащие на границе, не трогаются. Людям с настройками по
умолчанию (UTC, 0) граница и есть полночь — у них не меняется ничего.

Без аргументов — только показать. Меняет только с --apply.
"""

import argparse
import asyncio
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from common.study_day import day_started_utc, settings_of, study_day

load_dotenv(ROOT / "backend" / ".env")
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:8527")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "language_learning_bot")


async def settings_for(db, user_id, language_id) -> dict:
    from bson import ObjectId

    try:
        doc = await db.user_language_settings.find_one(
            {"user_id": ObjectId(str(user_id)), "language_id": ObjectId(str(language_id))})
        return doc or {}
    except Exception:
        return {}


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="действительно сдвинуть даты")
    ap.add_argument("--show", type=int, default=10, help="сколько примеров показать")
    args = ap.parse_args()

    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGODB_DB_NAME]

    pairs = set()
    async for d in db.user_statistics.find({}, {"user_id": 1, "language_id": 1}):
        pairs.add((d.get("user_id"), d.get("language_id")))

    total, moved, examples = 0, 0, []
    for user_id, language_id in sorted(pairs, key=str):
        settings = await settings_for(db, user_id, language_id)
        tz_name, day_start = settings_of(settings)
        if tz_name == "UTC" and day_start == 0:
            continue                     # граница и есть полночь — двигать нечего

        async for doc in db.user_statistics.find(
                {"user_id": user_id, "language_id": language_id,
                 "next_check_date": {"$ne": None}}):
            old = doc["next_check_date"]
            if not isinstance(old, datetime):
                continue
            total += 1
            # Старое значение означало «повторить в день D», где D — его дата.
            want = day_started_utc(old.date(), tz_name, day_start)
            if want == old:
                continue
            moved += 1
            if len(examples) < args.show:
                examples.append((doc.get("word_id", "")[-6:], old, want, tz_name, day_start))
            if args.apply:
                await db.user_statistics.update_one(
                    {"_id": doc["_id"]}, {"$set": {"next_check_date": want}})

    if args.apply and moved:
        # «Недопройдено» в сегодняшнем снимке выведено из дат, которые мы
        # только что сдвинули. Без пересчёта график до вечера показывает
        # прежнее число: у владельца живой показатель стал 0, а на графике
        # висело 53.
        from datetime import datetime as _dt
        for user_id, language_id in sorted(pairs, key=str):
            settings = await settings_for(db, user_id, language_id)
            tz_name, day_start = settings_of(settings)
            if tz_name == "UTC" and day_start == 0:
                continue
            today = study_day(_dt.utcnow(), tz_name, day_start)
            boundary = day_started_utc(today, tz_name, day_start)
            overdue = await db.user_statistics.count_documents({
                "user_id": user_id, "language_id": language_id,
                "next_check_date": {"$lt": boundary},
                "score": 1, "is_skipped": {"$ne": True}})
            res = await db.user_daily_statistics.update_one(
                {"user_id": user_id, "language_id": language_id, "type": "daily",
                 "date": _dt.combine(today, _dt.min.time())},
                {"$set": {"words_overdue": overdue}})
            if res.modified_count:
                print(f"  снимок за {today}: «недопройдено» -> {overdue}")

    print(f"дат просмотрено: {total}, не на границе: {moved}")
    for wid, old, want, tz_name, hour in examples:
        print(f"  слово …{wid}: {old} -> {want}   ({tz_name}, начало суток {hour})")

    if moved and not args.apply:
        print(f"\nэто только показ. Чтобы сдвинуть {moved} дат — запустите с --apply")
    elif args.apply:
        print(f"\nсдвинуто: {moved}")

    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
