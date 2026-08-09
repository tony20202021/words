#!/usr/bin/env python3
"""
Разбор собранного викитекста в сопоставимые поля и поиск расхождений.

Что делает
----------
fetch_sources.py приносит сырые статьи. Здесь они превращаются в то же, что
хранится у нас — огласовка, IPA, транслитерация, часть речи, значение, — и
сравниваются со словарём. На выходе список расхождений, разложенный по полю и
по причине.

Почему сравнение отдельно от решения
------------------------------------
Расхождение само по себе не ошибка. Викисловарь даёт словарную форму, а у нас
может стоять словоформа; IPA бывает библейский, а не израильский; часть речи
у приставочной формы законно отличается от части речи леммы. Поэтому скрипт
только показывает, ЧТО разошлось и с чем, а решает человек или агент, глядя на
все варианты сразу. Ровно так же был устроен triage_niqqud_review.py, и это
единственное, что сделало прошлые 646 расхождений обозримыми.

Использование
-------------
    python parse_sources.py --max-rank 1000
    python parse_sources.py --max-rank 1000 --show 20
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hebrew_freq")
FULL = os.path.join(HERE, "hebrew_freq_10000_full.json")

# Части речи: наши сокращения <- как их называют источники.
POS_FROM_EN = {
    "Noun": "сущ", "Proper noun": "имя", "Verb": "глаг", "Adjective": "прил",
    "Adverb": "нареч", "Pronoun": "мест", "Preposition": "предл",
    "Conjunction": "союз", "Interjection": "межд", "Particle": "част",
    "Numeral": "числ", "Determiner": "мест",
}
POS_FROM_RU = {
    "существительное": "сущ", "глагол": "глаг", "прилагательное": "прил",
    "наречие": "нареч", "местоимение": "мест", "предлог": "предл",
    "союз": "союз", "частица": "част", "междометие": "межд",
    "числительное": "числ", "имя собственное": "имя",
}


def strip_niqqud(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text or "")
                   if unicodedata.category(c) != "Mn")


HEBREW_LETTERS = re.compile(r"[\u05d0-\u05ea]")


def has_niqqud(text: str) -> bool:
    """
    Огласованный ли ивритский текст.

    Проверять одну лишь категорию Mn нельзя: NFD раскладывает русское «й» на
    «и» + бреве, а бреве — тоже Mn, и слово «свойства» из библиографии
    ru.wiktionary проходило как огласовка. Поэтому сначала — есть ли вообще
    ивритские буквы.
    """
    if not text or not HEBREW_LETTERS.search(text):
        return False
    return any(unicodedata.category(c) == "Mn"
               for c in unicodedata.normalize("NFD", text))


FORM_OF = re.compile(r"\{\{he-(\w+) form of\|([^|}]+)\|?([^}]*)\}\}")


def clean(s: str) -> str:
    """Викиразметку — в читаемый текст. Достаточно для сравнения и для глаз."""
    # «Форма слова X» — это и есть толкование словоформы, а не служебная разметка.
    # Без этого у причастий и приставочных форм значение выходило пустым.
    s = FORM_OF.sub(lambda m: f"форма слова {m.group(2)} ("
                              + ", ".join(p for p in m.group(3).split("|")
                                          if p and "=" not in p and p != "nocap") + ")", s)
    s = re.sub(r"\{\{(?:inflection of|infl of)\|he\|([^|}]+)\|?([^}]*)\}\}",
               lambda m: f"форма слова {m.group(1)}", s)
    s = re.sub(r"\{\{(?:lb|label)\|[^|}]*\|([^}]*)\}\}",
               lambda m: "(" + m.group(1).replace("|", ", ") + ")", s)
    s = re.sub(r"\{\{(?:tcl|l|m|w)\|[^|}]*\|([^|}]*)(?:\|[^}]*)?\}\}", r"\1", s)
    s = re.sub(r"\{\{(?:gl|gloss|q|qualifier)\|([^}]*)\}\}", r"(\1)", s)
    s = re.sub(r"\{\{[^}]*\}\}", " ", s)
    s = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[\[([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"'{2,}", "", s)
    return re.sub(r"\s+", " ", s).strip(" ,;")


def hebrew_section(wt: str | None) -> str:
    if not wt or "==Hebrew==" not in wt:
        return ""
    s = wt[wt.index("==Hebrew=="):]
    nxt = re.search(r"\n==[^=]", s)
    return s[:nxt.start()] if nxt else s


def parse_en(wt: str | None, via: str) -> list[dict]:
    """Разделы частей речи английского Викисловаря — по одному на чтение."""
    heb = hebrew_section(wt)
    if not heb:
        return []
    root_m = re.search(r"\{\{he-rootbox\|([^}|]*)", heb)
    root = root_m.group(1).strip() if root_m else ""

    out = []
    headers = list(re.finditer(
        r"\n=+(" + "|".join(map(re.escape, POS_FROM_EN)) + r")=+\n", heb))
    for i, m in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(heb)
        block = heb[m.end():end]
        entry = {"via": via, "pos_src": m.group(1), "pos": POS_FROM_EN[m.group(1)], "root": root}

        # Заголовочный шаблон раздела. Словарные статьи используют
        # {{he-noun|…}}, а СЛОВОФОРМЫ — общий {{head|he|verb form|head=רוֹצֶה}}:
        # без второго терялись огласовка и транслитерация ровно у тех слов,
        # которых в частотном списке больше всего — причастий, форм лица,
        # приставочных форм.
        # Шаблоны «* of» (he-verb form of, he-defective spelling of) стоят в
        # ТОЛКОВАНИИ, а не в заголовке, и несут транслитерацию исходного слова.
        # Приняв их за заголовок, мы приписывали форме произношение леммы:
        # רוֹצֶה получало ratsá вместо rotsé.
        params = ""
        for hm in re.finditer(r"\{\{(he-[a-z ]+|head\|he)\|([^}]*)\}\}", block):
            if hm.group(1).endswith(" of"):
                continue
            params = hm.group(2)
            break
        wv = re.search(r"\bwv=([^|}]+)", params)
        tr = re.search(r"\btr=([^|}]+)", params)
        entry["translit"] = (tr.group(1).strip() if tr else "")

        # Огласовка стоит в wv=, но у предлогов и частиц — в head=, и там
        # перечислено несколько форм через запятую (אֵת, אֶת־).
        cands: list[str] = []
        if wv:
            cands.append(wv.group(1))
        head = re.search(r"\bhead=([^|}]+)", params)
        if head:
            cands.extend(head.group(1).split(","))
        cands.extend(p for p in params.split("|") if "=" not in p)
        entry["niqqud"] = ""
        for c in cands:
            c = c.strip().strip("־").strip()
            if c and has_niqqud(c):
                entry["niqqud"] = c
                break

        # Произношение объявляется выше разделов и относится ко всей статье.
        entry["ipa"] = ipa_modern(heb)
        entry["glosses"] = [clean(g) for g in re.findall(r"\n# ([^\n]+)", block)]
        entry["glosses"] = [g for g in entry["glosses"] if g]
        out.append(entry)
    return out


def ipa_modern(heb: str) -> list[str]:
    """Из всех вариантов — израильский. Библейский и ашкеназский нам не про то."""
    modern, plain = [], []
    for m in re.finditer(r"\{\{IPA\|he\|([^}]*)\}\}", heb):
        body = m.group(1)
        vals = [p.strip() for p in body.split("|")
                if p.strip().startswith(("/", "[")) and "=" not in p]
        if "a=Modern Hebrew" in body:
            modern.extend(vals)
        elif "a=" not in body:
            plain.extend(vals)
    return modern or plain


def ru_hebrew_section(wt: str | None) -> str:
    """
    Ивритский раздел русского Викисловаря.

    Страница там устроена как «= {{-he-}} = … = {{-yi-}} = … = {{-kdr-}} = …»:
    одно написание может описываться и как иврит, и как идиш, и как крымчакский.
    Разбирая страницу целиком, мы подмешивали чужие языки в свидетельства об
    иврите — у יש в значения попадали крымчакские «возраст» и «зелёный», а у בין
    идишское произношение bin. Проверяющий видел это как русские словарные
    значения ивритского слова.
    """
    if not wt or "{{-he-}}" not in wt:
        return ""
    s = wt[wt.index("{{-he-}}"):]
    nxt = re.search(r"\{\{-(?!he-)[a-z]+-\}\}", s)
    return s[:nxt.start()] if nxt else s


def parse_ru(wt: str | None, via: str) -> list[dict]:
    wt = ru_hebrew_section(wt)
    if not wt:
        return []
    out = []
    blocks = re.split(r"\n== \{\{з\|\(([^)]*)\)", "\n" + wt)
    # split даёт [до первого; заголовок1; тело1; заголовок2; тело2; ...]
    pairs = list(zip(blocks[1::2], blocks[2::2])) or [("", wt)]
    for title, body in pairs:
        pos_word = re.sub(r"\s+[IVX]+$", "", title.strip()).strip()
        entry = {"via": via, "pos_src": title.strip(),
                 "pos": POS_FROM_RU.get(pos_word, "")}
        entry["niqqud"] = [p.strip() for p in re.findall(r"[^\s|{}=]+", body)
                           if has_niqqud(p)][:4]
        # {{transcription|IPA|аудиофайл}} — второй параметр это запись голоса,
        # а не транскрипция; {{transcriptions|ед|мн}} — обе формы наши.
        entry["ipa"] = []
        for m in re.finditer(r"\{\{transcription(s?)\|([^}]*)\}\}", body):
            parts = [x.strip() for x in m.group(2).split("|") if x.strip()]
            keep = parts[:2] if m.group(1) else parts[:1]
            entry["ipa"].extend(k for k in keep if not is_audio(k))
        sense = re.search(r"==== Значени[ея] ====(.*?)(?:\n====|\n===|\Z)", body, re.S)
        entry["senses"] = [clean(s) for s in re.findall(r"\n# ([^\n]+)", sense.group(1))] if sense else []
        entry["senses"] = [s for s in entry["senses"] if s]
        out.append(entry)
    return [e for e in out if e["niqqud"] or e["senses"] or e["ipa"]]


# ── сравнение ────────────────────────────────────────────────────────────────

def is_audio(s: str) -> bool:
    """Викисловарь кладёт рядом с транскрипцией имя звукового файла."""
    return bool(re.search(r"\.(wav|ogg|mp3|flac)$", s or "", re.I)) or "LL-Q" in (s or "")


def ipa_variants(s: str) -> set[str]:
    """
    Нормализованные варианты записи одного произношения.

    Расходятся не звуки, а соглашения записи. Гортанная смычка алефа и айина в
    израильском иврите почти не произносится, и источники пишут её то как ʔ, то
    как (ʔ), то опускают вовсе: наше ʔaˈni, их (ʔ)aˈni, ещё где-то ani — одно и
    то же слово. Ударение и долготу тоже ставят не все. Поэтому сравниваем не
    строки, а множество допустимых прочтений.
    """
    if not s or is_audio(s):
        return set()
    core = re.sub(r"\(([^)]*)\)", r"\1", s)          # (ʔ) — необязательный звук
    # Ударение пишут и как ˈ, и обычным апострофом; слоговые точки, долгота и
    # дефисы к звукам отношения не имеют.
    core = re.sub(r"[/\[\]ˈˌ'\u02bc\u2019.ːˑ\s\-]", "", core)
    out = {core}
    out.add(re.sub(r"^[ʔʕ]", "", core))              # без начальной смычки
    out.add(re.sub(r"[ʔʕ]", "", core))               # без смычек вовсе
    return {v for v in out if v}


def compare(row: dict, ev: dict) -> list[dict]:
    """Расхождения по одному слову. Пусто — все источники согласны с нами."""
    issues = []
    en = parse_en(ev.get("en_form"), "форма") + parse_en(ev.get("en_lemma"), "лемма")
    ru = parse_ru(ev.get("ru_form"), "форма") + parse_ru(ev.get("ru_lemma"), "лемма")

    # Чтения ЭТОГО написания: у одних согласных бывает несколько огласовок, и
    # статья описывает их все. Записи про другое слово (את как дефектное
    # написание אוֹת) отсекаем по составу согласных — иначе каждый омограф
    # тянул бы за собой чужие части речи и чужое произношение.
    ours_skel = strip_niqqud(row["hebrew"])
    readings = [e for e in en
                if e["via"] == "форма" and e.get("niqqud")
                and strip_niqqud(e["niqqud"]) == ours_skel]
    ru_readings = [e for e in ru if e["via"] == "форма"]

    # ── огласовка ───────────────────────────────────────────────────────────
    ours_niq = (row.get("niqqud") or "").strip()
    cand = [e["niqqud"] for e in readings]
    for e in ru_readings:
        cand += [n for n in e["niqqud"] if strip_niqqud(n) == ours_skel]
    if cand and ours_niq and ours_niq not in cand:
        issues.append({"field": "niqqud", "ours": ours_niq, "theirs": sorted(set(cand))})

    # Наше чтение среди описанных — по нему и сверяем остальные поля.
    mine = next((e for e in readings if e["niqqud"] == ours_niq), None)

    # ── IPA ─────────────────────────────────────────────────────────────────
    ours_ipa = (row.get("ipa") or "").strip()
    ipa_cand = list((mine or {}).get("ipa") or [])
    if not ipa_cand:
        ipa_cand = [i for e in readings for i in e.get("ipa", [])]
    ipa_cand += [i for e in ru_readings for i in e.get("ipa", [])]
    ipa_cand = [i for i in ipa_cand if not is_audio(i)]
    ours_v = ipa_variants(ours_ipa)
    if ipa_cand and ours_v and not any(ipa_variants(i) & ours_v for i in ipa_cand):
        issues.append({"field": "ipa", "ours": ours_ipa, "theirs": sorted(set(ipa_cand))})

    # ── часть речи ──────────────────────────────────────────────────────────
    # Сверяем с ЧАСТЬЮ РЕЧИ НАШЕГО ЧТЕНИЯ. У омографа они разные по определению
    # (עם — «с» предлог и «народ» существительное), и объединять их значило бы
    # объявлять расхождением сам факт омонимии.
    ours_pos = (row.get("pos") or "").strip()
    if mine is not None:
        pos_cand = {mine["pos"]} if mine["pos"] else set()
    else:
        pos_cand = {e["pos"] for e in readings if e["pos"]}
        pos_cand |= {e["pos"] for e in ru_readings if e["pos"]}
    if pos_cand and ours_pos and ours_pos not in pos_cand:
        issues.append({"field": "pos", "ours": ours_pos, "theirs": sorted(pos_cand),
                       "по_нашему_чтению": mine is not None})

    # ── значение: машинный перевод расходится с нашим ───────────────────────
    ours_ru = (row.get("russian") or "").split("\n")[0].strip()
    gtx = (ev.get("gtx_form") or "").strip()
    if gtx and ours_ru and not overlap(ours_ru, gtx):
        issues.append({"field": "russian", "ours": ours_ru, "theirs": [gtx],
                       "senses_ru": [s for e in ru for s in e.get("senses", [])][:6],
                       "glosses_en": [g for e in en for g in e.get("glosses", [])][:6]})

    # ── несколько чтений: письмо неоднозначно, а у нас одна запись ──────────
    # Разная огласовка ещё не омография. רוצה это rotsé и rotsá — мужская и
    # женская формы ОДНОГО глагола רצה, и учащемуся они нужны вместе, а не как
    # два слова. Настоящий омограф — когда за одним написанием стоят разные
    # слова: עם это «с» и «народ». Различаем по источнику: если Викисловарь
    # говорит «форма слова X», сводим чтение к X и считаем базы.
    def base_of(e: dict) -> str:
        for g in e.get("glosses", []):
            m = re.match(r"форма слова (\S+)", g)
            if m:
                return m.group(1)
        return e["niqqud"]

    distinct = {e["niqqud"] for e in readings}
    if len({base_of(e) for e in readings}) > 1 and len(distinct) > 1:
        issues.append({"field": "homograph", "ours": ours_niq, "theirs": sorted(distinct),
                       "glosses_en": [f"{e['niqqud']}: {'; '.join(e['glosses'][:2])}"
                                      for e in readings]})
    return issues


def norm_words(s: str) -> set[str]:
    return {w for w in re.findall(r"[а-яёa-z]+", (s or "").lower()) if len(w) > 2}


def overlap(a: str, b: str) -> bool:
    """
    Переводы «считаются согласными», если делят хоть одно значимое слово.

    Фильтр «слова длиннее двух букв» отсекает предлоги и частицы, но у самых
    частотных слов ВЕСЬ перевод такой: «я», «он», «но», «да». Возврат True при
    пустом множестве означал, что перевод 52 самых частотных слов не сверялся
    никогда — то есть ровно того, что учащийся видит первым. Если сторона
    осталась пустой, сравниваем нормализованные строки целиком.
    """
    wa, wb = norm_words(a), norm_words(b)
    if wa and wb:
        return bool(wa & wb)
    na = set(re.findall(r"[а-яёa-z]+", (a or "").lower()))
    nb = set(re.findall(r"[а-яёa-z]+", (b or "").lower()))
    if not na or not nb:
        return True          # сравнивать нечего
    return bool(na & nb)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-rank", type=int, default=1000)
    ap.add_argument("--show", type=int, default=8, help="сколько примеров печатать")
    args = ap.parse_args()

    src = os.path.join(HERE, f"sources_{args.max_rank}.json")
    if not os.path.exists(src):
        print(f"нет {os.path.basename(src)} — сначала выполните fetch_sources.py")
        return 1

    rows = {r["rank"]: r for r in json.load(open(FULL, encoding="utf-8"))}
    evidence = json.load(open(src, encoding="utf-8"))

    by_field: Counter = Counter()
    per_word: dict[int, list] = {}
    no_source = 0
    for ev in evidence:
        row = rows.get(ev["rank"])
        if row is None:
            continue
        if not (hebrew_section(ev.get("en_form")) or hebrew_section(ev.get("en_lemma"))
                or ev.get("ru_form") or ev.get("ru_lemma")):
            no_source += 1
        issues = compare(row, ev)
        if issues:
            per_word[ev["rank"]] = issues
            by_field.update(i["field"] for i in issues)

    print(f"проверено слов: {len(evidence)}")
    print(f"без единой словарной статьи: {no_source}")
    print(f"слов с расхождениями: {len(per_word)}\n")
    print("расхождений по полю:")
    for f, n in by_field.most_common():
        print(f"  {f:12} {n}")

    for field in by_field:
        picked = [(r, i) for r, iss in sorted(per_word.items()) for i in iss if i["field"] == field]
        print(f"\n── {field} ── примеры ({min(args.show, len(picked))} из {len(picked)}):")
        for rank, issue in picked[:args.show]:
            row = rows[rank]
            print(f"  №{rank:4} {row['hebrew']:10} наше {issue['ours']!r:28} "
                  f"источники {issue['theirs']}")

    out = os.path.join(HERE, f"disagreements_{args.max_rank}.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({str(k): v for k, v in sorted(per_word.items())}, fh, ensure_ascii=False, indent=1)
    print(f"\nзаписано: {os.path.basename(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
