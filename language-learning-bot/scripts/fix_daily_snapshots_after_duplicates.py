#!/usr/bin/env python
"""
Убирает из дневных снимков след от задвоенных записей слов.

Откуда взялось
--------------
30.09.2026 в 20:02 офлайн-отправки создали 27 лишних записей `user_statistics`
(одно слово — две записи). 08.10.2026 в 20:34 их удалили, но дневные снимки,
снятые между этими датами, уже посчитали их как настоящие слова. На графиках
это видно как горб и обрыв: «изучено» росло 131 → 178 → 262, а 09.10 упало до
236, хотя слов не убавлялось.

Снимок пишется ОДИН раз в сутки и потом не трогается, поэтому сам он не
починится. Удалять снимки нельзя: «новых слов за день» и «не знаю на последнем
проходе» считаются как разница между соседними днями, и дыра в ряду дала бы
ложный скачок у соседей.

Как считается поправка
----------------------
Точно, а не на глаз. В копии удалённых записей (backups/user_statistics_
duplicates_*.json) есть у каждой дата создания, счёт, пометка пропуска и дата
следующей проверки, и ни одна из них после создания не менялась. Значит, для
любого дня можно пересчитать, сколько они добавляли к каждому полю — ровно по
тем же условиям, по которым считает агрегация бэкенда.

Правится только окно, когда дубли существовали: снимки с 01.10 по 08.10.
Снимок за 30.09 снят утром, до их появления, за 09.10 — после удаления.

Без аргументов — только показать. Меняет с --apply, сделав копию снимков.
"""

import argparse
import asyncio
import collections
import glob
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dateutil import parser as dateparser
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(ROOT / "backend" / ".env")
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:8527")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "language_learning_bot")

# Окно, когда дубли существовали в базе.
BORN = datetime(2026, 9, 30, 20, 2, 58)
KILLED = datetime(2026, 10, 8, 20, 34, 36)


def deleted_duplicates() -> list[dict]:
    """Лишние записи из копии: в каждой группе оставляли самую свежую."""
    files = sorted(glob.glob(str(ROOT / "backups" / "user_statistics_duplicates_*.json")))
    if not files:
        sys.exit("нет копии удалённых записей в backups/")
    docs = json.load(open(files[-1], encoding="utf-8"))
    groups = collections.defaultdict(list)
    for d in docs:
        groups[(d["user_id"], d["word_id"])].append(d)
    removed = []
    for group in groups.values():
        group.sort(key=lambda d: (d.get("updated_at") or "", str(d["_id"])))
        removed += group[:-1]
    # Две записи 2025 года жили всегда и к этому окну отношения не имеют.
    return [d for d in removed
            if dateparser.parse(str(d["created_at"])).replace(tzinfo=None) >= BORN]


def when(doc: dict, field: str) -> datetime:
    value = doc.get(field)
    return dateparser.parse(str(value)).replace(tzinfo=None) if value else datetime.max


def contribution(dups: list[dict], midnight: datetime) -> dict:
    """Сколько дубли добавляли к полям снимка на эту дату."""
    return {
        "words_studied": len(dups),
        "words_known": sum(1 for d in dups if d.get("score") == 1),
        "words_unknown_now": sum(1 for d in dups
                                 if d.get("score") == 0 and not d.get("is_skipped")),
        "words_for_today": sum(1 for d in dups if when(d, "next_check_date") <= midnight),
        "words_overdue": sum(1 for d in dups
                             if when(d, "next_check_date") < midnight
                             and d.get("score") == 1 and not d.get("is_skipped")),
    }


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="записать поправку")
    args = ap.parse_args()

    dups = deleted_duplicates()
    print(f"дублей в окне: {len(dups)}, появились {BORN}, удалены {KILLED}")

    db = AsyncIOMotorClient(MONGODB_URL)[MONGODB_DB_NAME]
    user_ids = {d["user_id"] for d in dups}

    touched, backup = 0, []
    async for snap in db.user_daily_statistics.find({"type": "daily"}).sort("date", 1):
        day = snap.get("date")
        if not isinstance(day, datetime) or snap.get("user_id") not in user_ids:
            continue
        # Снимок снимается утром: учитываем только дни, целиком лежащие внутри
        # окна. 30.09 снят до появления дублей, 09.10 — уже после удаления.
        if not (BORN < day < KILLED):
            continue
        midnight = datetime(day.year, day.month, day.day)
        delta = contribution(dups, midnight)
        changes = {k: (snap.get(k) or 0) - v for k, v in delta.items() if v}
        if not changes:
            continue
        touched += 1
        print(f"  {str(day)[:10]}: " + ", ".join(
            f"{k.replace('words_', '')} {snap.get(k)} -> {v}" for k, v in changes.items()))
        if any(v < 0 for v in changes.values()):
            sys.exit(f"  ОСТАНОВЛЕНО: на {str(day)[:10]} поправка уводит в минус — "
                     "значит, окно определено неверно, и трогать нельзя")
        backup.append(snap)
        if args.apply:
            await db.user_daily_statistics.update_one({"_id": snap["_id"]}, {"$set": changes})

    print(f"\nснимков затронуто: {touched}")
    if touched and args.apply:
        out = ROOT / "backups"
        out.mkdir(exist_ok=True)
        path = out / f"daily_snapshots_before_fix_{datetime.now():%Y%m%d_%H%M%S}.json"
        path.write_text(json.dumps(backup, default=str, ensure_ascii=False, indent=1))
        print(f"копия прежних снимков: {path}")
    elif touched:
        print("это только показ. Чтобы записать — запустите с --apply")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
