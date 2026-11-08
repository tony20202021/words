#!/usr/bin/env python3
"""Порции на перевод и приём переведённого.

Остаток, который прежний словарь не закрывает, переводится вручную — порциями
по двести-триста слов. Руками же делается и последний отсев: имена, оставшиеся
после фильтров, междометия и осколки видно только глазами.

Накопленное живёт в двух файлах рядом со списком:
    translations.json — слово → список переводов;
    dropped.json      — слово → причина, по которой оно выброшено.

Слово обязано попасть ровно в один из них, иначе порция «переведена», а слова
в словаре нет: тихая пропажа, ровно та, против которой заведены сторожа.

Примеры:
    python batches.py next --size 250                 # следующая порция
    python batches.py add --file порция.json          # принять переведённое
    python batches.py status                          # сколько осталось
"""
import argparse
import json
import sys
from pathlib import Path

ТУТ = Path(__file__).resolve().parent
ДАННЫЕ = ТУТ.parents[0] / "data" / "eng_freq"
СПИСОК = ДАННЫЕ / "frequency.txt"
ПЕРЕВОДЫ = ДАННЫЕ / "translations.json"
ОТБРОШЕНО = ДАННЫЕ / "dropped.json"


def читать_список():
    """[(ранг, слово, вид, откуда перевод)] в порядке частоты."""
    out = []
    for l in СПИСОК.read_text(encoding="utf-8").splitlines():
        if not l or l.startswith("#"):
            continue
        ранг, слово, вид, откуда = l.split("\t")
        out.append((int(ранг), слово, вид, откуда))
    return out


def _читать(путь) -> dict:
    if not путь.exists():
        return {}
    return json.loads(путь.read_text(encoding="utf-8"))


def _писать(путь, d):
    путь.write_text(json.dumps(d, ensure_ascii=False, indent=1, sort_keys=True)
                    + "\n", encoding="utf-8")


def осталось():
    переводы, отброшено = _читать(ПЕРЕВОДЫ), _читать(ОТБРОШЕНО)
    готово = set(переводы) | set(отброшено)
    return [(р, w, v) for р, w, v, откуда in читать_список()
            if откуда == "нужен" and w not in готово]


ОКОНЧАНИЯ = (("ies", "y"), ("es", ""), ("s", ""), ("ing", ""), ("ing", "e"),
             ("ed", ""), ("ed", "e"), ("er", ""), ("est", ""), ("ly", ""),
             ("ning", "n"), ("tting", "t"), ("pping", "p"), ("mming", "m"))


def возможная_основа(w: str, все: set):
    """Грубая обратная морфология — подсказка, а не приговор.

    Она ошибается в обе стороны: «shower» выводит из «show», «flower» из
    «flow», «cares» из «car». Поэтому это только пометка в порции; решает
    человек, глядя на смысл.
    """
    for к, зам in ОКОНЧАНИЯ:
        if w.endswith(к) and len(w) - len(к) >= 3:
            основа = w[:len(w) - len(к)] + зам
            if основа in все:
                return основа
    return None


def команда_next(a):
    ждут = осталось()
    порция = ждут[:a.size]
    if not порция:
        print("переводить больше нечего")
        return 0
    print(f"# порция: {len(порция)} слов, осталось всего {len(ждут)}")
    print(f"# ранги {порция[0][0]}–{порция[-1][0]}")
    print("# пометки: «имя?» — решить, слово это или имя;")
    print("#          «форма от X?» — возможно, дубль уже имеющегося слова")
    все = {w for _, w, _, _ in читать_список()}
    for ранг, w, вид in порция:
        пометки = []
        if вид == "возможно имя":
            пометки.append("имя?")
        основа = возможная_основа(w, все)
        if основа:
            пометки.append(f"форма от {основа}?")
        хвост = ("   ← " + ", ".join(пометки)) if пометки else ""
        print(f"{ранг}\t{w}{хвост}")
    return 0


def команда_add(a):
    """Принимает {"слово": ["перевод", ...]} и {"слово": "причина"} вместе."""
    сырое = json.loads(Path(a.file).read_text(encoding="utf-8")) if a.file \
        else json.loads(sys.stdin.read())
    в_списке = {w for _, w, _, откуда in читать_список() if откуда == "нужен"}
    переводы, отброшено = _читать(ПЕРЕВОДЫ), _читать(ОТБРОШЕНО)

    новых, выброшено, беды = 0, 0, []
    for w, значение in сырое.items():
        if w not in в_списке:
            беды.append(f"«{w}» не числится ждущим перевода")
            continue
        if isinstance(значение, str):           # причина отсева
            отброшено[w] = значение
            выброшено += 1
        elif isinstance(значение, list) and значение and all(
                isinstance(x, str) and x.strip() for x in значение):
            переводы[w] = значение
            новых += 1
        else:
            беды.append(f"«{w}»: перевод должен быть непустым списком строк")

    if беды:
        for b in беды:
            print("ОШИБКА:", b, file=sys.stderr)
        return 1

    _писать(ПЕРЕВОДЫ, переводы)
    _писать(ОТБРОШЕНО, отброшено)
    print(f"принято: {новых} переводов, {выброшено} отброшено")
    print(f"осталось: {len(осталось())}")
    return 0


def команда_status(a):
    список = читать_список()
    из_старого = sum(1 for *_, откуда in список if откуда == "старый")
    нужен = len(список) - из_старого
    переводы, отброшено = _читать(ПЕРЕВОДЫ), _читать(ОТБРОШЕНО)
    ждут = осталось()

    print(f"список:            {len(список)} слов")
    print(f"из прежнего словаря: {из_старого}")
    print(f"нужен перевод:       {нужен}")
    print(f"  переведено вручную: {len(переводы)}")
    print(f"  отброшено вручную:  {len(отброшено)}")
    print(f"  осталось:           {len(ждут)}")
    if ждут:
        print(f"следующее слово: {ждут[0][1]} (ранг {ждут[0][0]})")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    под = p.add_subparsers(dest="что", required=True)

    n = под.add_parser("next", help="напечатать следующую порцию")
    n.add_argument("--size", type=int, default=250)
    n.set_defaults(func=команда_next)

    a_ = под.add_parser("add", help="принять переведённое")
    a_.add_argument("--file", help="файл JSON; без него читается ввод")
    a_.set_defaults(func=команда_add)

    s = под.add_parser("status", help="сколько сделано и сколько осталось")
    s.set_defaults(func=команда_status)

    a = p.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
