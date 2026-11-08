#!/usr/bin/env python3
"""
Озвучка слов: три голоса на слово, для любого языка.

Зачем отдельно от иврита
------------------------
Для иврита звуки делал разовый скрипт gen_sounds_1000.py: пути, голоса и
номера были вшиты в него намертво. Владелец попросил озвучку для английского,
а дальше тем же понадобится немецкий, испанский и французский — поэтому язык
здесь параметр, а не часть кода.

Голоса бесплатные и без ключей: gTTS (Google) и edge_tts (голоса Microsoft
Edge). Ничего оплачивать и нигде регистрироваться не нужно.

Почему имя файла — СЛОВО, а не номер
------------------------------------
У иврита файлы названы по номеру слова (17.mp3). Для английского так делать
нельзя: владелец ищет другой, общеупотребительный частотный список взамен
нынешнего делового («#3005 mainframes», «#3050 barrels»), и при его замене
номера съедут — вся озвучка окажется привязана не к тем словам.

Имя по слову такую замену переживает. Проверено: все 8466 английских
написаний различны, необычный символ есть ровно в одном («AT&T's»), и он
уходит в слаг. Для иврита имена остаются прежними — там уже всё сделано.

Повторный запуск продолжает с места обрыва: готовые непустые файлы
пропускаются. Это и способ лечить обрывы сети — просто запустить снова.

Запуск:
    python words/tts/gen_sounds.py --language Английский --limit 20   # проба
    python words/tts/gen_sounds.py --language Английский             # всё
    python words/tts/gen_sounds.py --language Английский --write-db  # записать пути
"""
import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOUNDS = ROOT / "language-learning-bot" / "backend" / "data" / "sounds"
ENV = ROOT / "language-learning-bot" / ".env"

# Язык -> код каталога, язык для gTTS и два голоса Microsoft Edge.
# Добавить язык = добавить строку. Список голосов: edge-tts --list-voices
#
# ИВРИТА ЗДЕСЬ НЕТ НАМЕРЕННО. Его озвучка уже сделана прежним скриптом, и
# устроена иначе: файлы названы по номеру слова (17.mp3), каталоги голосов —
# hila и avri. Запусти этот инструмент для иврита, он сложил бы рядом второй
# набор из десяти тысяч файлов под другими именами: база продолжила бы
# указывать на старые, а новые заняли бы место впустую и никому не
# понадобились. Переименовывать готовое ради единообразия — работа без выгоды
# и с риском остаться без звука, поэтому иврит оставлен как есть.
LANGUAGES = {
    "Английский": {"code": "en", "gtts": "en",
                   "edge": ["en-US-AriaNeural", "en-US-GuyNeural"]},
    "Немецкий":   {"code": "de", "gtts": "de",
                   "edge": ["de-DE-KatjaNeural", "de-DE-ConradNeural"]},
    "Испанский":  {"code": "es", "gtts": "es",
                   "edge": ["es-ES-ElviraNeural", "es-ES-AlvaroNeural"]},
    "Французский": {"code": "fr", "gtts": "fr",
                    "edge": ["fr-FR-DeniseNeural", "fr-FR-HenriNeural"]},
}

VOICE_DIRS = ["gtts", "voice1", "voice2"]


def slug(word: str) -> str:
    """
    Имя файла из слова. Небуквенное — в подчёркивание, иначе путь зависел бы
    от того, что файловая система считает допустимым.
    """
    s = re.sub(r"[^0-9A-Za-z_.-]+", "_", word.strip())
    return s.strip("._") or "_"


def env_value(key: str) -> str:
    """Значение из .env без разбора остального файла и без печати секретов."""
    try:
        for line in ENV.read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def trim(path: Path, thr: float = -40.0, keep: int = 40) -> None:
    """Обрезать тишину по краям: движки щедры на паузы, а слушать их незачем."""
    from pydub import AudioSegment
    from pydub.silence import detect_leading_silence
    try:
        seg = AudioSegment.from_file(path)
        lead = detect_leading_silence(seg, silence_threshold=thr)
        trail = detect_leading_silence(seg.reverse(), silence_threshold=thr)
        start, end = max(0, lead - keep), len(seg) - max(0, trail - keep)
        if end > start:
            seg[start:end].export(path, format="mp3", bitrate="48k")
    except Exception as e:
        print(f"    обрезка не вышла {path.name}: {e}")


def ready(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def gtts_save(text: str, lang: str, path: Path, tries: int = 3) -> bool:
    from gtts import gTTS
    for i in range(tries):
        try:
            gTTS(text=text, lang=lang, slow=False).save(str(path))
            if ready(path):
                return True
        except Exception:
            time.sleep(1.5 * (i + 1))
    return False


# Срок ожидания одного запроса к голосу. Повторы без срока не помогают вовсе:
# 08.11.2026 работа встала на 7400-м слове из 8466 — соединение к серверу
# Microsoft осталось открытым, ответа не пришло, и `except` не сработал, потому
# что ничего не упало. Четыре часа работы молча замерли на одном слове.
СРОК_ЗАПРОСА = 60


async def edge_save(text: str, voice: str, path: Path, tries: int = 3,
                    срок: float = СРОК_ЗАПРОСА) -> bool:
    import edge_tts
    for i in range(tries):
        try:
            await asyncio.wait_for(
                edge_tts.Communicate(text, voice).save(str(path)), timeout=срок)
            if ready(path):
                return True
        except asyncio.TimeoutError:
            # Молчание сервера — такая же беда, как отказ, и лечится так же:
            # подождать и попробовать снова, а не висеть.
            await asyncio.sleep(1.5 * (i + 1))
        except Exception:
            await asyncio.sleep(1.5 * (i + 1))
    return False


def load_words(language: str, limit: int, first: int = 1, last: int = 0):
    from bson import ObjectId          # noqa: F401  (нужен pymongo)
    from pymongo import MongoClient
    db = MongoClient(env_value("MONGODB_URL"), serverSelectionTimeoutMS=5000)[
        env_value("MONGODB_DB_NAME") or "language_learning_bot"]
    lang = db.languages.find_one({"name_ru": language})
    if not lang:
        raise SystemExit(f"языка {language!r} в базе нет")
    номер = {}
    if first > 1:
        номер["$gte"] = first
    if last:
        номер["$lte"] = last
    q = {"language_id": lang["_id"]}
    if номер:
        q["word_number"] = номер
    cur = db.words.find(q, {"word_number": 1, "word_foreign": 1}).sort("word_number", 1)
    if limit:
        cur = cur.limit(limit)
    return db, lang["_id"], list(cur)


def слова_из_файла(путь: Path, limit: int, first: int = 1, last: int = 0):
    """Слова из готового словаря, минуя базу.

    Нужно, когда словарь ещё не загружен. Новый английский список — десять
    тысяч слов, и у 2768 из них озвучки нет: в базе этих слов никогда не было,
    а брать их оттуда — единственный путь, который инструмент знал. Ждать
    загрузки нельзя: загрузка словаря меняет то, по чему люди уже занимаются,
    и делается отдельным решением. Озвучка же ничего не меняет — файлы просто
    лежат на диске и ждут.

    Формат тот же, что у data/eng_freq/eng10k.json и прежнего eng.json:
    номер -> запись со словом.
    """
    записи = json.loads(путь.read_text(encoding="utf-8"))
    перебор = записи.values() if isinstance(записи, dict) else записи
    слова = []
    for r in перебор:
        слово = (r.get("word") or r.get("word_foreign") or "").strip()
        номер = r.get("frequency") or r.get("word_number") or 0
        if not слово:
            continue
        if first > 1 and номер < first:
            continue
        if last and номер > last:
            continue
        слова.append({"word_number": номер, "word_foreign": слово})
    слова.sort(key=lambda x: x["word_number"])
    if limit:
        слова = слова[:limit]
    return слова


def записать_пути(db, spec, base, слова) -> int:
    """Пути к ГОТОВЫМ файлам — в поле sounds. Несделанное не трогаем."""
    import json
    обновлено = 0
    for w in слова:
        текст = (w.get("word_foreign") or "").strip()
        if not текст:
            continue
        имя = slug(текст)
        пути = {f"sound_{n}": f"sounds/{spec['code']}/{d}/{имя}.mp3"
                for n, d in enumerate(VOICE_DIRS, 1)
                if ready(base / d / f"{имя}.mp3")}
        if not пути:
            continue
        r = db.words.update_one({"_id": w["_id"]},
                                {"$set": {"sounds": json.dumps(пути, ensure_ascii=False)}})
        обновлено += r.modified_count
    return обновлено


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--language", required=True, choices=sorted(LANGUAGES))
    ap.add_argument("--limit", type=int, default=0, help="сколько слов (0 — все)")
    # Диапазон номеров. Нужен потому, что генерация идёт часами, а людям
    # звук нужен там, где они сейчас занимаются, а не с самого частотного
    # слова: 07.11.2026 второй пользователь шёл по номерам около 4000, и
    # очередь дошла бы до него только через пять часов.
    ap.add_argument("--from", dest="first", type=int, default=1,
                    help="с какого номера слова")
    ap.add_argument("--to", dest="last", type=int, default=0,
                    help="по какой номер включительно (0 — до конца)")
    ap.add_argument("--write-db", action="store_true",
                    help="записать пути в поле sounds у слов")
    # Пути пишутся ПОРЦИЯМИ, а не один раз в конце. На коротком заходе разницы
    # нет, а на 8466 словах конец наступает через пять часов: всё это время
    # файлы на диске есть, а в приложении тишина — база о них не знает.
    ap.add_argument("--db-batch", type=int, default=200,
                    help="через сколько слов дописывать пути в базу")
    # Ничего не скачивать, только зарегистрировать уже лежащее на диске.
    # Нужно, чтобы подхватить сделанное, не останавливая идущую генерацию.
    ap.add_argument("--only-db", action="store_true",
                    help="не скачивать, только записать пути к готовым файлам")
    # Слова из файла, а не из базы: озвучить можно и то, что в базу ещё не
    # загружено. Записать пути при этом некуда — базе эти слова неизвестны.
    ap.add_argument("--words-from", type=Path,
                    help="взять слова из файла словаря, минуя базу")
    args = ap.parse_args()

    if args.words_from and (args.write_db or args.only_db):
        ap.error("--words-from и запись в базу несовместимы: слов из файла "
                 "в базе ещё нет, записывать пути некуда")

    spec = LANGUAGES[args.language]
    base = SOUNDS / spec["code"]
    for d in VOICE_DIRS:
        (base / d).mkdir(parents=True, exist_ok=True)

    if args.words_from:
        db, language_id = None, None
        words = слова_из_файла(args.words_from, args.limit,
                               args.first, args.last)
        откуда = f"файл {args.words_from.name}"
    else:
        db, language_id, words = load_words(args.language, args.limit,
                                            args.first, args.last)
        откуда = "база"
    отрезок = (f"номера {args.first}–{args.last or 'конец'}"
               if (args.first > 1 or args.last) else "все номера")
    print(f"{args.language}: {отрезок}, слов {len(words)}, "
          f"источник {откуда}, каталог {base}")

    t0 = time.time()
    сделано = пропущено = не_вышло = записано = 0
    пачка = []
    for i, w in enumerate(words, 1):
        text = (w.get("word_foreign") or "").strip()
        if not text:
            continue
        name = slug(text)
        if not args.only_db:
            цели = [
                (base / "gtts" / f"{name}.mp3", None),
                (base / "voice1" / f"{name}.mp3", spec["edge"][0]),
                (base / "voice2" / f"{name}.mp3", spec["edge"][1]),
            ]
            for path, voice in цели:
                if ready(path):
                    пропущено += 1
                    continue
                ok = (gtts_save(text, spec["gtts"], path) if voice is None
                      else await edge_save(text, voice, path))
                if ok:
                    trim(path)
                    сделано += 1
                else:
                    не_вышло += 1
                    print(f"  не вышло: {text!r} -> {path.name}")

        пачка.append(w)
        if args.write_db and len(пачка) >= max(1, args.db_batch):
            записано += записать_пути(db, spec, base, пачка)
            пачка.clear()

        if i % 100 == 0:
            прошло = time.time() - t0
            print(f"  {i}/{len(words)}  сделано {сделано}, пропущено {пропущено}, "
                  f"не вышло {не_вышло}, записано в базу {записано}, "
                  f"{прошло/60:.1f} мин", flush=True)

    if args.write_db and пачка:
        записано += записать_пути(db, spec, base, пачка)

    print(f"\nитог: сделано {сделано}, пропущено {пропущено}, не вышло {не_вышло}, "
          f"за {(time.time()-t0)/60:.1f} мин")

    if args.write_db:
        print(f"записано путей в базу: {записано}")
    else:
        print("пути в базу НЕ писались — для этого нужен --write-db")
    return 0 if не_вышло == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
