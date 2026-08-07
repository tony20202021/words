#!/usr/bin/env python3
"""
Сверка огласовки с транскрипцией: гласные должны совпадать.

Зачем это вместо чтения 2800 слов глазами
-----------------------------------------
Ревизия огласовки шла партиями по 400 слов, семь партий остались непроверенными.
Просматривать редкие слова по одному ненадёжно и невоспроизводимо. Но у каждого
слова уже есть IPA, полученный независимо, и огласовка обязана ему соответствовать:
если написано הַמֵּיטָב, то читаться должно ha-mei-tav, а не как-то иначе.

Скрипт вытаскивает последовательность гласных из огласовки и из IPA и сравнивает.
Расхождение — повод посмотреть слово руками; совпадение считаем подтверждением.
Проверка независима от того, кто ставил огласовку, и её можно перезапускать.

Что НЕ ловится
--------------
Ошибку, при которой и огласовка, и IPA неверны одинаково (оба пришли из одного
источника для части слов). И различие дагеша/шва, на звучание гласных не влияющее.

Использование
-------------
    python check_niqqud_vs_ipa.py                # весь словарь
    python check_niqqud_vs_ipa.py --ranges 3601-4000,6801-7200
    python check_niqqud_vs_ipa.py --show 40      # сколько расхождений напечатать
"""

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hebrew_freq")
DATA = os.path.join(HERE, "hebrew_freq_10000_full.json")

# Знак огласовки -> гласный звук. Шва и дагеш звука не дают.
VOWEL = {
    "ַ": "a",   # патах
    "ָ": "a",   # камац
    "ׇ": "o",   # камац катан
    "ֲ": "a",   # хатаф-патах
    "ִ": "i",   # хирик
    "ֵ": "e",   # цере
    "ֶ": "e",   # сегол
    "ֱ": "e",   # хатаф-сегол
    "ֹ": "o",   # холам
    "ֳ": "o",   # хатаф-камац
    "ֻ": "u",   # кубуц
}
DAGESH = "ּ"
SHEVA = "ְ"
VAV, YOD = "ו", "י"


def niqqud_pattern(text: str) -> str:
    """
    Регулярное выражение по последовательности гласных, которую задаёт огласовка.

    Часть знаков читается неоднозначно, и это НЕ ошибка — поэтому вместо точного
    сравнения строим шаблон с допусками:
      шва   — подвижная звучит как «e», немая не звучит вовсе  ->  e?
      камац — обычно «a», в закрытом безударном слоге «o»      ->  [ao]
      хатаф — сверхкраткий, в транскрипции может не отражаться ->  x?
    """
    chars = unicodedata.normalize("NFD", text)
    out: list[str] = []
    i = 0
    while i < len(chars):
        ch = chars[i]
        marks = ""
        j = i + 1
        while j < len(chars) and unicodedata.category(chars[j]) == "Mn":
            marks += chars[j]
            j += 1

        if ch == VAV:
            if "\u05b9" in marks:
                out.append("o")
            elif DAGESH in marks and not any(m in VOWEL for m in marks):
                out.append("u")
            else:
                out.extend(_atom(m) for m in marks if m in VOWEL or m == SHEVA)
        elif ch == YOD and not any(m in VOWEL for m in marks):
            out.extend(_atom(m) for m in marks if m == SHEVA)
        else:
            out.extend(_atom(m) for m in marks if m in VOWEL or m == SHEVA)
        i = j
    return "".join(out)


def _atom(mark: str) -> str:
    if mark == SHEVA:
        return "e?"
    if mark == "\u05b8":          # камац: «a» или «o»
        return "[ao]"
    if mark in ("\u05b2", "\u05b1", "\u05b3"):   # хатафы — сверхкраткие
        return VOWEL[mark] + "?"
    return VOWEL[mark]


def ipa_vowels(ipa: str) -> str:
    """Последовательность гласных из IPA, без ударений и длительности."""
    cleaned = ipa.strip().strip("/").replace("ˈ", "").replace("ˌ", "").replace("ː", "")
    return "".join(c for c in cleaned if c in "aeiou")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ranges", help="диапазоны рангов через запятую, напр. 3601-4000,6801-7200")
    ap.add_argument("--show", type=int, default=30, help="сколько расхождений напечатать")
    ap.add_argument("--json-out", help="сохранить расхождения в файл")
    args = ap.parse_args()

    rows = json.load(open(DATA, encoding="utf-8"))

    if args.ranges:
        spans = []
        for part in args.ranges.split(","):
            a, _, b = part.partition("-")
            spans.append((int(a), int(b or a)))
        rows = [r for r in rows if any(a <= r["rank"] <= b for a, b in spans)]

    ok = mism = skipped = 0
    bad: list[dict] = []
    for r in rows:
        niq, ipa = r.get("niqqud") or "", r.get("ipa") or ""
        if not niq or not ipa:
            skipped += 1
            continue
        nv, iv = niqqud_pattern(niq), ipa_vowels(ipa)
        if not nv and not iv:
            skipped += 1
            continue
        if re.fullmatch(nv, iv):
            ok += 1
        else:
            mism += 1
            bad.append({"rank": r["rank"], "hebrew": r["hebrew"], "niqqud": niq,
                        "ipa": ipa, "niqqud_pattern": nv, "ipa_vowels": iv,
                        "russian": (r.get("russian") or "")[:40]})

    total = ok + mism
    print(f"проверено слов: {total}   (пропущено без данных: {skipped})")
    print(f"  гласные совпали:   {ok}  ({ok * 100 // max(total, 1)}%)")
    print(f"  РАСХОЖДЕНИЯ:       {mism}  ({mism * 100 // max(total, 1)}%)")

    if bad:
        print(f"\nпервые {min(args.show, len(bad))}:")
        print(f"  {'ранг':>6}  {'слово':12} {'огласовка':16} {'IPA':16} {'шаблон':10} {'из IPA':8}")
        for b in bad[:args.show]:
            print(f"  {b['rank']:6}  {b['hebrew']:12} {b['niqqud']:16} {b['ipa']:16} "
                  f"{b['niqqud_pattern']:10} {b['ipa_vowels']:8} {b['russian']}")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(bad, fh, ensure_ascii=False, indent=2)
        print(f"\nрасхождения сохранены: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
