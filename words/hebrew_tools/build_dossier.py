#!/usr/bin/env python3
"""
Досье по каждому слову: наши поля рядом со всем, что сказали источники.

Зачем отдельный файл
--------------------
Сырые статьи Викисловаря — это сотни килобайт разметки на слово, и решать по ним
нельзя ни человеку, ни агенту: утонешь в шаблонах. Здесь то же самое сведено к
одной строке JSON на слово — наши поля, разобранные свидетельства каждого
источника и уже посчитанные расхождения. Дальше по этому файлу работают
проверяющие: каждый берёт свой диапазон рангов и видит все варианты сразу,
как и просил план — «внимательно проанализировать все варианты».

Формат — JSONL, по строке на слово, отсортировано по рангу. Строки независимы,
поэтому файл можно резать на диапазоны без разбора целиком.

Использование
-------------
    python build_dossier.py --max-rank 1000
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from parse_sources import compare, parse_en, parse_ru

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hebrew_freq")
FULL = os.path.join(HERE, "hebrew_freq_10000_full.json")

OUR_FIELDS = ("niqqud", "ipa", "translit_ru", "russian", "pos", "lemma")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-rank", type=int, default=1000)
    args = ap.parse_args()

    src = os.path.join(HERE, f"sources_{args.max_rank}.json")
    if not os.path.exists(src):
        print(f"нет {os.path.basename(src)} — сначала fetch_sources.py")
        return 1

    rows = {r["rank"]: r for r in json.load(open(FULL, encoding="utf-8"))}
    evidence = {e["rank"]: e for e in json.load(open(src, encoding="utf-8"))}

    out_path = os.path.join(HERE, f"dossier_{args.max_rank}.jsonl")
    # Пишем через временный файл: досье читают агенты, и перезапись на месте
    # отдала бы кому-то половину файла.
    tmp_path = out_path + ".tmp"
    n_with_issues = 0
    with open(tmp_path, "w", encoding="utf-8") as fh:
        for rank in sorted(evidence):
            row = rows.get(rank)
            if row is None:
                continue
            ev = evidence[rank]
            en = parse_en(ev.get("en_form"), "форма") + parse_en(ev.get("en_lemma"), "лемма")
            ru = parse_ru(ev.get("ru_form"), "форма") + parse_ru(ev.get("ru_lemma"), "лемма")
            issues = compare(row, ev)
            if issues:
                n_with_issues += 1
            rec = {
                "rank": rank,
                "hebrew": row["hebrew"],
                "ours": {k: row.get(k) or "" for k in OUR_FIELDS},
                "en": [{k: e[k] for k in ("via", "pos", "pos_src", "niqqud", "translit",
                                          "ipa", "root", "glosses")} for e in en],
                "ru": ru,
                "gtx": ev.get("gtx_form") or "",
                "wd": ev.get("wd_form") or [],
                "issues": issues,
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    os.replace(tmp_path, out_path)
    size = os.path.getsize(out_path)
    print(f"досье: {os.path.basename(out_path)}  {len(evidence)} слов, {size // 1024} КБ")
    print(f"из них с расхождениями: {n_with_issues}")
    print(f"средний размер записи: {size // max(1, len(evidence))} байт")
    return 0


if __name__ == "__main__":
    sys.exit(main())
