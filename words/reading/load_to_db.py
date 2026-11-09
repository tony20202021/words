#!/usr/bin/env python3
"""Кладёт предложения для чтения в поле reading_sentences каждого слова.

ПОЧЕМУ ПОЛЕМ СЛОВА, А НЕ ОТДЕЛЬНОЙ КОЛЛЕКЦИЕЙ. Так уже сделано у tag_groups:
состав группы собирается заранее скриптом и лежит в самом слове, а карточка
только перекладывает его наружу. Отдельная коллекция потребовала бы соединения
в каждой из пяти выборок слова — и каждая, где про него забыли, молча отдавала
бы карточку без предложений.

ЗАГРУЗЧИК ПЕРЕПРОВЕРЯЕТ, А НЕ ПЕРЕКЛАДЫВАЕТ. Предложения сочинены под словарь,
каким он был в день сочинения. Словарь меняется: 08.11.2026 английский заменили
целиком, и слово №50 стало другим словом. Если бы загрузчик просто переложил
файл, предложения уехали бы к чужим словам — и выглядело бы это как «плохие
примеры», а не как сбой загрузки.

Поэтому каждое предложение проверяется заново тем же сторожем, что при приёме:
состав по разрешённым словам и наличие целевого. Слово, у которого хоть одно
предложение не прошло, НЕ записывается целиком — половина примеров хуже, чем
отсутствие блока, потому что про вторую половину никто не узнает.

Запуск:  python words/reading/load_to_db.py --language he [--apply]
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ТУТ = Path(__file__).resolve().parent
sys.path.insert(0, str(ТУТ))

from check import проверить                                  # noqa: E402
from vocabulary import собрать                               # noqa: E402

ДАННЫЕ = ТУТ.parents[0] / "data" / "reading"
ЯЗЫКИ = {"en": "Английский", "he": "Иврит"}
URL = os.getenv("MONGODB_URL", "mongodb://localhost:8527")
DB_NAME = os.getenv("MONGODB_DB_NAME", "language_learning_bot")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--language", choices=sorted(ЯЗЫКИ), default="he")
    ap.add_argument("--always", type=int, default=100,
                    help="слова до этого номера разрешены всегда")
    ap.add_argument("--apply", action="store_true", help="записать изменения")
    a = ap.parse_args()

    from pymongo import MongoClient, UpdateOne
    db = MongoClient(URL, serverSelectionTimeoutMS=5000)[DB_NAME]
    lang = db.languages.find_one({"name_ru": ЯЗЫКИ[a.language]})
    if not lang:
        print(f"языка {ЯЗЫКИ[a.language]!r} в базе нет")
        return 1

    слова = sorted(db.words.find({"language_id": lang["_id"]},
                                 {"word_number": 1, "word_foreign": 1, "lemma": 1,
                                  "reading_sentences": 1}),
                   key=lambda w: w["word_number"])
    по_номеру = {w["word_number"]: w for w in слова}

    путь = ДАННЫЕ / a.language / "sentences.json"
    if not путь.exists():
        print(f"нет файла {путь}")
        return 1
    данные = json.loads(путь.read_text(encoding="utf-8"))

    к_записи, отказы = [], []
    всего = 0
    for ключ in sorted(данные, key=int):
        номер = int(ключ)
        слово = по_номеру.get(номер)
        if not слово:
            отказы.append((ключ, f"слова №{номер} в языке нет"))
            continue
        словарь = собрать(слова, до_номера=номер, всегда_первые=a.always,
                          язык=a.language)
        годные, плохие = [], []
        for п in данные[ключ]:
            итог = проверить(п["text"], слово["word_foreign"], словарь)
            if итог.годится:
                # Транскрипция едет вместе с текстом: на карточке это четвёртая
                # колонка таблицы (владелец, 09.11.2026). Собирает её
                # reading/transcribe.py, у иврита — со сверкой глазами.
                годные.append({"text": п["text"], "ru": п["ru"],
                               "tr": п.get("tr", "")})
            else:
                плохие.append((п["text"], итог.объясни()))
        if плохие:
            # Частично — нельзя: про выпавшие примеры никто не узнает.
            отказы.append((ключ, f"{len(плохие)} из {len(данные[ключ])} не прошли: "
                                 + "; ".join(f"«{т}» — {п}" for т, п in плохие[:3])))
            continue
        всего += len(годные)
        if слово.get("reading_sentences") == годные:
            continue
        к_записи.append(UpdateOne({"_id": слово["_id"]},
                                  {"$set": {"reading_sentences": годные,
                                            "updated_at": datetime.now(timezone.utc)}}))

    print(f"язык: {ЯЗЫКИ[a.language]}")
    print(f"  слов в файле:        {len(данные)}")
    print(f"  предложений прошло:  {всего}")
    print(f"  слов к записи:       {len(к_записи)}")
    print(f"  отказов:             {len(отказы)}")
    for ключ, причина in отказы[:15]:
        print(f"    №{ключ} — {причина}")

    if not a.apply:
        print("\n[без --apply] не записано")
        return 1 if отказы else 0
    if к_записи:
        итог = db.words.bulk_write(к_записи, ordered=False)
        print(f"\nзаписано слов: {итог.modified_count}")
    else:
        print("\nнечего записывать")
    return 1 if отказы else 0


if __name__ == "__main__":
    sys.exit(main())
