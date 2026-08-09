#!/usr/bin/env python3
"""
Применение подтверждённых правок к словарю — с проверкой каждой на допустимость.

Почему не применять напрямую
----------------------------
Правки приходят от проверяющих (агентов или человека), а проверяющий ошибается.
В прошлый раз валидатор поймал предложение קלטת -> קַסֶּטֶת: согласная ל заменена
на ס, то есть вместо огласовки подставлено ДРУГОЕ СЛОВО. Такая правка выглядит
безобидно в списке из четырёхсот строк и незаметно портит словарь. Поэтому здесь
каждая правка проходит проверку по своему полю, а отвергнутые печатаются с
причиной — их разбирают руками, а не молча теряют.

Что проверяется
---------------
    niqqud    снятие огласовки обязано вернуть исходное написание;
              допустима разница по вав/йод (ktiv male/haser)
    pos       только из принятого набора сокращений
    ipa       непустая строка без ивритских букв (частая ошибка — вписать туда
              огласовку)
    russian   непустая строка без ивритских букв
    tones     ивритский текст, каждая строка варианта содержит огласовку
    lemma     ивритское слово без огласовки

Использование
-------------
    python apply_review.py правки.json           # проверить, ничего не менять
    python apply_review.py правки.json --apply   # записать в словарь
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import unicodedata

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hebrew_freq")
FULL = os.path.join(HERE, "hebrew_freq_10000_full.json")

MATRES = "וי"
POS_OK = {"сущ", "глаг", "прил", "нареч", "мест", "предл",
          "союз", "межд", "част", "числ", "имя"}
HEBREW = tuple(chr(c) for c in range(0x05D0, 0x05EB))


def strip_niqqud(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text or "")
                   if unicodedata.category(c) != "Mn")


def skeleton(text: str) -> str:
    return "".join(c for c in strip_niqqud(text) if c not in MATRES and c not in "\"'־ ")


def has_niqqud(text: str) -> bool:
    return any(unicodedata.category(c) == "Mn"
               for c in unicodedata.normalize("NFD", text or ""))


def has_hebrew(text: str) -> bool:
    return any(c in HEBREW for c in (text or ""))


def check(row: dict, field: str, value: str) -> tuple[bool, str]:
    """Допустима ли правка. Возвращает (можно, причина отказа)."""
    value = (value or "").strip()
    if not value:
        return False, "пустое значение"

    if field == "niqqud":
        if not has_niqqud(value):
            return False, "огласовки нет вовсе"
        want, got = row["hebrew"], strip_niqqud(value)
        if got == want:
            return True, ""
        if skeleton(got) == skeleton(want):
            return True, "разница вав/йод (ktiv male/haser) — допустима"
        return False, f"согласные разошлись: {want} vs {got}"

    if field == "pos":
        return (value in POS_OK, "" if value in POS_OK else f"часть речи вне набора: {value}")

    if field in ("ipa", "translit_ru", "russian"):
        if has_hebrew(value):
            return False, "в поле попал ивритский текст"
        return True, ""

    if field == "lemma":
        if not has_hebrew(value):
            return False, "лемма без ивритских букв"
        if has_niqqud(value):
            return False, "лемма хранится без огласовки"
        return True, ""

    if field == "tones":
        if not has_hebrew(value):
            return False, "варианты огласовки без ивритского текста"
        variants = [l for l in value.split("\n") if l.strip().startswith("-")]
        if len(variants) < 2:
            return False, "меньше двух вариантов — нечего показывать"
        if not all(has_niqqud(l) for l in variants):
            return False, "не у всех вариантов есть огласовка"
        return True, ""

    return False, f"неизвестное поле: {field}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edits", help="JSON со списком правок: rank, hebrew, field, proposed")
    ap.add_argument("--apply", action="store_true", help="записать изменения")
    ap.add_argument("--show", type=int, default=25, help="сколько правок показать")
    args = ap.parse_args()

    edits = json.load(open(args.edits, encoding="utf-8"))
    if isinstance(edits, dict):
        edits = edits.get("confirmed") or edits.get("edits") or []
    rows = json.load(open(FULL, encoding="utf-8"))
    by_rank = {r["rank"]: r for r in rows}

    ok, rejected, noop = [], [], []
    for e in edits:
        row = by_rank.get(e["rank"])
        if row is None:
            rejected.append((e, "ранга нет в словаре"))
            continue
        if row["hebrew"] != e.get("hebrew", row["hebrew"]):
            rejected.append((e, f"слово не совпало: в словаре {row['hebrew']}"))
            continue
        field, value = e["field"], (e.get("proposed") or "").strip()
        if (row.get(field) or "") == value:
            noop.append(e)
            continue
        good, why = check(row, field, value)
        (ok if good else rejected).append((e, why))

    print(f"правок на входе: {len(edits)}")
    print(f"  принято:     {len(ok)}")
    print(f"  уже так:     {len(noop)}")
    print(f"  ОТКЛОНЕНО:   {len(rejected)}")

    by_field: dict[str, int] = {}
    for e, _ in ok:
        by_field[e["field"]] = by_field.get(e["field"], 0) + 1
    if by_field:
        print("\nпринято по полям:")
        for f, n in sorted(by_field.items()):
            print(f"  {f:12} {n}")

    if rejected:
        print("\nОТКЛОНЕНО — разобрать руками:")
        for e, why in rejected[:args.show]:
            print(f"  №{e.get('rank'):5} {e.get('hebrew','?'):10} {e.get('field','?'):10} "
                  f"-> {str(e.get('proposed'))[:40]!r} — {why}")
        if len(rejected) > args.show:
            print(f"  … и ещё {len(rejected) - args.show}")

    if ok:
        print(f"\nпримеры принятых (до {args.show}):")
        for e, note in ok[:args.show]:
            row = by_rank[e["rank"]]
            print(f"  №{e['rank']:5} {e['hebrew']:10} {e['field']:10} "
                  f"{str(row.get(e['field']) or '')[:28]!r} -> {str(e['proposed'])[:38]!r}"
                  + (f"  ({note})" if note else ""))

    if not args.apply:
        print("\nпробный прогон. Чтобы записать — запустите с --apply")
        return 0

    if not ok:
        print("\nнечего применять")
        return 0

    shutil.copy2(FULL, FULL + ".bak")
    for e, _ in ok:
        by_rank[e["rank"]][e["field"]] = e["proposed"].strip()
    with open(FULL, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2)
    print(f"\nзаписано в {os.path.basename(FULL)}: {len(ok)} правок (бэкап: .bak)")
    print("дальше: python sync_hebrew.py --apply — донести до базы")
    return 0


if __name__ == "__main__":
    sys.exit(main())
