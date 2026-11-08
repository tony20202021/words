#!/usr/bin/env python3
"""Загружает собранный словарь английского в базу, сохраняя прогресс людей.

Почему не штатной загрузкой. Штатный путь (админка → BLS → backend) обновляет
слово по номеру, и это правильно: номер остаётся, запись остаётся, значит
остаётся и прогресс, привязанный к записи. Но на замене целого словаря он
спотыкается о две вещи:

  1. В коллекции words уникальный индекс (language_id, word_foreign). Новый
     словарь переставляет слова по номерам: «it» переезжает с 10-го на 12-й, и
     в этот миг оно ещё занято прежним владельцем. База отказывает. Лечится
     двумя проходами: сперва все переезжающие слова получают временные имена,
     потом настоящие.

  2. Озвучка. Поле sounds хранит пути, собранные по САМОМУ слову: у 12-го
     номера это sounds/en/gtts/said.mp3. Сменив слово на «it» и не тронув
     sounds, мы получим «it», которое вслух говорит «said». Штатная загрузка
     так и сделает: пустое значение она отбрасывает, а не очищает. Поэтому
     пути здесь пересчитываются по новому слову, а где файлов нет — поле
     очищается. Молчание честнее чужого голоса.

Что НЕ делается. Прогресс не трогается вовсе: ни одной записи
user_statistics. Люди остаются на тех же номерах — слова под номерами
меняются, и об этом их предупреждают отдельно.

Примеры:
    python eng_tools/load_to_db.py --dry-run     # посчитать, ничего не писать
    python eng_tools/load_to_db.py               # записать
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ТУТ = Path(__file__).resolve().parent
sys.path.insert(0, str(ТУТ))
sys.path.insert(0, str(ТУТ.parents[0] / "tts"))

ДАННЫЕ = ТУТ.parents[0] / "data" / "eng_freq"
ОЗВУЧКА = (ТУТ.parents[1] / "language-learning-bot" / "backend" / "data"
           / "sounds" / "en")
ГОЛОСА = ["gtts", "voice1", "voice2"]
ЯЗЫК = "Английский"
ВРЕМЕННОЕ = "⁣вр{}"       # невидимый разделитель: такого слова не бывает


def единиц(текст: str):
    """Столько же, сколько считает backend: слова через пробел."""
    if not текст or not текст.strip():
        return None
    return len(текст.split())


def slug(word: str) -> str:
    from gen_sounds import slug as s
    return s(word)


def пути_озвучки(слово: str):
    """Пути к готовым файлам или None, если готовых нет."""
    имя = slug(слово)
    пути = {f"sound_{n}": f"sounds/en/{каталог}/{имя}.mp3"
            for n, каталог in enumerate(ГОЛОСА, 1)
            if (ОЗВУЧКА / каталог / f"{имя}.mp3").exists()}
    return json.dumps(пути, ensure_ascii=False) if пути else None


def подключиться():
    from pymongo import MongoClient
    db = MongoClient("mongodb://localhost:8527",
                     serverSelectionTimeoutMS=5000)["language_learning_bot"]
    язык = db.languages.find_one({"name_ru": ЯЗЫК})
    if not язык:
        raise SystemExit(f"языка {ЯЗЫК!r} в базе нет")
    return db, язык["_id"]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true",
                   help="посчитать и показать, ничего не записывая")
    p.add_argument("--dictionary", type=Path, default=ДАННЫЕ / "eng10k.json")
    a = p.parse_args(argv)

    словарь = json.loads(a.dictionary.read_text(encoding="utf-8"))
    db, язык_id = подключиться()

    было = {w["word_number"]: w
            for w in db.words.find({"language_id": язык_id})}

    # ── что получится ──────────────────────────────────────────────────────
    задумано = {}
    for ключ, запись in словарь.items():
        номер = int(запись.get("frequency") or ключ)
        задумано[номер] = {
            "word_foreign": запись["word"],
            "translation": ", ".join(запись["description"]),
            "transcription": запись["transcription"] or None,
            "sounds": пути_озвучки(запись["word"]),
        }

    переезжают = [n for n, ц in задумано.items()
                  if n in было and было[n]["word_foreign"] != ц["word_foreign"]]
    создать = [n for n in задумано if n not in было]
    лишние = [n for n in было if n not in задумано]
    без_озвучки = [n for n, ц in задумано.items() if ц["sounds"] is None]
    теряют_озвучку = [n for n, ц in задумано.items()
                      if n in было and было[n].get("sounds") and ц["sounds"] is None]

    print(f"в базе сейчас: {len(было)} слов")
    print(f"в словаре:     {len(задумано)} слов")
    print(f"меняют слово:  {len(переезжают)}")
    print(f"создать:       {len(создать)}")
    print(f"лишних в базе: {len(лишние)}" +
          (f" — номера {sorted(лишние)[:10]}" if лишние else ""))
    print(f"останутся без озвучки: {len(без_озвучки)}")
    print(f"  из них потеряют прежнюю (она была от другого слова): "
          f"{len(теряют_озвучку)}")
    прогресс = db.user_statistics.count_documents({"language_id": str(язык_id)})
    print(f"записей прогресса (не тронем ни одной): {прогресс}")

    if a.dry_run:
        print("\n--dry-run: ничего не записано")
        return 0

    # ── проход 1: освободить занятые слова ─────────────────────────────────
    # Переименовываются только переезжающие. Этого довольно: если слово X
    # занято записью, которая НЕ переезжает, то X — её собственная цель, и
    # второй претендент на X означал бы дубль в словаре, чего там нет.
    for i, номер in enumerate(переезжают, 1):
        db.words.update_one(
            {"_id": было[номер]["_id"]},
            {"$set": {"word_foreign": ВРЕМЕННОЕ.format(номер)}})
        if i % 500 == 0:
            print(f"  проход 1: {i}/{len(переезжают)}")
    print(f"проход 1: освобождено {len(переезжают)} слов")

    # ── проход 2: настоящие значения ───────────────────────────────────────
    обновлено = создано = 0
    сейчас = datetime.utcnow()
    for номер in sorted(задумано):
        цель = задумано[номер]
        поля = {
            "word_foreign": цель["word_foreign"],
            "translation": цель["translation"],
            "transcription": цель["transcription"],
            "word_foreign_unit_count": единиц(цель["word_foreign"]),
            "transcription_unit_count": единиц(цель["transcription"] or ""),
            "sounds": цель["sounds"],
            "updated_at": сейчас,
        }
        if номер in было:
            db.words.update_one({"_id": было[номер]["_id"]}, {"$set": поля})
            обновлено += 1
        else:
            db.words.insert_one({**поля, "language_id": язык_id,
                                 "word_number": номер, "created_at": сейчас})
            создано += 1
        if (обновлено + создано) % 1000 == 0:
            print(f"  проход 2: {обновлено + создано}/{len(задумано)}")

    print(f"проход 2: обновлено {обновлено}, создано {создано}")

    # ── проверка ───────────────────────────────────────────────────────────
    осталось_временных = db.words.count_documents(
        {"language_id": язык_id, "word_foreign": {"$regex": "^⁣вр"}})
    всего = db.words.count_documents({"language_id": язык_id})
    прогресс_после = db.user_statistics.count_documents(
        {"language_id": str(язык_id)})
    print(f"\nитог: слов {всего}, временных осталось {осталось_временных}, "
          f"записей прогресса {прогресс_после}")
    if осталось_временных:
        print("ВНИМАНИЕ: остались временные имена — проход 2 прошёл не до конца")
        return 1
    if прогресс_после != прогресс:
        print(f"ВНИМАНИЕ: прогресс изменился ({прогресс} → {прогресс_после})")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
