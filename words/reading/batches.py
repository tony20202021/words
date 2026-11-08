#!/usr/bin/env python3
"""Порции слов на сочинение предложений и приём сочинённого.

Предложения пишутся вручную порциями — как переводы для словаря английского.
Машина здесь не сочиняет, а СТОРОЖИТ: на приёме каждое предложение проверяется
на состав, и негодное не принимается. Без этой проверки затея разваливается
тихо — одно незнакомое слово превращает понятный вход в непонятный, а заметить
это в потоке из сотен предложений нельзя.

Данные лежат рядом со словарями: words/data/reading/<код языка>/sentences.json,
ключ — номер слова, значение — список {text, ru}.

Примеры:
    python reading/batches.py next --language en --from 1 --to 50 --size 10
    python reading/batches.py add --language en --file порция.json
    python reading/batches.py status --language en
"""
import argparse
import json
import sys
from pathlib import Path

ТУТ = Path(__file__).resolve().parent
sys.path.insert(0, str(ТУТ))

from check import ключ_повтора, проверить, слова_текста  # noqa: E402
from vocabulary import без_огласовок, собрать            # noqa: E402

ДАННЫЕ = ТУТ.parents[0] / "data" / "reading"
ЯЗЫКИ = {"en": "Английский", "he": "Иврит"}

# Сколько слов показывать в порции целиком. Для малых номеров список короткий
# и нужен весь; для больших он бесполезен — там и так разрешено почти всё
# частотное, а три тысячи слов в порции только мешают.
ПОКАЗЫВАТЬ_ЦЕЛИКОМ = 150


def слова_языка(код: str) -> list:
    """Слова из базы: номер, написание, лемма, перевод."""
    from pymongo import MongoClient
    db = MongoClient("mongodb://localhost:8527",
                     serverSelectionTimeoutMS=5000)["language_learning_bot"]
    язык = db.languages.find_one({"name_ru": ЯЗЫКИ[код]})
    if not язык:
        raise SystemExit(f"языка {ЯЗЫКИ[код]!r} в базе нет")
    поля = {"word_number": 1, "word_foreign": 1, "lemma": 1, "translation": 1}
    return sorted(db.words.find({"language_id": язык["_id"]}, поля),
                  key=lambda w: w["word_number"])


def файл(код: str) -> Path:
    return ДАННЫЕ / код / "sentences.json"


def читать(код: str) -> dict:
    п = файл(код)
    return json.loads(п.read_text(encoding="utf-8")) if п.exists() else {}


def писать(код: str, данные: dict) -> None:
    п = файл(код)
    п.parent.mkdir(parents=True, exist_ok=True)
    п.write_text(json.dumps(данные, ensure_ascii=False, indent=1,
                            sort_keys=lambda: None) if False else
                 json.dumps({k: данные[k] for k in sorted(данные, key=int)},
                            ensure_ascii=False, indent=1) + "\n",
                 encoding="utf-8")


def команда_next(a):
    слова = слова_языка(a.language)
    готово = читать(a.language)

    ждут = [w for w in слова
            if a.first <= w["word_number"] <= (a.last or 10 ** 9)
            and str(w["word_number"]) not in готово]
    порция = ждут[:a.size]
    if not порция:
        print("в этом отрезке сочинять больше нечего")
        return 0

    граница = max(порция[-1]["word_number"], a.always)
    доступные = [w for w in слова if w["word_number"] <= граница]

    print(f"# язык: {ЯЗЫКИ[a.language]}, слов в порции: {len(порция)}, "
          f"ещё ждут: {len(ждут) - len(порция)}")
    print(f"# разрешены слова с номером не больше {граница} "
          f"(нижняя граница {a.always})")
    print(f"# нужно {a.count} предложений на слово; перевод обязателен")
    print()
    if len(доступные) <= ПОКАЗЫВАТЬ_ЦЕЛИКОМ:
        print("# ВЕСЬ доступный словарь:")
        print("# " + " ".join(w["word_foreign"] for w in доступные))
        print()
    else:
        последние = доступные[-40:]
        print(f"# доступно {len(доступные)} слов; последние сорок "
              f"(их легче всего забыть):")
        print("# " + " ".join(w["word_foreign"] for w in последние))
        print()
    print(f"# уже сочинено предложений: {sum(len(v) for v in готово.values())}; "
          f"повторы запрещены — одна фраза живёт в файле один раз")
    print()
    for w in порция:
        print(f"{w['word_number']}\t{w['word_foreign']}\t{w.get('translation', '')}")
    return 0


def команда_add(a):
    """Принимает {"номер": [{"text": ..., "ru": ...}]} с проверкой состава."""
    сырое = json.loads(Path(a.file).read_text(encoding="utf-8")) if a.file \
        else json.loads(sys.stdin.read())
    слова = слова_языка(a.language)
    по_номеру = {w["word_number"]: w for w in слова}
    готово = читать(a.language)

    # Повторы запрещены по всему файлу, а не только внутри слова: одна и та
    # же фраза годится сразу для нескольких слов, и без этой проверки
    # «I know you» встанет и к you, и к i, и к know.
    занятые = {}
    for ключ_слова, список in готово.items():
        for п in список:
            занятые[ключ_повтора(п["text"], a.language)] = ключ_слова

    принято, отвергнуто, оговорки = 0, [], []
    for ключ, предложения in сырое.items():
        номер = int(ключ)
        слово = по_номеру.get(номер)
        if not слово:
            отвергнуто.append((ключ, "—", f"слова №{номер} в языке нет"))
            continue

        словарь = собрать(слова, до_номера=номер, всегда_первые=a.always,
                          язык=a.language)
        годные = []
        for п in предложения:
            текст = (п.get("text") or "").strip()
            перевод = (п.get("ru") or "").strip()
            if not текст or not перевод:
                отвергнуто.append((ключ, текст[:40], "пустой текст или перевод"))
                continue
            повтор = ключ_повтора(текст, a.language)
            if повтор in занятые:
                отвергнуто.append((ключ, текст[:40],
                                   f"повтор: уже есть у слова №{занятые[повтор]}"))
                continue

            итог = проверить(текст, слово["word_foreign"], словарь)
            if итог.годится:
                годные.append({"text": текст, "ru": перевод})
                занятые[повтор] = ключ
                if итог.поздние:
                    оговорки.append((ключ, текст[:40], итог.оговорки()))
            else:
                отвергнуто.append((ключ, текст[:40], итог.объясни()))

        if годные:
            готово[ключ] = готово.get(ключ, []) + годные
            принято += len(годные)

    писать(a.language, готово)
    print(f"принято предложений: {принято}")
    if оговорки:
        # Не брак: предложение понятно. Но знать про это надо.
        print(f"с оговоркой: {len(оговорки)}")
        for номер, текст, что in оговорки:
            print(f"  №{номер} «{текст}» — {что}")
    if отвергнуто:
        print(f"ОТВЕРГНУТО: {len(отвергнуто)}")
        for номер, текст, причина in отвергнуто[:20]:
            print(f"  №{номер} «{текст}» — {причина}")
        return 1
    return 0


def команда_audit(a):
    """Перепроверка всего, что уже лежит в файле.

    Приём проверяет порцию в момент приёма — но правила с тех пор менялись
    (запрет повторов появился, когда предложений было уже сто десять), да и
    словарь в базе мог поехать. Поэтому нужна команда, которая перепроверяет
    всё с нуля и отвечает одним числом: сколько нарушений.

    Выводится ещё и наибольший использованный номер. Он отвечает на главный
    вопрос затеи — «все ли слова в пределах разрешённого» — одной строкой.
    """
    слова = слова_языка(a.language)
    по_номеру = {w["word_number"]: w for w in слова}
    готово = читать(a.language)

    нарушения, оговорки = [], []
    занятые = {}
    наибольший = наибольший_любой = 0
    всего = 0

    for ключ in sorted(готово, key=int):
        номер = int(ключ)
        слово = по_номеру.get(номер)
        if not слово:
            нарушения.append((ключ, "—", f"слова №{номер} в языке больше нет"))
            continue
        словарь = собрать(слова, до_номера=номер, всегда_первые=a.always,
                          язык=a.language)
        for п in готово[ключ]:
            всего += 1
            текст = п["text"]
            итог = проверить(текст, слово["word_foreign"], словарь)
            if not итог.годится:
                нарушения.append((ключ, текст[:40], итог.объясни()))
            if итог.поздние:
                оговорки.append((ключ, текст[:40], итог.оговорки()))
            повтор = ключ_повтора(текст, a.language)
            if повтор in занятые:
                нарушения.append((ключ, текст[:40],
                                  f"повтор: такое же у слова №{занятые[повтор]}"))
            else:
                занятые[повтор] = ключ
            # Наибольший номер считается ДВАЖДЫ, и это не прихоть. Одна
            # цифра тут врёт: приставочная форма שכאן стоит в словаре под
            # №4619, и строка «наибольший номер 4619» пугает, хотя в тексте
            # всего-то ש + כאן (№35). Поэтому отдельно — по словам, узнанным
            # своей статьёй, и отдельно — с приставочными формами.
            for т in слова_текста(текст):
                свой = словарь.свой_номер(т)
                if not свой:
                    continue
                наибольший_любой = max(наибольший_любой, свой)
                путь, _ = словарь.опознать(т)
                if путь in ("точно", "лемма"):
                    наибольший = max(наибольший, свой)

    print(f"язык: {ЯЗЫКИ[a.language]}")
    print(f"  предложений проверено:   {всего}")
    print(f"  различных:               {len(занятые)}")
    # Предел у каждого слова свой: его собственный номер, но не ниже нижней
    # границы. Печатать одно число («предел 100») значило бы врать: для слова
    # №300 разрешены все триста.
    print(f"  наибольший номер слова:  {наибольший}")
    print(f"  предел:                  номер слова, но не меньше {a.always}")
    if наибольший_любой > наибольший:
        print(f"    с приставочными формами: {наибольший_любой} — "
              f"это их собственные статьи, а не чужие слова в тексте")
    print(f"  нарушений:               {len(нарушения)}")
    for номер, текст, причина in нарушения:
        print(f"    №{номер} «{текст}» — {причина}")
    if оговорки:
        print(f"  с оговоркой (не брак):   {len(оговорки)}")
        for номер, текст, что in оговорки:
            print(f"    №{номер} «{текст}» — {что}")
    return 1 if нарушения else 0


def команда_status(a):
    слова = слова_языка(a.language)
    готово = читать(a.language)
    всего_слов = len(слова)
    со_словами = len(готово)
    всего_предложений = sum(len(v) for v in готово.values())
    print(f"язык: {ЯЗЫКИ[a.language]}")
    print(f"  слов в языке:          {всего_слов}")
    print(f"  слов с предложениями:  {со_словами}")
    print(f"  предложений всего:     {всего_предложений}")
    if со_словами:
        номера = sorted(int(k) for k in готово)
        print(f"  покрытый отрезок:      №{номера[0]}–{номера[-1]}")
    return 0


def main(argv=None):
    # Общие ключи наследуются подкомандами: иначе их пришлось бы ставить
    # ПЕРЕД подкомандой, что запоминается ровно до первой ошибки.
    общий = argparse.ArgumentParser(add_help=False)
    общий.add_argument("--language", choices=sorted(ЯЗЫКИ), default="en")
    общий.add_argument("--always", type=int, default=100,
                       help="слова до этого номера разрешены всегда")

    p = argparse.ArgumentParser(description=__doc__, parents=[общий],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    под = p.add_subparsers(dest="что", required=True)

    n = под.add_parser("next", parents=[общий], help="следующая порция слов")
    n.add_argument("--from", dest="first", type=int, default=1)
    n.add_argument("--to", dest="last", type=int, default=0)
    n.add_argument("--size", type=int, default=10)
    n.add_argument("--count", type=int, default=5,
                   help="сколько предложений нужно на слово")
    n.set_defaults(func=команда_next)

    a_ = под.add_parser("add", parents=[общий], help="принять сочинённое")
    a_.add_argument("--file")
    a_.set_defaults(func=команда_add)

    u = под.add_parser("audit", parents=[общий],
                       help="перепроверить всё уже сочинённое")
    u.set_defaults(func=команда_audit)

    s = под.add_parser("status", parents=[общий], help="сколько сделано")
    s.set_defaults(func=команда_status)

    a = p.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
