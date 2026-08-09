#!/usr/bin/env python3
"""
Сбор подтверждённых правок из результата многоагентного разбора.

Что здесь чинится
-----------------
Результат приходит от агентов, а не из машины, и в нём регулярно попадаются
две поломки, каждая из которых тихо портит словарь, если не проверять:

  HTML-сущности    Поле tones содержит разметку <b>…</b>, и после сериализации
                   она приезжает как &lt;b&gt;. Записав её как есть, мы получим
                   на карточке видимые угловые скобки вместо жирного текста.

  Ранг вместо
  порядкового      Один из проверяющих пронумеровал правки 1,2,3,4,5 — по
  номера           порядку в своей партии, а не рангом слова. Пять правок
                   указывали на совершенно другие слова. Ловится сверкой
                   написания с рангом; чинится поиском ранга по написанию.

Плюс отбрасываются правки, которые уже применены: диапазоны иногда
пересчитываются заново, и без этого apply_review.py показывал бы их как
изменения.

Использование
-------------
    python collect_review.py итог_прогона.json --out правки.json
    python collect_review.py итог.json --out правки.json --max-rank 400
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from collections import Counter

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hebrew_freq")
FULL = os.path.join(HERE, "hebrew_freq_10000_full.json")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("result", help="JSON, отданный прогоном разбора")
    ap.add_argument("--out", required=True, help="куда положить нормализованные правки")
    ap.add_argument("--max-rank", type=int, default=1000,
                    help="в каком диапазоне искать ранг по написанию")
    args = ap.parse_args()

    data = json.load(open(args.result, encoding="utf-8"))
    # Результат может быть завёрнут обёрткой запуска.
    if "result" in data and isinstance(data["result"], dict):
        data = data["result"]
    confirmed = data.get("confirmed") or []
    print(f"диапазон: {data.get('range','?')}, счётчики: {data.get('counts')}")
    print(f"подтверждённых на входе: {len(confirmed)}")

    rows = json.load(open(FULL, encoding="utf-8"))
    by_rank = {r["rank"]: r for r in rows}

    out, already, unresolved = [], 0, []
    remapped = 0
    for p in confirmed:
        p["proposed"] = html.unescape(p.get("proposed") or "")
        p["current"] = html.unescape(p.get("current") or "")
        row = by_rank.get(p.get("rank"))
        if not row or row["hebrew"] != p.get("hebrew"):
            cands = [r["rank"] for r in rows
                     if r["hebrew"] == p.get("hebrew") and r["rank"] <= args.max_rank]
            if len(cands) != 1:
                unresolved.append((p, cands))
                continue
            print(f"  ранг исправлен по написанию: {p['hebrew']} {p['field']} "
                  f"{p.get('rank')} -> {cands[0]}")
            p["rank"] = cands[0]
            row = by_rank[cands[0]]
            remapped += 1
        if (row.get(p["field"]) or "") == p["proposed"].strip():
            already += 1
            continue
        out.append(p)

    print(f"  уже применено:        {already}")
    print(f"  ранг восстановлен:    {remapped}")
    print(f"  к применению:         {len(out)}  {dict(Counter(p['field'] for p in out))}")
    if unresolved:
        print(f"  НЕ СОПОСТАВЛЕНО:      {len(unresolved)} — разобрать руками:")
        for p, c in unresolved:
            print(f"    {p.get('hebrew','?')} {p.get('field','?')} ранг {p.get('rank')}, "
                  f"кандидаты {c}")

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"\nзаписано: {args.out}")
    print("дальше: python apply_review.py <файл> --apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
