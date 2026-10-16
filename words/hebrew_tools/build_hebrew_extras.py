#!/usr/bin/env python3
"""
Заполняет для иврита поля tones и references — по смыслу, а не по названию.

Почему эти поля подходят
------------------------
Оба поля заводились под китайский, но задачи, которые они решают, у иврита ровно
те же — меняется только чем именно письмо неоднозначно.

  tones       В китайском одна и та же транскрипция с разными тонами это разные
              слова: ma -> mā «мама», mǎ «лошадь». В иврите то же самое делает
              огласовка при одинаковых согласных: יצר -> יֵצֶר «инстинкт»,
              יָצַר «создал». В обоих случаях письмо не различает слова, а
              диакритика различает.

  references  В китайском это слова из тех же иероглифов. Организующий принцип
              иврита — трёхбуквенный корень, и слова одного корня связаны и по
              смыслу, и по written form. Берём их по общей лемме, которая уже
              посчитана отдельной стадией конвейера для всех слов.

Формат повторяет китайский, чтобы карточка и фильтрация [#N] работали как есть.
Разметка [#N] важна: card_builder прячет ссылки на слова, до которых учащийся
ещё не дошёл, — иначе подсказка забегала бы вперёд.

Использование
-------------
    python build_hebrew_extras.py            # показать, что получится
    python build_hebrew_extras.py --apply    # записать в словарь
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import shutil
import unicodedata

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hebrew_freq")
FULL = os.path.join(HERE, "hebrew_freq_10000_full.json")
HOMOGRAPHS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "homographs.json")

# Сколько однокоренных показывать максимум — длинный список на карточке бесполезен.
MAX_REFS = 12


def strip_niqqud(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text or "")
                   if unicodedata.category(c) != "Mn")


def build_tones(entry: dict) -> str:
    """Варианты огласовки одних и тех же согласных — аналог тонов."""
    readings = entry["readings"]
    lines = [f"<b>{entry['hebrew']}</b>: <i>вариантов огласовки: {len(readings)}</i>"]
    for r in readings:
        lines.append(f" - <b>{r['niqqud']}</b> [{r['ipa']}]: {r['sense']}")
    return "\n".join(lines)


_TONE_LINE = re.compile(r"^(\s*-\s*)(<i>\[#\d+\]</i>)?(<b>.+?</b>)\s*\[([^\]]*)\]\s*:\s*(.*)$")


def tone_resolver(rows: list[dict]):
    """Как найти номер слова по строке варианта огласовки.

    Три попытки, от точной к приблизительной: по самой огласовке, по
    согласным вместе с IPA (огласовка в источнике вариантов и в словаре
    иногда записана чуть иначе — дагеш, шва), и по одному лишь IPA, если
    такое звучание в словаре единственное.
    """
    by_niqqud: dict[str, int] = {}
    by_pair: dict[tuple[str, str], int] = {}
    by_ipa: dict[str, list[int]] = collections.defaultdict(list)
    for r in rows:
        by_niqqud.setdefault(r["niqqud"], r["rank"])
        by_pair.setdefault((strip_niqqud(r["niqqud"]), r["ipa"]), r["rank"])
        by_ipa[r["ipa"]].append(r["rank"])

    def resolve(niqqud: str, ipa: str):
        if niqqud in by_niqqud:
            return by_niqqud[niqqud]
        pair = by_pair.get((strip_niqqud(niqqud), ipa))
        if pair is not None:
            return pair
        same = by_ipa.get(ipa, [])
        return same[0] if len(same) == 1 else None

    return resolve


def number_tone_rows(text: str, resolve) -> str:
    """Проставить номера слов в строках вариантов огласовки.

    Просьба владельца: «таблица вариантов огласовки, первый столбец пустой —
    добавить номера слова». Номер есть не у каждого варианта: вторая огласовка
    тех же согласных часто сама в десятитысячник не входит (אַתְּ «ты (ж)» при
    אֵת), и тогда ставить нечего — ячейка остаётся пустой, как была.

    Повторный запуск ничего не портит: строка с номером пропускается.
    """
    out = []
    for line in (text or "").split("\n"):
        m = _TONE_LINE.match(line)
        if not m or m.group(2):
            out.append(line)
            continue
        dash, _, form, ipa, sense = m.groups()
        rank = resolve(re.sub(r"</?b>", "", form), ipa)
        marker = f"<i>[#{rank}]</i>" if rank else ""
        out.append(f"{dash}{marker}{form} [{ipa}]: {sense}")
    return "\n".join(out)


def build_references(row: dict, family: list[dict]) -> str:
    """Слова того же корня, кроме самого слова."""
    others = [w for w in family if w["rank"] != row["rank"]]
    if not others:
        return ""
    # Число берём ДО обрезки: считать после — значит утверждать «слов с этой
    # основой: 12» там, где их 49. У 70 основ семья больше лимита, и такие
    # заголовки стояли на 1433 карточках.
    total = len(others)
    others = others[:MAX_REFS]
    head = f"<b>{row['lemma']}</b>: <i>слов с этой основой: {total}</i>"
    if total > MAX_REFS:
        head += f" <i>(показаны первые {MAX_REFS})</i>"
    lines = [head]
    for w in others:
        form = (w.get("niqqud") or "").strip() or w["hebrew"]
        sense = (w.get("russian") or "").split("\n")[0]
        lines.append(f"<i>[#{w['rank']}]</i>{form} [{w.get('ipa','')}] {sense}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="записать в словарь")
    args = ap.parse_args()

    rows = json.load(open(FULL, encoding="utf-8"))
    by_rank = {r["rank"]: r for r in rows}
    homographs = json.load(open(HOMOGRAPHS, encoding="utf-8"))

    # ── tones: варианты огласовки ────────────────────────────────────────────
    tones_set = 0
    for entry in homographs:
        row = by_rank.get(entry["rank"])
        if row is None or row["hebrew"] != entry["hebrew"]:
            continue
        row["_tones"] = build_tones(entry)
        tones_set += 1

    # ── references: однокоренные по лемме ────────────────────────────────────
    families: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        lemma = (r.get("lemma") or "").strip()
        if lemma:
            families[lemma].append(r)

    refs_set = 0
    for r in rows:
        lemma = (r.get("lemma") or "").strip()
        fam = families.get(lemma, [])
        if len(fam) < 2:
            continue
        text = build_references(r, sorted(fam, key=lambda w: w["rank"]))
        if text:
            r["_references"] = text
            refs_set += 1

    sizes = collections.Counter(len(v) for v in families.values() if len(v) > 1)
    print(f"слов в словаре: {len(rows)}")
    print(f"  варианты огласовки (tones):      {tones_set}")
    print(f"  однокоренные (references):       {refs_set}")
    print(f"  семей с общей основой:           {sum(1 for v in families.values() if len(v) > 1)}")
    print(f"  крупнейшие семьи: {sorted(sizes.items(), reverse=True)[:5]}")

    example = next((r for r in rows if r.get("_references")), None)
    if example:
        print(f"\nпример однокоренных для {example['hebrew']} (основа {example['lemma']}):")
        for line in example["_references"].split("\n")[:5]:
            print("   ", line)
    example_t = next((r for r in rows if r.get("_tones")), None)
    if example_t:
        print(f"\nпример вариантов огласовки для {example_t['hebrew']}:")
        for line in example_t["_tones"].split("\n"):
            print("   ", line)

    if not args.apply:
        print("\nпробный прогон. Чтобы записать — запустите с --apply")
        return 0

    # Затирать tones огулом нельзя: этот скрипт строит их только для записей из
    # homographs.json, а поле пополняется и разбором по внешним источникам.
    # Проход «r["tones"] = r.pop("_tones", "")» стёр бы все чужие блоки — на
    # момент обнаружения таких было 36 из 54.
    doomed = [r for r in rows if (r.get("tones") or "").strip() and not r.get("_tones")]
    if doomed:
        print(f"\nостановлено: {len(doomed)} записей имеют tones, построенные не этим "
              f"скриптом — он их не тронет, но и не подтвердит:")
        for r in doomed[:8]:
            print(f"  №{r['rank']:5} {r['hebrew']}")
        print("  (они сохраняются как есть)")

    shutil.copy2(FULL, FULL + ".bak")
    resolve = tone_resolver(rows)
    for r in rows:
        built = r.pop("_tones", "")
        if built:
            r["tones"] = built
        # Номера проставляем и в блоках, построенных не здесь: таблица на
        # карточке одна, и колонка номеров в ней должна вести себя одинаково.
        if (r.get("tones") or "").strip():
            r["tones"] = number_tone_rows(r["tones"], resolve)
        r["references"] = r.pop("_references", "")
    with open(FULL, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2)
    print(f"\nзаписано в {os.path.basename(FULL)} (бэкап: .bak)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
