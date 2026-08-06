#!/usr/bin/env python3
"""
Синхронизация иврита в MongoDB с hebrew_freq_10000_full.json.

Зачем отдельно от load_hebrew.py
--------------------------------
`load_hebrew.py` — первичная заливка, он только ВСТАВЛЯЕТ и пропускает уже
существующие слова. После правок в словаре (ревизия огласовки, проверка
перевода) он не обновит ничего: все 10000 слов уже в базе.

Этот скрипт наоборот — только ОБНОВЛЯЕТ существующие записи и показывает,
что именно изменится.

Что во что кладётся
-------------------
    word_foreign   <- niqqud, а если огласовки нет — hebrew
    translation    <- russian
    transcription  <- "/{ipa}/\\n{translit_ru}"

В базе слово хранится ОГЛАСОВАННЫМ — именно его видит пользователь.
Неогласованный `hebrew` остаётся только в json как исходник.

Использование
-------------
    python sync_hebrew.py            # показать расхождения, ничего не менять
    python sync_hebrew.py --apply    # записать
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import unicodedata
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "data", "hebrew_freq")
DATA = os.path.join(HERE, "hebrew_freq_10000_full.json")
URL = os.getenv("MONGODB_URL", "mongodb://localhost:8527")
DB_NAME = os.getenv("MONGODB_DB_NAME", "language_learning_bot")
NAME_RU = "Иврит"


def unit_count(text: str | None) -> int | None:
    if not text or not text.strip():
        return None
    text = text.strip()
    if any("一" <= c <= "鿿" for c in text):
        return len(text)
    return len(text.split())


def display_form(row: dict) -> str:
    """Что показывать пользователю: огласованная форма, иначе исходная."""
    niq = (row.get("niqqud") or "").strip()
    return niq or row["hebrew"]


def transcription_of(row: dict) -> str:
    return f"/{row.get('ipa','')}/\n{row.get('translit_ru','')}"


def has_niqqud(text: str) -> bool:
    return any(unicodedata.category(c) == "Mn"
               for c in unicodedata.normalize("NFD", text))


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="записать изменения")
    ap.add_argument("--limit-show", type=int, default=15, help="сколько расхождений показать")
    args = ap.parse_args()

    rows = {r["rank"]: r for r in json.load(open(DATA, encoding="utf-8"))}
    db = AsyncIOMotorClient(URL)[DB_NAME]

    lang = await db.languages.find_one({"name_ru": NAME_RU})
    if not lang:
        print(f"язык «{NAME_RU}» не найден — сначала выполните load_hebrew.py")
        return 1
    lang_id = lang["_id"]
    print(f"язык: {NAME_RU} id={lang_id}")

    total = await db.words.count_documents({"language_id": lang_id})
    print(f"слов в базе: {total}, в словаре: {len(rows)}\n")

    diffs: list[tuple[int, str, str, str]] = []
    missing: list[int] = []
    async for doc in db.words.find({"language_id": lang_id}):
        row = rows.get(doc.get("word_number"))
        if row is None:
            missing.append(doc.get("word_number"))
            continue
        for field, want in (
            ("word_foreign", display_form(row)),
            ("translation", row.get("russian") or ""),
            ("transcription", transcription_of(row)),
        ):
            if (doc.get(field) or "") != want:
                diffs.append((doc["word_number"], field, doc.get(field) or "", want))

    by_field: dict[str, int] = {}
    for _, field, _, _ in diffs:
        by_field[field] = by_field.get(field, 0) + 1

    print("расхождений с базой:")
    for field, n in sorted(by_field.items()):
        print(f"  {field:14} {n}")
    if not diffs:
        print("  нет — база уже соответствует словарю")
    if missing:
        print(f"  слов в базе, которых нет в словаре: {len(missing)}")

    if diffs:
        print(f"\nпримеры (до {args.limit_show}):")
        for rank, field, old, new in diffs[:args.limit_show]:
            print(f"  №{rank:5} {field:14} {old!r:26} -> {new!r}")

    # Отдельно — сколько слов останется без огласовки: это дефекты исходных данных.
    no_niq = [r for r in rows.values() if not has_niqqud(display_form(r))]
    if no_niq:
        print(f"\nбез огласовки останется {len(no_niq)} слов "
              f"(обрывки и междометия из частотного списка):")
        for r in no_niq:
            print(f"  №{r['rank']:5} {r['hebrew']:10} {(r.get('russian') or '')[:36]}")

    if not args.apply:
        print("\nпробный прогон. Чтобы записать — запустите с --apply")
        return 0

    if not diffs:
        print("\nнечего обновлять")
        return 0

    updated = 0
    collisions: list[str] = []
    now = datetime.now(timezone.utc)
    for rank in sorted({d[0] for d in diffs}):
        row = rows[rank]
        form = display_form(row)
        trans = transcription_of(row)
        try:
            res = await db.words.update_one(
                {"language_id": lang_id, "word_number": rank},
                {"$set": {
                    "word_foreign": form,
                    "translation": row.get("russian") or "",
                    "transcription": trans,
                    "word_foreign_unit_count": unit_count(form),
                    "transcription_unit_count": unit_count(trans),
                    "updated_at": now,
                }},
            )
            updated += res.modified_count
        except DuplicateKeyError:
            # На (language_id, word_foreign) висит уникальный индекс. Две записи
            # частотного списка могут схлопнуться в одну огласованную форму —
            # например полное и неполное написание одного слова (הכל / הכול).
            # Это дефект исходных данных: пропускаем и показываем, решать вручную.
            other = await db.words.find_one(
                {"language_id": lang_id, "word_foreign": form},
                {"word_number": 1},
            )
            collisions.append(
                f"№{rank} {row['hebrew']} -> {form} — форма уже занята "
                f"№{other['word_number'] if other else '?'}")

    print(f"\nобновлено записей: {updated}")
    if collisions:
        print(f"пропущено из-за совпадения огласованных форм: {len(collisions)}")
        for line in collisions:
            print(f"  {line}")
        print("  это дубликаты в частотном списке — решить, какой ранг оставить")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
