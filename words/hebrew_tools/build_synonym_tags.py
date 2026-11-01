#!/usr/bin/env python3
"""Выводит теги-синонимы из словаря: разные слова с одним значением.

Чем это отличается от остальных тегов. Числительные и родственники курируются
вручную — состав и порядок задаёт человек. Синонимы курировать нельзя, их
слишком много, зато они выводятся механически: у двух записей совпадает первое
значение перевода.

Наивное сравнение даёт половину мусора, поэтому отсеиваются три вещи.

  Формы одного слова. אותו и אותה — не синонимы, а падежные формы, и
  однокоренные показывает свой блок. Сравниваем по леммам, по одному
  представителю на лемму.

  Род и лицо. «они (м)» и «они (ж)» — הם и הן — разные слова, а не синонимы.
  Поэтому пометы в скобках НЕ срезаются: они и различают такие пары.

  Варианты написания. דיוויד, דייויד, דיויד — одно имя, записанное по-разному
  (ktiv male). Отсеиваются похожие написания и все имена собственные.

Результат пишется в tags_synonyms.json рядом с ручным tags.json — файл
перегенерируется и просматривается глазами, а не собирается на лету.

Запуск:  python words/hebrew_tools/build_synonym_tags.py [--dry]
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data", "hebrew_freq"))
FULL = os.path.join(DATA, "hebrew_freq_10000_full.json")
OUT = os.path.join(DATA, "tags_synonyms.json")

# Подпись говорит ровно то, по чему собрана группа: совпал ПЕРЕВОД. Раньше
# стояло «То же значение», и это был перебор — особенно после того, как
# значение стало кончаться и на запятой. Так в один ряд попадают יש «есть,
# имеется» и לאכול «есть» (кушать): значение разное, перевод один. Для
# пик-режима это и нужно — такие варианты человек не различит, подставлять их
# вместе нельзя; а на карточке обещать «то же значение» было бы неправдой.
LABEL = "🔗 Тот же перевод"


def sense(translation: str) -> str:
    """Первое значение, вместе с пометами: они и различают род и лицо.

    Где кончается значение. Разделителей два — «;» и «,», — и это должно
    совпадать с meanings_of() в quiz_service: там отвлекающие отсеиваются по
    пересечению значений. Пока здесь резали только по «;», два места понимали
    «значение» по-разному и расходились на живых словах: «как» (#44) и «как,
    подобно» (#47) для фильтра отвлекающих были одним значением, а для
    построителя тегов — разными, и ряд не собирался. Владелец заметил это
    сам: «komo и eih — хорошо бы объединить в общий тег».

    Запятая внутри скобок разделителем не считается. Пометы в скобках как раз
    и различают пары вроде «они (м)» и «они (ж)», и разрезать их нельзя.
    """
    head = _until_separator(translation or "")
    return head.strip().lower()


def _until_separator(text: str) -> str:
    """Кусок до первой «;» или «,», не считая те, что внутри скобок."""
    depth = 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch in ";," and depth == 0:
            return text[:i]
    return text


def lemma_of(row: dict) -> str:
    lemma = (row.get("lemma") or "").strip()
    if lemma:
        return lemma
    word = row.get("hebrew", "")
    # Определённый артикль ה превращает слово в «то же самое с артиклем».
    return word[1:] if word.startswith("ה") and len(word) > 2 else word


MATRES = "אהוי"   # матери чтения: пишутся или нет по орфографической традиции


def skeleton(word: str) -> str:
    """Согласный костяк: без артикля и без матерей чтения.

    Именно они и различают варианты написания одного слова — מאלה и מאלו,
    אימא и האמא. Сравнение подпоследовательностью такие пары не ловило:
    буквы не вставлены, а заменены.
    """
    return "".join(ch for ch in word if ch not in MATRES)


def _edit_distance_le_1(a: str, b: str) -> bool:
    if abs(len(a) - len(b)) > 1:
        return False
    if a == b:
        return True
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    i = j = 0
    used = False
    while i < len(short) and j < len(long):
        if short[i] == long[j]:
            i += 1
            j += 1
            continue
        if used:
            return False
        used = True
        j += 1
        if len(short) == len(long):
            i += 1
    return True


def same_spelling(a: str, b: str) -> bool:
    """Одно слово, записанное по-разному."""
    sa, sb = skeleton(a), skeleton(b)
    # Слова целиком из матерей чтения костяка не имеют (הוא, היא) — там сравнивать
    # нечего, сравниваем как есть. Костяк из одной буквы уже показателен: אימא и
    # האמא обе дают «מ», и это одно слово с артиклем.
    if not sa or not sb:
        return a == b
    if sa == sb:
        return True
    # Род и число одного слова: כּוֹאֵב и כּוֹאֶבֶת дают костяки «כב» и «כבת».
    # По лемме такое не поймать — у женской формы в словаре леммой записана
    # мужская, а не корень.
    for suffix in ("ת", "ם", "ן", "תם", "תן"):
        if sa == sb + suffix or sb == sa + suffix:
            return True
    # Расхождение в одну букву считаем опиской только у костяков подлиннее.
    # У двухбуквенных это половина слова: בלי и ללא дают «בל» и «לל», а это
    # разные слова, оба означающие «без», — настоящая синонимическая пара.
    return len(sa) >= 3 and len(sb) >= 3 and _edit_distance_le_1(sa, sb)


def is_proper_name(translation: str) -> bool:
    """Имя собственное: перевод с заглавной буквы.

    Значения pos="имя" в словаре нет вовсе — часть речи у имён стоит «сущ», и
    прежний фильтр по ней был мёртвым кодом. Зато переводы у всех остальных
    слов строчные, а «Том», «Говард», «Диана» — с заглавной.
    """
    head = (translation or "").strip()
    return bool(head) and head[0].isupper()


def curated_membership(path: str = None) -> dict:
    """Ранг → множество ручных тегов, в которых он уже состоит."""
    path = path or os.path.join(DATA, "tags.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        manual = json.load(fh)["tags"]
    out = collections.defaultdict(set)
    for name, spec in manual.items():
        for rank in list(spec.get("members", [])) + list(spec.get("also", [])):
            out[rank].add(name)
    return out


def already_together(words: list, curated: dict) -> bool:
    """
    Все участники уже стоят рядом в одной ручной группе — тогда синонимический
    ряд ничего не добавляет, а на карточке появляется вторым блоком с тем же
    содержимым. Так было у «здесь», «сюда», «отсюда», «назад»: все они и так
    лежат в «Здесь, сюда, отсюда».
    """
    if not curated:
        return False
    sets = [curated.get(w["rank"], set()) for w in words]
    return bool(set.intersection(*sets)) if all(sets) else False


def build(rows: list, curated: dict = None) -> dict:
    by_sense = collections.defaultdict(list)
    for row in rows:
        if is_proper_name(row.get("russian", "")):   # имена синонимов не образуют
            continue
        key = sense(row.get("russian", ""))
        if len(key) > 1:
            by_sense[key].append(row)

    tags = {}
    for key, words in by_sense.items():
        per_lemma = {}
        for w in words:
            per_lemma.setdefault(lemma_of(w), w)
        kept = []
        for w in sorted(per_lemma.values(), key=lambda x: x["rank"]):
            if any(same_spelling(w["hebrew"], k["hebrew"]) for k in kept):
                continue
            kept.append(w)
        if len(kept) > 1 and not already_together(kept, curated):
            tags[f"синонимы: {key}"] = {
                "label": LABEL,
                "note": "по частотности: между синонимами естественного порядка нет",
                "sort": "ранг",
                # Участники ряда годятся друг за друга как ответ — ряд и
                # собран по совпадению значения. В пик-режиме подставлять их
                # вариантами нельзя: у вопроса окажется два верных ответа, а
                # человек получит «Неверно» за правильный по смыслу выбор.
                "взаимозаменяемы": True,
                "members": sorted(w["rank"] for w in kept),
                "also": [],
            }
    return tags


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--show", type=int, default=12, help="сколько групп показать")
    args = ap.parse_args()

    with open(FULL, encoding="utf-8") as fh:
        rows = json.load(fh)
    by_rank = {r["rank"]: r for r in rows}
    tags = build(rows, curated_membership())

    covered = {rk for spec in tags.values() for rk in spec["members"]}
    print(f"  групп синонимов: {len(tags)}, слов в них: {len(covered)}")
    shown = sorted(tags.items(), key=lambda kv: min(kv[1]["members"]))[:args.show]
    for name, spec in shown:
        forms = ", ".join(f"{by_rank[rk]['hebrew']}#{rk}" for rk in spec["members"])
        print(f"    {name[10:]:<26} {forms}")

    if args.dry:
        print("\n[--dry] не записано")
        return 0
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"_": ["Сгенерировано build_synonym_tags.py — правьте генератор, не файл."],
                   "tags": tags}, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)
    print(f"\nзаписано: {os.path.relpath(OUT, os.path.join(HERE, '..', '..'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
