#!/usr/bin/env python3
"""
Слияние результатов агентской проверки иврита в hebrew_freq_10000_full.json.

Стадии проверки шли партиями по 400 слов, каждая клала JSON в свой каталог:
  niqrev_out/qout_NN_диапазон.json  — ревизия огласовки  {rank, hebrew, niqqud, changed}
  ru_out/rout_NN_диапазон.json      — проверка перевода  {rank, hebrew, russian, changed}

Скрипт идемпотентен: повторный запуск ничего не портит.

Зачем валидация огласовки
-------------------------
Огласовка (никуд) — это диакритика поверх согласных, она НЕ должна менять
буквенный состав слова. Если снять все знаки с предложенной огласовки, должно
получиться исходное слово. Расхождение означает, что проверяющий подменил слово,
а не огласовал его.

Реальный пример из данных: для קלטת («кассета») предложено קַסֶּטֶת — согласная
ל заменена на ס. Это другое слово, а не огласовка исходного.

Исключение — ktiv male/haser: неогласованное письмо часто содержит вав и йод
как матери чтения, а огласованное их опускает. Разница только по ו/י допустима.

Использование
-------------
    python merge_reviews.py            # проверить и показать, что будет сделано
    python merge_reviews.py --apply    # записать изменения в full.json
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import unicodedata
from typing import Any

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "data", "hebrew_freq")
FULL = os.path.join(HERE, "hebrew_freq_10000_full.json")

MATRES = "וי"  # вав и йод — матери чтения


def strip_niqqud(text: str) -> str:
    """Снять диакритику, оставить только согласные."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def skeleton(text: str) -> str:
    """Согласные без матерей чтения и знаков препинания — для сравнения ktiv male/haser."""
    return "".join(c for c in strip_niqqud(text) if c not in MATRES and c not in "\"'")


def niqqud_matches(hebrew: str, niqqud: str) -> tuple[bool, str]:
    """
    Проверить, что огласовка относится к тому же слову.
    Возвращает (годна, причина).
    """
    bare = strip_niqqud(niqqud)
    if bare == hebrew:
        return True, "exact"
    if skeleton(bare) == skeleton(hebrew):
        return True, "ktiv"  # разница только по вав/йод
    return False, f"согласные разошлись: {hebrew} vs {bare}"


def load_reviews(pattern: str, field: str) -> dict[int, dict[str, Any]]:
    """Собрать записи всех партий стадии в {rank: запись}, оставляя только changed."""
    out: dict[int, dict[str, Any]] = {}
    for path in sorted(glob.glob(os.path.join(HERE, pattern))):
        for rec in json.load(open(path, encoding="utf-8")):
            if rec.get("changed") and field in rec:
                rec["_src"] = os.path.basename(path)
                out[rec["rank"]] = rec
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="записать изменения (без флага — только показать)")
    args = ap.parse_args()

    words = json.load(open(FULL, encoding="utf-8"))
    by_rank = {w["rank"]: w for w in words}
    print(f"словарь: {len(words)} слов\n")

    niq = load_reviews("niqrev_out/*.json", "niqqud")
    ru = load_reviews("ru_out/*.json", "russian")
    print(f"правок из ревизии огласовки: {len(niq)}")
    print(f"правок из проверки перевода: {len(ru)}\n")

    applied_niq = skipped_niq = already_niq = 0
    rejected: list[str] = []

    for rank, rec in sorted(niq.items()):
        word = by_rank.get(rank)
        if word is None:
            rejected.append(f"ранг {rank}: нет такого слова в словаре")
            skipped_niq += 1
            continue
        ok, why = niqqud_matches(rec["hebrew"], rec["niqqud"])
        if not ok:
            rejected.append(
                f"ранг {rank} ({rec['_src']}): {rec['hebrew']} -> {rec['niqqud']} — {why}")
            skipped_niq += 1
            continue
        if word.get("niqqud") == rec["niqqud"]:
            already_niq += 1
            continue
        word["niqqud"] = rec["niqqud"]
        applied_niq += 1

    # Пометка, которой apply_homographs.py дописывает другие чтения слова.
    HOMOGRAPH_MARK = "⚠ то же написание читается иначе:"

    applied_ru = already_ru = kept_homograph = 0
    for rank, rec in sorted(ru.items()):
        word = by_rank.get(rank)
        if word is None:
            continue
        if word.get("russian") == rec["russian"]:
            already_ru += 1
            continue
        # У омографов перевод собран вручную и перечисляет несколько чтений.
        # Стадия ru_out делалась до этого и хранит однострочную версию —
        # применив её, мы бы молча откатили разбор омографов.
        if HOMOGRAPH_MARK in (word.get("russian") or ""):
            kept_homograph += 1
            continue
        word["russian"] = rec["russian"]
        applied_ru += 1

    print("огласовка:")
    print(f"  уже было применено ранее: {already_niq}")
    print(f"  применяется сейчас:       {applied_niq}")
    print(f"  ОТКЛОНЕНО валидацией:     {skipped_niq}")
    print("перевод:")
    print(f"  уже было применено ранее: {already_ru}")
    print(f"  применяется сейчас:       {applied_ru}")
    if kept_homograph:
        print(f"  сохранено разборов омографов: {kept_homograph}")

    if rejected:
        print("\nотклонённые правки — проверить вручную:")
        for line in rejected:
            print(f"  {line}")

    # Сплошная проверка словаря, а не только изменённых записей.
    broken = [
        w for w in words
        if w.get("niqqud") and not niqqud_matches(w["hebrew"], w["niqqud"])[0]
    ]
    print(f"\nсплошная проверка словаря: записей с несовпадением согласных — {len(broken)}")
    for w in broken[:20]:
        print(f"  ранг {w['rank']:5} {w['hebrew']:14} {w['niqqud']}")
    if len(broken) > 20:
        print(f"  ... и ещё {len(broken) - 20}")

    if not args.apply:
        print("\nпробный прогон. Чтобы записать — запустите с --apply")
        return 0

    if applied_niq or applied_ru:
        shutil.copy2(FULL, FULL + ".bak")
        with open(FULL, "w", encoding="utf-8") as fh:
            json.dump(words, fh, ensure_ascii=False, indent=2)
        print(f"\nзаписано в {os.path.basename(FULL)} (бэкап: .bak)")
    else:
        print("\nнечего применять — файл не тронут")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
