#!/usr/bin/env python3
"""Чтение определений тегов — общее для разметки и для сборки групп.

Зачем отдельным модулем. Порядок участников нужен обоим скриптам: apply_tags
пишет его в слово, build_tag_groups раскладывает по нему строки таблицы. Пока
правило жило в двух местах, оно могло разъехаться молча — карточка показывала бы
один порядок, а поле order говорило другое.

Порядок задаётся полем "sort":
    "ручной" — как перечислено в members. Только там, где порядок ОЧЕВИДЕН
               читателю: числа по значению, единицы времени по длительности,
               лица глагола по парадигме.
    "ранг"   — по номеру в частотном словаре. Для групп, где никакого
               естественного порядка нет: части тела, родственники,
               вопросительные слова. Выдуманная последовательность там хуже
               отсутствия: читатель ищет в ней смысл, которого нет.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data", "hebrew_freq"))
TAGS = os.path.join(DATA, "tags.json")
# Синонимы выводятся из словаря механически (build_synonym_tags.py), а не
# курируются: их 138 групп, и вручную такое не ведут. Лежат отдельным файлом,
# чтобы результат генератора можно было просмотреть и сравнить, а не собирать
# на лету при каждом запуске.
AUTO = os.path.join(DATA, "tags_synonyms.json")

SORTS = ("ручной", "ранг")


def load_tags(path: str = TAGS, auto: str = AUTO) -> dict:
    """Определения тегов с участниками, уже расставленными в порядке показа.

    Ручные и выведенные объединяются: слово может попасть и в курированную
    группу, и в синонимический ряд — это разные поводы для повторения.
    """
    with open(path, encoding="utf-8") as fh:
        defs = json.load(fh)["tags"]
    if auto and os.path.exists(auto):
        with open(auto, encoding="utf-8") as fh:
            for name, spec in json.load(fh)["tags"].items():
                if name in defs:
                    raise ValueError(f"тег {name!r} задан и вручную, и генератором")
                defs[name] = spec
    for tag, spec in defs.items():
        sort = spec.get("sort", "ручной")
        if sort not in SORTS:
            raise ValueError(f"{tag}: неизвестный порядок {sort!r}, ожидалось {SORTS}")
        if sort == "ранг":
            spec["members"] = sorted(spec["members"])
    return defs
