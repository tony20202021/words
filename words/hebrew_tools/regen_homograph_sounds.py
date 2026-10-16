#!/usr/bin/env python3
"""Переозвучивает омографы — из ОГЛАСОВАННОЙ формы, а не из голых согласных.

Что было не так
---------------
Все звуки делались из поля `hebrew`, то есть из написания без огласовки
(gen_sounds_1000.py, строка `w = rows[n]["hebrew"]`). Для большинства слов это
сходит с рук, но у 108 записей одно и то же написание читается двумя
способами — и каждый движок выбирал чтение сам.

Жалоба владельца 09.10.2026 про слово 233: транскрипция «бэхА», а голоса
говорят «бах», «бех», «бех». Проверено на слух им же:

    из בך    (как сейчас)  → «бах»   — это чтение ЖЕНСКОЕ, בָּךְ
    из בְּךָ  (огласованно)  → «беха»  — верно
    из בָּךְ                 → «бах»   — верно, но это другое слово

То есть без огласовки движок читал женскую форму вместо мужской. Карточка
показывала одно, а произносила другое — хуже, чем молчать.

Что делает этот скрипт
----------------------
Для каждого слова с непустым `tones` (их 108) генерирует три голоса из
`niqqud` и кладёт рядом со старыми, под именем `{номер}_niqqud.mp3`.

Почему новое имя, а не поверх старого. Телефон кеширует звуки по пути: тот же
путь — тот же файл, и перезаписанный на сервере до него уже не доедет. Новое
имя заодно оставляет прежние файлы на месте, так что откат — это вернуть
прежние пути в базе.

Пути в базе обновляются здесь же: поле `sounds` у этих слов начинает
указывать на новые файлы.

Запуск:
    python words/hebrew_tools/regen_homograph_sounds.py          # показать
    python words/hebrew_tools/regen_homograph_sounds.py --apply  # сделать
"""

import argparse
import asyncio
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data", "hebrew_freq"))
FULL = os.path.join(DATA, "hebrew_freq_10000_full.json")
SOUNDS = "/home/tony/repos/words/language-learning-bot/backend/data/sounds/he"
VOICES = (("gtts", None), ("hila", "he-IL-HilaNeural"), ("avri", "he-IL-AvriNeural"))
SUFFIX = "_niqqud"


def trim(path: str, threshold: float = -40.0, keep: int = 40) -> None:
    """Срезать тишину по краям — как это делал gen_sounds_1000.py."""
    from pydub import AudioSegment
    from pydub.silence import detect_leading_silence

    try:
        seg = AudioSegment.from_file(path)
        lead = detect_leading_silence(seg, silence_threshold=threshold)
        trail = detect_leading_silence(seg.reverse(), silence_threshold=threshold)
        start, end = max(0, lead - keep), len(seg) - max(0, trail - keep)
        if end > start:
            seg[start:end].export(path, format="mp3", bitrate="48k")
    except Exception as e:
        print(f"    не удалось подрезать {path}: {e}")


def gtts_save(text: str, path: str, tries: int = 3) -> bool:
    from gtts import gTTS

    for i in range(tries):
        try:
            gTTS(text=text, lang="iw", slow=False).save(path)
            if os.path.getsize(path) > 0:
                return True
        except Exception:
            time.sleep(1.5 * (i + 1))
    return False


async def edge_save(text: str, voice: str, path: str, tries: int = 3) -> bool:
    import edge_tts

    for i in range(tries):
        try:
            await edge_tts.Communicate(text, voice).save(path)
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return True
        except Exception:
            await asyncio.sleep(1.5 * (i + 1))
    return False


def homographs(rows):
    """Слова, у которых одно написание читается по-разному."""
    return [r for r in rows if (r.get("tones") or "").strip()]


async def regenerate(rows, apply: bool):
    targets = homographs(rows)
    print(f"омографов: {len(targets)}; голосов на каждый: {len(VOICES)}")
    for r in targets[:5]:
        print(f"    #{r['rank']:<5} {r['hebrew']:<10} -> {r['niqqud']:<14} {r['russian'][:30]}")
    if not apply:
        print("\nпробный прогон. Чтобы озвучить — запустите с --apply")
        return []

    done, failed = [], []
    for i, r in enumerate(targets, 1):
        text, rank = r["niqqud"], r["rank"]
        paths = {}
        for folder, voice in VOICES:
            out = f"{SOUNDS}/{folder}/{rank}{SUFFIX}.mp3"
            ok = gtts_save(text, out) if voice is None else await edge_save(text, voice, out)
            if ok:
                trim(out)
                paths[folder] = f"sounds/he/{folder}/{rank}{SUFFIX}.mp3"
            else:
                failed.append((rank, folder))
        if len(paths) == len(VOICES):
            done.append((rank, paths))
        if i % 20 == 0:
            print(f"  {i}/{len(targets)}, не вышло: {len(failed)}")
    print(f"озвучено слов: {len(done)}, неудач: {len(failed)}")
    if failed:
        print("  не вышло:", failed[:10])
    return done


async def update_db(done):
    """Переставить пути в базе на новые файлы."""
    from dotenv import load_dotenv
    from motor.motor_asyncio import AsyncIOMotorClient
    from bson import ObjectId

    load_dotenv("/home/tony/repos/words/language-learning-bot/backend/.env")
    db = AsyncIOMotorClient(os.getenv("MONGODB_URL", "mongodb://localhost:8527"))[
        os.getenv("MONGODB_DB_NAME", "language_learning_bot")]
    heb = ObjectId("6a5f9b89f97381939e0699fb")
    updated = 0
    for rank, paths in done:
        sounds = json.dumps({
            "sound_1": paths["gtts"],
            "sound_2": paths["hila"],
            "sound_3": paths["avri"],
        }, ensure_ascii=False)
        res = await db.words.update_one(
            {"language_id": heb, "word_number": rank}, {"$set": {"sounds": sounds}})
        updated += res.modified_count
    print(f"путей обновлено в базе: {updated}")


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    with open(FULL, encoding="utf-8") as fh:
        rows = json.load(fh)
    done = await regenerate(rows, args.apply)
    if args.apply and done:
        await update_db(done)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
