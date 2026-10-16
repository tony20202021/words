#!/usr/bin/env python3
"""Собирает по проставленным тегам готовые к показу группы — поле tag_groups.

Зачем отдельным проходом. Тег на слове говорит только «оно из этой группы».
Чтобы показать группу на карточке, нужен весь её состав в нужном порядке, а он
разбросан по словарю: «один» на 40-м месте, «десять» на 890-м. Собирать это на
каждый показ — лишняя работа сервера, а собирать в трёх клиентах — три копии
знания. Поэтому группа складывается здесь, один раз.

В запись кладётся:
    "tag_groups": [{"tag": "...", "label": "...", "rows": [
        {"rank": 40, "ru": "один", "ipa": "ʔeˈχad", "foreign": "אֶחָד", "self": false}]}]

Строки из "also" в состав не входят: формы с артиклем ה, притяжательные и формы
по родам получают тег и показывают группу, но сами в ней не значатся — иначе
«родственники» содержали бы «ребёнок» трижды.

Исключение — само открытое слово. Если оно из "also", в его собственной таблице
не было ни одной строки с self, и на вопрос «а где тут я» таблица не отвечала:
слово 80 «могу (ж)» не находило себя среди модальных. Поэтому своя строка
добавляется всегда, и ставится сразу за представителем той же леммы — «могу (ж)»
идёт за «могу (м)», а не уезжает по рангу в середину списка.

Запуск:  python words/hebrew_tools/build_tag_groups.py [--dry]
"""
import argparse
import json
import os
import re
import sys

from tag_defs import load_tags

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data", "hebrew_freq"))
FULL = os.path.join(DATA, "hebrew_freq_10000_full.json")
TAGS = os.path.join(DATA, "tags.json")


def primary(translation: str) -> str:
    """Первое значение: в колонке таблицы длинному перечислению не место."""
    head = (translation or "").split(";")[0].strip()
    return head or (translation or "").strip()


def own_row(r):
    """Строка самого открытого слова — для таблицы, где его нет в составе."""
    return {
        "rank": r["rank"],
        "ru": primary(r.get("russian", "")),
        "ipa": r.get("ipa", ""),
        "foreign": r.get("niqqud") or r.get("hebrew", ""),
        "self": True,
    }


def senses(ru):
    """Значения перевода как множество: «это, эта (ж)» → {«это», «эта»}.

    Пометки в скобках — род, число, стиль — отбрасываем: они различают формы
    одного значения, а здесь ищут как раз форму того же значения.
    """
    out = set()
    for part in (ru or "").split(","):
        part = re.sub(r"\([^)]*\)", "", part).strip()
        if part:
            out.add(part)
    return out


def insert_own(rows_out, own, by_rank, lemma, sort):
    """Поставить свою строку рядом с тем, на кого она похожа.

    По рангу вставлять нельзя: «могу (ж)» (80) уехала бы за «нужно» (43) и
    оторвалась от «могу (м)» (29). Ищем соседа по смыслу, в три захода:

    1. Та же лемма И общее значение — ровно та строка, рядом с которой её и
       ищут: «этот (м) הַזֶּה» встаёт за «это, этот זֶה», «могу (ж)» за
       «могу (м)».
    2. Просто та же лемма, считая с конца — как было раньше. Так базовая форма
       парадигмы («для, ради בִּשְׁבִיל») остаётся в хвосте своего ряда, а не
       вклинивается между «для меня» и «для меня».
    3. Общее значение при другой лемме — книжное «эти הַלָּלוּ» (лемма הללו)
       родни по лемме в таблице не имеет, но место его очевидно: среди
       остальных «эти».

    Почему одной леммы мало. Поиск шёл только с конца и брал ПОСЛЕДНЮЮ строку
    с той же леммой. У леммы זה в указательных местоимениях есть и «это, этот»,
    и «такой» (כָּזֶה) — и «этот (м)» уезжало в хвост, к «такой», а «эти
    הָאֵלֶּה» вставало под «такие». Таблица на вопрос «где тут я» отвечала
    неправдой.

    Если не нашлось никого, для групп с порядком по рангу встраиваем по рангу,
    а для ручных дописываем в конец: ручной порядок задан смыслом (числа по
    значению), и вклинивать в него по номеру частотности нельзя.
    """
    own_senses = senses(own.get("ru"))

    def lemma_of(row):
        return by_rank.get(row["rank"], {}).get("lemma")

    def after_block(match):
        """За подходящими строками — за всем их подряд идущим блоком сразу.

        Не за первой: у числительных «три (м)» и «три (ж)» идут рядом, и своя
        строка должна встать после обеих, а не между ними.
        """
        start = next((i for i, row in enumerate(rows_out) if match(row)), None)
        if start is None:
            return None
        end = start
        while end + 1 < len(rows_out) and match(rows_out[end + 1]):
            end += 1
        return rows_out[:end + 1] + [own] + rows_out[end + 1:]

    def after_last(match):
        for i in range(len(rows_out) - 1, -1, -1):
            if match(rows_out[i]):
                return rows_out[:i + 1] + [own] + rows_out[i + 1:]
        return None

    attempts = (
        (after_block, lambda row: bool(lemma) and lemma_of(row) == lemma
                                  and bool(senses(row["ru"]) & own_senses)),
        (after_last,  lambda row: bool(lemma) and lemma_of(row) == lemma),
        (after_block, lambda row: bool(senses(row["ru"]) & own_senses)),
    )
    for place, match in attempts:
        placed = place(match)
        if placed is not None:
            return placed

    if sort == "ранг":
        pos = next((i for i, row in enumerate(rows_out) if row["rank"] > own["rank"]),
                   len(rows_out))
        return rows_out[:pos] + [own] + rows_out[pos:]
    return rows_out + [own]


def _with_note(text: str, note: str | None) -> str:
    return f"{text} — {note}" if note else text


def build(rows, defs):
    by_rank = {r["rank"]: r for r in rows}

    # Состав каждой группы — один раз на все слова.
    composition = {}
    for tag, spec in defs.items():
        # Пометка к отдельной строке таблицы. Нужна там, где в группе есть
        # строка иного рода, чем остальные: в таблицах приставок это слово,
        # которое значит то же самое, но пишется отдельно (מִן при приставке
        # מ). Без пометки его не отличить от приставочных форм, а смешивать в
        # одной таблице разное — ровно та ошибка, за которую группу приставок
        # уже переделывали.
        notes = {int(k): v for k, v in (spec.get("row_notes") or {}).items()}
        composition[tag] = [{
            "rank": rank,
            "ru": _with_note(primary(by_rank[rank].get("russian", "")), notes.get(rank)),
            "ipa": by_rank[rank].get("ipa", ""),
            "foreign": by_rank[rank].get("niqqud") or by_rank[rank].get("hebrew", ""),
        } for rank in spec.get("members", [])]

    built = 0
    for r in rows:
        r.pop("tag_groups", None)
        tags = r.get("tags") or []
        if not tags:
            continue
        groups = []
        for t in sorted(tags, key=lambda x: x["tag"]):
            rows_out = [dict(row, self=(row["rank"] == r["rank"]))
                        for row in composition[t["tag"]]]
            if not any(row["self"] for row in rows_out):
                rows_out = insert_own(rows_out, own_row(r), by_rank,
                                      r.get("lemma"), defs[t["tag"]].get("sort", "ручной"))
            groups.append({
                "tag": t["tag"],
                "label": defs[t["tag"]]["label"],
                "rows": rows_out,
            })
        if groups:
            r["tag_groups"] = groups
            built += 1
    return built, composition


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    with open(FULL, encoding="utf-8") as fh:
        rows = json.load(fh)
    defs = load_tags(TAGS)

    built, composition = build(rows, defs)

    for tag, comp in composition.items():
        print(f"  {defs[tag]['label']:<30} строк в группе: {len(comp)}")
    print(f"\nслов с собранными группами: {built}")

    example = next((r for r in rows if r["rank"] == 417), None)
    if example and example.get("tag_groups"):
        g = example["tag_groups"][0]
        print(f"\nпример — слово #417 {example['hebrew']} ({example['russian']}), группа «{g['tag']}»:")
        for row in g["rows"][:6]:
            mark = " ←" if row["self"] else ""
            print(f"    #{row['rank']:<5} {row['ru']:<14} [{row['ipa']}]  {row['foreign']}{mark}")
        print(f"    … всего строк: {len(g['rows'])}")

    if args.dry:
        print("\n[--dry] не записано")
        return 0
    tmp = FULL + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, FULL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
