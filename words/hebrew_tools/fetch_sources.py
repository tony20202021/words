#!/usr/bin/env python3
"""
Сбор внешних свидетельств по словам иврита: Викисловари, Викиданные, переводчик.

Зачем несколько источников
--------------------------
Ни один источник не покрывает задачу целиком, и у каждого своя слепая зона:

  en.wiktionary   Лучший по форме слова: даёт огласовку (wv=), транслитерацию
                  (tr=), современный израильский IPA, часть речи, корень.
                  Омонимы разведены по Etymology — видно, что написание читается
                  по-разному. Слабое место: только словарные формы. По выборке
                  из первой тысячи статья нашлась у 68% написаний, но у 98% лемм.

  ru.wiktionary   Единственный источник РУССКОГО значения из словаря, а не из
                  машинного перевода. Плюс своя огласовка и транскрипция —
                  независимая проверка первых двух.

  Викиданные      Лексемы разведены по значениям, у форм своя огласовка. Помогает
                  там, где нужна не лемма, а конкретная словоформа.

  переводчик      Единственный, кто берёт словоформы и приставочные формы:
                  בחדר «в комнате», ממני «от меня» — их в словарях нет вовсе.
                  Машинный, поэтому голосует наравне с остальными, а не решает.

Кэш
---
Всё складывается в data/hebrew_freq/sources_cache/. Повторный запуск ничего не
перекачивает: разбор и сверку правим часто, а выкачка стоит тысяч запросов и
чужого трафика. Чтобы обновить запись — удалите её файл.

Использование
-------------
    python fetch_sources.py --max-rank 1000
    python fetch_sources.py --max-rank 1000 --workers 4
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hebrew_freq")
FULL = os.path.join(HERE, "hebrew_freq_10000_full.json")
CACHE = os.path.join(HERE, "sources_cache")

# Викимедиа просит представляться и указывать контакт — иначе запросы вправе
# резать. Тот же адрес, что и в подписи проекта.
UA = ("LangBot-dictionary-check/1.0 "
      "(https://github.com/tony20202021/words; anton.v.mikhalev@gmail.com)")

_throttle = threading.Semaphore(1)
_last_call = [0.0]
MIN_GAP = 0.12  # с, между запросами к одному хосту — вежливость, не требование


def _fetch(url: str, timeout: int = 25, tries: int = 3) -> str | None:
    for attempt in range(tries):
        with _throttle:
            gap = MIN_GAP - (time.time() - _last_call[0])
            if gap > 0:
                time.sleep(gap)
            _last_call[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            # 429 и 5xx — отступаем, остальное бессмысленно повторять.
            if e.code not in (429, 500, 502, 503, 504):
                return None
        except Exception:
            pass
        time.sleep(1.5 * (attempt + 1))
    return None


def _cache_path(key: str) -> str:
    return os.path.join(CACHE, hashlib.sha1(key.encode("utf-8")).hexdigest() + ".json")


def cached(key: str, produce):
    """Значение из кэша либо свежее. Кэшируем и отрицательный ответ: «статьи нет»
    — это тоже результат, и перепроверять его каждый прогон незачем."""
    path = _cache_path(key)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)["value"]
        except Exception:
            pass
    value = produce()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"key": key, "value": value}, fh, ensure_ascii=False)
    os.replace(tmp, path)
    return value


def wikitext(site: str, title: str) -> str | None:
    def go():
        url = (f"https://{site}/w/api.php?action=parse&format=json&prop=wikitext"
               f"&page={urllib.parse.quote(title)}")
        raw = _fetch(url)
        if not raw:
            return None
        try:
            return json.loads(raw)["parse"]["wikitext"]["*"]
        except Exception:
            return None
    return cached(f"{site}|{title}", go)


def translate_ru(text: str) -> str | None:
    """Машинный перевод — берёт словоформы, которых нет в словарях."""
    def go():
        url = ("https://translate.googleapis.com/translate_a/single"
               f"?client=gtx&sl=iw&tl=ru&dt=t&q={urllib.parse.quote(text)}")
        raw = _fetch(url)
        if not raw:
            return None
        try:
            return "".join(part[0] for part in json.loads(raw)[0] if part and part[0]).strip()
        except Exception:
            return None
    return cached(f"gtx|{text}", go)


def wikidata_lexemes(word: str) -> list[dict] | None:
    """Лексемы иврита с таким написанием: по одной на значение."""
    def go():
        url = ("https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json"
               f"&type=lexeme&language=he&limit=10&search={urllib.parse.quote(word)}")
        raw = _fetch(url)
        if not raw:
            return None
        try:
            out = []
            for e in json.loads(raw).get("search", []):
                # Поиск отдаёт и составные выражения — нужна ровно эта запись.
                if e.get("label") == word:
                    out.append({"id": e.get("id"), "description": e.get("description")})
            return out
        except Exception:
            return None
    return cached(f"wd|{word}", go)


def harvest(row: dict) -> dict:
    form = row["hebrew"]
    lemma = (row.get("lemma") or "").strip() or form
    out = {
        "rank": row["rank"],
        "hebrew": form,
        "lemma": lemma,
        "en_form": wikitext("en.wiktionary.org", form),
        "en_lemma": wikitext("en.wiktionary.org", lemma) if lemma != form else None,
        "ru_form": wikitext("ru.wiktionary.org", form),
        "ru_lemma": wikitext("ru.wiktionary.org", lemma) if lemma != form else None,
        "gtx_form": translate_ru(form),
        "wd_form": wikidata_lexemes(form),
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-rank", type=int, default=1000, help="до какого ранга собирать")
    ap.add_argument("--workers", type=int, default=4, help="параллельных запросов")
    args = ap.parse_args()

    os.makedirs(CACHE, exist_ok=True)
    rows = [r for r in json.load(open(FULL, encoding="utf-8")) if r["rank"] <= args.max_rank]
    print(f"слов: {len(rows)}, кэш: {CACHE}")

    done = [0]
    lock = threading.Lock()

    def one(r):
        res = harvest(r)
        with lock:
            done[0] += 1
            if done[0] % 25 == 0 or done[0] == len(rows):
                print(f"  {done[0]}/{len(rows)}", flush=True)
        return res

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        harvested = list(ex.map(one, rows))

    stats = {
        "en по написанию": sum(1 for h in harvested if h["en_form"] and "==Hebrew==" in h["en_form"]),
        "en по лемме": sum(1 for h in harvested if h["en_lemma"] and "==Hebrew==" in h["en_lemma"]),
        "ru по написанию": sum(1 for h in harvested if h["ru_form"]),
        "ru по лемме": sum(1 for h in harvested if h["ru_lemma"]),
        "перевод": sum(1 for h in harvested if h["gtx_form"]),
        "лексемы": sum(1 for h in harvested if h["wd_form"]),
    }
    print("\nсобрано:")
    for k, v in stats.items():
        print(f"  {k:18} {v}")

    covered = sum(1 for h in harvested
                  if (h["en_form"] and "==Hebrew==" in h["en_form"])
                  or (h["en_lemma"] and "==Hebrew==" in h["en_lemma"])
                  or h["ru_form"] or h["ru_lemma"])
    print(f"  {'словарь хоть один':18} {covered} из {len(harvested)}")

    out = os.path.join(HERE, f"sources_{args.max_rank}.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(harvested, fh, ensure_ascii=False)
    print(f"\nзаписано: {os.path.basename(out)} ({os.path.getsize(out) // 1024} КБ)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
