#!/usr/bin/env python3
"""Озвучка предложений для чтения — всеми голосами языка.

Делает недостающие mp3 для каждого предложения из data/reading/<язык>/
sentences.json, по одному файлу на голос (см. sounds.py). Готовые непустые
файлы пропускает, поэтому после обрыва сети достаточно запустить снова —
продолжит с места. После генерации пути кладёт в базу load_to_db.py.

Голоса и приёмы те же, что у слов (words/tts/gen_sounds.py): gTTS и голоса
Microsoft Edge, тишина по краям обрезается, на каждый запрос к Edge — срок
ожидания, чтобы молчащий сервер не останавливал работу.

Запуск:
    python words/reading/gen_reading_sounds.py --language he --limit 20   # проба
    python words/reading/gen_reading_sounds.py --language he              # всё
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ТУТ = Path(__file__).resolve().parent
sys.path.insert(0, str(ТУТ))
sys.path.insert(0, str(ТУТ.parent / "tts"))

from sounds import ГОЛОСА, КОРЕНЬ, путь  # noqa: E402

ДАННЫЕ = ТУТ.parent / "data" / "reading"


# Движки этого генератора. Голос Piper делает words/tts/piper_noa.py.
ДВИЖКИ = ("gtts", "edge")


def задания(язык: str, тексты, корень: Path = КОРЕНЬ, голоса=None):
    """(текст, каталог голоса, движок, параметр) — только чего ещё нет.

    голоса — какие каталоги делать (None — все). 21.11.2026 Google посреди
    английского начал отказывать gTTS: генерацию продолжили без него, а его
    догоняют потом, медленно, отдельным запуском."""
    итог, было = [], set()
    for текст in тексты:
        if текст in было:
            continue
        было.add(текст)
        for голос, движок, параметр in ГОЛОСА[язык]:
            if движок not in ДВИЖКИ or (голоса and голос not in голоса):
                continue
            f = корень / путь(язык, голос, текст)
            if f.is_file() and f.stat().st_size > 0:
                continue
            итог.append((текст, голос, движок, параметр))
    return итог


def тексты_из_файла(язык: str):
    данные = json.loads((ДАННЫЕ / язык / "sentences.json").read_text(encoding="utf-8"))
    for номер in sorted(данные, key=int):
        for п in данные[номер]:
            if п.get("text"):
                yield п["text"]


async def сделать(язык, работы, потоков: int):
    from gen_sounds import edge_save, gtts_save, trim

    sem = asyncio.Semaphore(потоков)
    счёт = {"готово": 0, "сбой": 0}
    начало = time.time()

    async def одно(текст, голос, движок, параметр):
        f = КОРЕНЬ / путь(язык, голос, текст)
        f.parent.mkdir(parents=True, exist_ok=True)
        async with sem:
            if движок == "gtts":
                ok = await asyncio.to_thread(gtts_save, текст, параметр, f)
            else:
                ok = await edge_save(текст, параметр, f)
            if ok:
                await asyncio.to_thread(trim, f)
        счёт["готово" if ok else "сбой"] += 1
        n = счёт["готово"] + счёт["сбой"]
        if n % 100 == 0 or n == len(работы):
            прошло = time.time() - начало
            print(f"  {n}/{len(работы)}  сбоев {счёт['сбой']}  {прошло / 60:.1f} мин", flush=True)

    await asyncio.gather(*(одно(*р) for р in работы))
    return счёт


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--language", choices=sorted(ГОЛОСА), default="he")
    ap.add_argument("--limit", type=int, default=0, help="сколько предложений взять (проба)")
    ap.add_argument("--workers", type=int, default=3, help="запросов одновременно")
    ap.add_argument("--voices", default="", help="через запятую: только эти каталоги голосов")
    a = ap.parse_args()

    тексты = list(dict.fromkeys(тексты_из_файла(a.language)))
    if a.limit:
        тексты = тексты[:a.limit]
    голоса = {г.strip() for г in a.voices.split(",") if г.strip()} or None
    работы = задания(a.language, тексты, голоса=голоса)
    print(f"язык {a.language}: предложений {len(тексты)}, файлов сделать {len(работы)}", flush=True)
    if not работы:
        return 0
    счёт = asyncio.run(сделать(a.language, работы, a.workers))
    print(f"готово {счёт['готово']}, сбоев {счёт['сбой']} "
          f"(сбойные доделает повторный запуск)", flush=True)
    return 0 if not счёт["сбой"] else 2


if __name__ == "__main__":
    sys.exit(main())
