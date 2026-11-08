#!/usr/bin/env python3
"""Собирает учебный частотный список английского и считает, что уже переведено.

Зачем. Прежний список (data/eng.json, 10000 слов) оказался деловым: в нём нет
ни «cat», ни «laugh», ни «hungry», ни «spoon», зато «the» и «The» лежат двумя
записями. Для изучающего язык это плохой словарь.

Откуда частоты. wordfreq 3.1.1 — сводный частотный список по восьми корпусам
(субтитры, книги, вики, новости, твиттер, реддит и другие). Пакет в окружение
не ставится и в репозиторий не кладётся: нужен один файл данных из его колеса,
путь к нему передаётся ключом. В репозиторий едет только результат — список,
он и есть то, что надо воспроизводить.

Откуда переводы. Прежний словарь выбрасывать незачем: в нём 8874 настоящих
английских слова с переводами и транскрипциями, и около семидесяти процентов
нового списка в нём уже есть. Остаток переводится вручную и накапливается в
data/eng_freq/translations.json.

Пример:
    python build_list.py --wordfreq ~/wf/wordfreq/data/large_en.msgpack.gz
    python build_list.py --names-from ~/wf    # пересобрать подсказку по именам
"""
import argparse
import json
import sys
from pathlib import Path

ТУТ = Path(__file__).resolve().parent
sys.path.insert(0, str(ТУТ))

from filters import (ВИДЫ_НА_ПЕРЕВОД, ВИДЫ_ОТСЕВА, годится_как_слово,  # noqa: E402
                     загрузить_имена, разметить, собрать_имена_из_источников)
from wordfreq_reader import buckets  # noqa: E402

КОРЕНЬ = ТУТ.parents[1]
ДАННЫЕ = КОРЕНЬ / "words" / "data" / "eng_freq"
СТАРЫЙ_СЛОВАРЬ = КОРЕНЬ / "data" / "eng.json"


def слова_по_частоте(путь_данных: Path):
    """Слова от частых к редким. Внутри корзины частота одна, порядок алфавитный."""
    видели = set()
    for корзина in buckets(str(путь_данных))[1:]:
        for w in корзина:
            if w in видели:
                continue
            видели.add(w)
            if годится_как_слово(w):
                yield w


КИРИЛЛИЦА = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюя")


def это_перевод(описание) -> bool:
    """Есть ли в описании хоть что-то по-русски.

    В прежнем словаре 85 записей «переведены» латиницей: фамилии («Wilson»),
    бренды («Microsoft»), аббревиатуры («ROM») и настоящие ляпы делового
    корпуса — «lie» и «lies» переведены как «False», «ram» как «RAM», «excel»
    как «Excel». Это не переводы, а эхо слова самого себя, и человеку они
    не говорят ничего.
    """
    return any(set(x.lower()) & КИРИЛЛИЦА for x in (описание or [])
               if isinstance(x, str))


def старые_переводы() -> dict:
    """Слово → запись прежнего словаря, но только там, где перевод есть.

    В прежнем словаре пятнадцать записей с пустым description — «am», «ones»,
    «Its», «THE» и прочие огрызки регистра — и ещё 85 с «переводом» латиницей.
    Считать их переведёнными значит оставить в словаре слова, которые человеку
    покажут пустыми или бессмысленными: ровно это и случилось, пока
    проверялось наличие слова вместо наличия перевода.
    Регистр не важен, первая годная запись частотнее.
    """
    d = json.loads(СТАРЫЙ_СЛОВАРЬ.read_text(encoding="utf-8"))
    записи = d.values() if isinstance(d, dict) else d
    out = {}
    for r in записи:
        w = (r.get("word") or "").strip().lower()
        if w and это_перевод(r.get("description")) and w not in out:
            out[w] = r
    return out


def отброшенные_вручную() -> dict:
    """Слово → причина. Пополняется при переводе порций.

    Фильтры не умеют отличить «lovely» от «loves»: первое отдельное слово,
    второе форма того же «love», и держать в словаре обе бессмысленно —
    человек учил бы кошку дважды, как «cat» и «cats». Решает это человек на
    переводе, а сборщик обязан его решение помнить и добрать список из
    глубины, иначе каждая пересборка возвращала бы выброшенное.
    """
    путь = ДАННЫЕ / "dropped.json"
    if not путь.exists():
        return {}
    return json.loads(путь.read_text(encoding="utf-8"))


def собрать(путь_данных: Path, предел: int):
    имена = загрузить_имена()
    выброшено_человеком = отброшенные_вручную()
    чистые, отсев = [], {}
    for w in слова_по_частоте(путь_данных):
        if w in выброшено_человеком:
            отсев.setdefault("отброшено вручную", []).append(w)
            continue
        вид = разметить(w, имена)
        if вид in ВИДЫ_НА_ПЕРЕВОД:
            чистые.append((w, вид))
            if len(чистые) >= предел:
                break
        else:
            отсев.setdefault(вид, []).append(w)
    return чистые, отсев


def записать(чистые, отсев, старый):
    ДАННЫЕ.mkdir(parents=True, exist_ok=True)
    with (ДАННЫЕ / "frequency.txt").open("w", encoding="utf-8") as f:
        f.write("# ранг\tслово\tвид\tперевод\n")
        for i, (w, вид) in enumerate(чистые, 1):
            откуда = "старый" if w in старый else "нужен"
            f.write(f"{i}\t{w}\t{вид}\t{откуда}\n")
    (ДАННЫЕ / "rejected.json").write_text(
        json.dumps({k: sorted(v) for k, v in отсев.items()},
                   ensure_ascii=False, indent=1),
        encoding="utf-8")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--wordfreq", type=Path,
                   help="путь к large_en.msgpack.gz из колеса wordfreq")
    p.add_argument("--limit", type=int, default=10000, help="сколько слов собрать")
    p.add_argument("--names-from", type=Path,
                   help="папка с first-names.txt и baby-names.csv: пересобрать names.txt")
    a = p.parse_args(argv)

    if a.names_from:
        имена = собрать_имена_из_источников(a.names_from / "first-names.txt",
                                            a.names_from / "baby-names.csv")
        ДАННЫЕ.mkdir(parents=True, exist_ok=True)
        (ДАННЫЕ / "names.txt").write_text("\n".join(sorted(имена)) + "\n",
                                          encoding="utf-8")
        print(f"names.txt: {len(имена)} имён")
        if not a.wordfreq:
            return 0

    if not a.wordfreq:
        p.error("нужен --wordfreq или --names-from")

    чистые, отсев = собрать(a.wordfreq, a.limit)
    старый = старые_переводы()
    записать(чистые, отсев, старый)

    есть = [w for w, _ in чистые if w in старый]
    нужен = [(w, v) for w, v in чистые if w not in старый]
    имена_в_остатке = [w for w, v in нужен if v == "возможно имя"]

    print(f"собрано слов: {len(чистые)}")
    print(f"отсеяно: {sum(len(v) for v in отсев.values())} — "
          f"{ {k: len(v) for k, v in отсев.items()} }")
    print(f"перевод есть в прежнем словаре: {len(есть)} "
          f"({100*len(есть)/len(чистые):.1f}%)")
    print(f"перевод нужен: {len(нужен)} ({100*len(нужен)/len(чистые):.1f}%)")
    print(f"  из них помечено «возможно имя»: {len(имена_в_остатке)}")
    print(f"записано в {ДАННЫЕ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
