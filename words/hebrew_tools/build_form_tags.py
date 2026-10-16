#!/usr/bin/env python3
"""Выводит теги-формы: одно слово в разных родах и числах.

Просьба владельца: «может как раз объединить в теги — единственное и
множественное число, если есть у одного и того же слова; и ещё разные роды —
мужской, женский, если есть у одного и того же слова».

Чем это отличается от соседних генераторов. Синонимы (build_synonym_tags.py)
собирают РАЗНЫЕ слова с одним значением; здесь наоборот — ОДНО слово в разных
формах: טוֹב и טוֹבִים, יוֹדֵעַ и יוֹדַעַת. Однокоренные показывает блок
references, но он текстовый, в нём бывает по шестнадцать слов, и парадигму в
нём не видно.

Что считается формой одного слова — два механических признака, оба проверяемые:

  Число. Неогласованная форма второго слова — это форма первого плюс ים или
  ות: דבר → דברים. Приставки сюда не попадают: с ними слово начиналось бы с
  другой буквы.

  Род. Перевод совпадает слово в слово, а различается только пометой в
  скобках: «ненавижу, ненавидит» и «ненавижу, ненавидит (ж.р.)».

Отсеивается:

  Формы с приставками. בַּדָּבָר, לִדְבָרִים, שֶׁהַדָּבָר — это предлог или
  союз плюс слово, им место в своих группах, а не в парадигме.

  Одиночки. Группа из одного слова не группа.

  Слишком большие семьи. Больше шести форм — значит, правило зацепило лишнее:
  у леммы ל в словаре три разных слова, а не три формы одного.

Результат пишется в tags_forms.json рядом с ручным tags.json — файл
перегенерируется и просматривается глазами, а не собирается на лету.

Запуск:  python words/hebrew_tools/build_form_tags.py [--dry]
"""
import argparse
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data", "hebrew_freq"))
FULL = os.path.join(DATA, "hebrew_freq_10000_full.json")
OUT = os.path.join(DATA, "tags_forms.json")

LABEL = "🧬 Формы одного слова"
PLURAL_SUFFIXES = ("ים", "ות")
MAX_FORMS = 6


def bare(translation: str) -> str:
    """Перевод без помет в скобках: именно они различают род и число."""
    return re.sub(r"\s*\([^)]*\)", "", translation or "").strip().lower()


def is_plural_of(base: str, other: str) -> bool:
    return any(other == base + suffix for suffix in PLURAL_SUFFIXES)


def is_article_of(base: str, other: str) -> bool:
    """Форма с определённым артиклем: הַזְּמַן при זְמַן."""
    return other == "ה" + base


def words_of(translation: str):
    return [w for w in re.split(r"[^\w-]+", bare(translation)) if len(w) > 1]


def related(base: str, other: str) -> bool:
    """Переводы говорят об одном и том же.

    Нужно потому, что неогласованные формы разных слов совпадают: עד — это и
    «до» (עַד), и основа «свидетеля» (עֵד), и правило «форма плюс ים» без этой
    проверки объявляло עֵדִים «свидетели» множественным числом предлога «до».

    Сравниваем по началу слов: «вещь» и «вещи», «хороший» и «хорошие»,
    «момент» и «моменты» совпадают первыми буквами, а «до» и «свидетели» — нет.
    """
    for a in words_of(base):
        for b in words_of(other):
            if len(a) < 3 or len(b) < 3:
                continue
            common = 0
            for x, y in zip(a, b):
                if x != y:
                    break
                common += 1
            # Трёх букв довольно: русские формы расходятся как раз в окончании
            # — «любит» и «любят», «знает» и «знают», «вещь» и «вещи». Требовать
            # четырёх значило бы терять ровно те пары, ради которых всё и
            # затевалось.
            if common >= 3:
                return True
    return False


def family(rows):
    """Слова одной леммы, от частого к редкому."""
    by_lemma = collections.defaultdict(list)
    for r in rows:
        if r.get("lemma"):
            by_lemma[r["lemma"]].append(r)
    for lemma, fam in by_lemma.items():
        yield lemma, sorted(fam, key=lambda r: r["rank"])


def forms_of(fam):
    """Формы самого частого слова семьи: его множественное число и род.

    Отсчёт ведём от самого частого — он и есть словарная форма. Иначе за
    основу мог бы попасть редкий вариант, и парадигма строилась бы от него.

    Возвращает (состав, формы с артиклем). Артиклевые в состав не входят — по
    общему правилу словаря: тег они получают и группу показывают, но своей
    строки не имеют, иначе в парадигме «время» стояло бы дважды.
    """
    base = fam[0]
    out = [base]
    article = []
    for other in fam[1:]:
        if is_article_of(base["hebrew"], other["hebrew"]):
            article.append(other)
            continue
        same_number = (bare(other["russian"]) == bare(base["russian"])
                       and other["russian"] != base["russian"])
        plural = (is_plural_of(base["hebrew"], other["hebrew"])
                  # Множественное число женского рода: מוֹרָה → מוֹרוֹת. Основа
                  # женского рода сама может быть формой базового слова.
                  or any(is_plural_of(f["hebrew"], other["hebrew"]) for f in out[1:]))
        if (plural or same_number) and related(base["russian"], other["russian"]):
            out.append(other)
    return out, article


def build(rows):
    tags = {}
    for lemma, fam in family(rows):
        if len(fam) < 2:
            continue
        forms, article = forms_of(fam)
        if len(forms) < 2 or len(forms) > MAX_FORMS:
            continue
        name = f"формы: {bare(forms[0]['russian'])}"
        if name in tags:
            # Два слова с одинаковым первым значением — различаем леммой,
            # иначе одна группа молча затёрла бы другую.
            name = f"{name} ({lemma})"
        tags[name] = {
            "label": LABEL,
            "note": "по словарной форме: сначала она, потом род и множественное число",
            "sort": "ручной",
            "members": [f["rank"] for f in forms],
            "also": [f["rank"] for f in article],
        }
    return tags


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--show", type=int, default=15, help="сколько групп показать")
    args = ap.parse_args()

    with open(FULL, encoding="utf-8") as fh:
        rows = json.load(fh)
    by_rank = {r["rank"]: r for r in rows}
    tags = build(rows)

    covered = {rk for spec in tags.values() for rk in spec["members"]}
    print(f"  групп форм: {len(tags)}, слов в них: {len(covered)}")
    shown = sorted(tags.items(), key=lambda kv: min(kv[1]["members"]))[:args.show]
    for name, spec in shown:
        forms = ", ".join(
            f"{by_rank[rk]['hebrew']}#{rk} {by_rank[rk]['russian'][:22]}"
            for rk in spec["members"])
        print(f"    {name:<28} {forms}")

    if args.dry:
        print("\n[--dry] не записано")
        return 0
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"_": ["Сгенерировано build_form_tags.py — правьте генератор, не файл."],
                   "tags": tags}, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)
    print(f"\nзаписано: {os.path.relpath(OUT, os.path.join(HERE, '..', '..'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
