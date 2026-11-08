#!/usr/bin/env python3
"""Собирает готовый словарь английского из списка, прежних записей и переводов.

Выход — тот же формат, что у прежнего data/eng.json: словарь, где ключ это
номер по частоте, а значение несёт слово, перевод, транскрипцию и запас
транскрипций по службам. Формат сохранён не из уважения к нему, а потому что
его читает уже написанная оснастка: загрузка слов в базу и сбор транскрипций.

Откуда что берётся:

  — слово и его номер — из frequency.txt;
  — перевод: у трёх четвертей слов он есть в прежнем словаре, остальные
    переведены вручную и лежат в translations.json;
  — транскрипция: из прежнего словаря, если слово там было. Для новых слов
    поле остаётся пустым: транскрипции собирает word_transcription/ по
    Викисловарю и словарным службам, и подделывать их здесь нельзя — неверная
    транскрипция хуже отсутствующей, потому что её не видно.

Пример:
    python build_dictionary.py
    python build_dictionary.py --out /tmp/eng10k.json
"""
import argparse
import json
import sys
from pathlib import Path

ТУТ = Path(__file__).resolve().parent
sys.path.insert(0, str(ТУТ))

from build_list import СТАРЫЙ_СЛОВАРЬ, старые_переводы  # noqa: E402

ДАННЫЕ = ТУТ.parents[0] / "data" / "eng_freq"


def читать_список():
    out = []
    for l in (ДАННЫЕ / "frequency.txt").read_text(encoding="utf-8").splitlines():
        if not l or l.startswith("#"):
            continue
        ранг, слово, вид, откуда = l.split("\t")
        out.append((int(ранг), слово, вид, откуда))
    return out


def собрать():
    список = читать_список()
    старый = старые_переводы()
    переводы = json.loads((ДАННЫЕ / "translations.json").read_text(encoding="utf-8"))

    словарь, без_перевода, без_транскрипции = {}, [], []
    for ранг, слово, _, откуда in список:
        прежняя = старый.get(слово)
        if откуда == "старый" and прежняя:
            перевод = прежняя.get("description") or []
            транскрипция = прежняя.get("transcription") or ""
            запас = прежняя.get("all_transcriptions") or []
        else:
            перевод = переводы.get(слово) or []
            транскрипция, запас = "", []

        if not перевод:
            без_перевода.append(слово)
        if not транскрипция:
            без_транскрипции.append(слово)

        словарь[str(ранг)] = {
            "word": слово,
            "transcription": транскрипция,
            "description": перевод,
            "frequency": ранг,
            "language": "en",
            "all_transcriptions": запас,
        }
    return словарь, без_перевода, без_транскрипции


def влить_из_ipa_dict(словарь: dict, путь: Path) -> int:
    """Добирает транскрипции прямо из словаря ipa-dict.

    Тот же источник, что читает DictionaryService в word_transcription/, —
    открытый IPA-словарь open-dict-data/ipa-dict, 125 927 английских слов.
    Прямое чтение нужно для случая, когда после пересборки списка добавилась
    горстка слов: гонять ради пяти слов весь прогон по десяти тысячам —
    десять минут на работу, которая занимает миг.

    Файл в репозиторий не кладётся, путь передаётся ключом:
        https://raw.githubusercontent.com/open-dict-data/ipa-dict/master/data/en_US.txt
    """
    из_файла = {}
    for строка in путь.read_text(encoding="utf-8").splitlines():
        if строка.startswith("#") or not строка.strip():
            continue
        части = строка.strip().split("\t")
        if len(части) >= 2:
            из_файла[части[0].strip().lower()] = части[1].strip()

    добавлено = 0
    for запись in словарь.values():
        if запись["transcription"]:
            continue
        найдено = из_файла.get(запись["word"])
        if not найдено:
            continue
        запись["transcription"] = найдено
        запись["all_transcriptions"] = [{"service": "DictionaryService",
                                        "transcription": найдено}]
        добавлено += 1
    return добавлено


def влить_транскрипции(словарь: dict, путь: Path) -> int:
    """Берёт транскрипции из файла, но только там, где своих нет.

    Именно «только там, где нет», а не вместо всех. Оснастка
    word_transcription/ переписывает поле целиком, и прогон по локальному
    словарю обеднил бы 5658 записей: прежний словарь собирал транскрипции из
    двух источников, и Викисловарь добавлял варианты — чаще британские.
    У «the» было /ˈðə/, /ðə/, /ði/, /ˈðiː/, после замены осталось три; «for»
    потеряло /fɔː(ɹ)/, «you» — /juː/. Терять их незачем: дополнять надо те
    две с лишним тысячи слов, у которых транскрипции не было вовсе.
    """
    привезённые = json.loads(путь.read_text(encoding="utf-8"))
    по_слову = {r["word"]: r for r in привезённые.values() if r.get("word")}

    добавлено = 0
    for запись in словарь.values():
        if запись["transcription"]:
            continue
        гость = по_слову.get(запись["word"])
        if not гость or not транскрипция_гостя(гость):
            continue
        запись["transcription"] = гость["transcription"]
        запись["all_transcriptions"] = гость.get("all_transcriptions") or []
        добавлено += 1
    return добавлено


def транскрипция_гостя(гость: dict) -> str:
    return гость.get("transcription") or ""


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, default=ДАННЫЕ / "eng10k.json")
    p.add_argument("--transcriptions", type=Path,
                   help="файл в том же формате: взять транскрипции оттуда для "
                        "слов, у которых своих нет")
    p.add_argument("--ipa-dict", type=Path,
                   help="словарь ipa-dict (en_US.txt): добрать транскрипции "
                        "прямо из него")
    a = p.parse_args(argv)

    словарь, без_перевода, без_транскрипции = собрать()
    if a.transcriptions:
        добавлено = влить_транскрипции(словарь, a.transcriptions)
        без_транскрипции = [r["word"] for r in словарь.values()
                            if not r["transcription"]]
        print(f"транскрипций влито: {добавлено}")
    if a.ipa_dict:
        добрано = влить_из_ipa_dict(словарь, a.ipa_dict)
        без_транскрипции = [r["word"] for r in словарь.values()
                            if not r["transcription"]]
        print(f"добрано из ipa-dict: {добрано}")
    a.out.write_text(json.dumps(словарь, ensure_ascii=False, indent=1),
                     encoding="utf-8")

    print(f"собрано: {len(словарь)} слов → {a.out}")
    print(f"без перевода: {len(без_перевода)}"
          + (f" — {без_перевода[:10]}" if без_перевода else " (ни одного)"))
    print(f"без транскрипции: {len(без_транскрипции)} "
          f"— их собирает word_transcription/")
    if без_перевода:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
