"""Отбор слов для учебного частотного списка английского.

Частотный список из интернет-корпуса даёт правильный охват, но грязный состав:
wordfreq собран в том числе из твиттера и реддита, и рядом с нужными словами там
лежат мат, имена, бренды, названия клубов и опечатки без апострофа. Для словаря,
по которому люди учат язык, это не слова.

Отсев здесь делится на две части по степени уверенности:

  — то, что выбрасывается сразу: мат, инициализмы, бренды и названия. Ошибиться
    тут почти невозможно: «nfl» и «lmao» не слова ни в каком смысле;
  — то, что только помечается: имена. Половина английских имён это заодно
    обычные слова — «grace», «rose», «mark», «will», «faith», «earl», «pearl»,
    — и выбрасывать их по списку имён нельзя. Помеченные слова смотрит человек.

Списки ведутся вручную и будут расти: это нормально, другого способа отличить
«chelsea» от «cherry» у программы нет.
"""
import csv
import re
from pathlib import Path

ДАННЫЕ = Path(__file__).resolve().parents[1] / "data" / "eng_freq"

# Обычное английское слово. Апостроф оставлен: «don't» и «it'll» живые слова.
СЛОВО = re.compile(r"^[a-z]+(?:'[a-z]+)?$")

# Одиночная буква словом бывает только в двух случаях. Остальные приходят из
# токенизации сокращений («don't» → «t») и словами не являются.
ОДИНОЧНЫЕ_СЛОВА = {"a", "i"}

ГЛАСНЫЕ = set("aeiouy")

# Настоящие короткие слова. Без этого списка правило «короче трёх букв —
# сокращение» срезает пол-начала языка: «to», «in», «is», «it», «of», «be».
# В остатке на перевод их не видно — они все есть в прежнем словаре, — поэтому
# ошибка всплыла только на полном списке.
КОРОТКИЕ_СЛОВА = set("""a i am an as at ax be by do go he hi id if in is it me my no
of oh ok on or ox so to up us we ad""".split())

МАТ = set("""shit fuck fucking fucked fuckin fucks ass asshole asses bitch bitches
bullshit cock pussy cunt tits boobs whore anal penis vagina sperm piss pissed cum
damn goddamn damned bastard crap horny nude naked porn dick slut shitty""".split())

# Инициализмы, сетевые сокращения, опечатки без апострофа и осколки токенизации.
СОКРАЩЕНИЯ = set("""lol omg lmao wtf btw tbh idk imo rofl pp bc tho nah yep yup ya yea
ye em ve ll re th da na op fi hd dvd cnn mp km il mi di sc fa hr aka cuz isnt hes
youre thats dont doesnt didnt cant wont im alot goin outta ugh huh eh ah aw oz ta tl
sh sp si su ka ki ji ni es und der von le les para que ba bb ce cf cl cr cs db def
dem dm ea ep ff fl fm fu gb gf gif gp gps ing int ive jo lb lbs lp ml mls mon mt
mvp ng nj nm nsa nsw ot pac pdf pg pi pl po pr prof pt qb ra rd ref res rt sd seo sf
sim sq ss td te tee tx ufc ur url usb usd vi vii vol vr wa wi wu xd xi yr aa aaa ab
abs af alt amp apr br bs ch chan chi comp cp dee dj hm ho ie lin ol
pic pics se cal nc ne nyc fc afl nhl nba nfl fifa espn mlb wwe ncaa http https
www sep jun ap pm dr mr mrs st jr sr vs etc""".split())

# Бренды, компании, продукты, города, страны, клубы, известные люди.
НАЗВАНИЯ = set("""facebook google twitter youtube amazon instagram netflix samsung ebay
walmart itunes yahoo wikipedia linux bitcoin covid brexit obamacare iphone ipad android
ios xbox playstation pokemon batman superman marvel avengers lego bmw mercedes ferrari
chrome kindle photoshop uber whatsapp tesla obama biden putin hitler barack hillary
shakespeare chelsea arsenal liverpool lakers yankees dodgers cubs broncos panthers
vikings titans spurs celtic leeds sheffield southampton newcastle queensland melbourne
delhi edinburgh barcelona glasgow dubai dublin bristol brighton nigeria kenya ghana
sudan qatar yemen mumbai bangkok adelaide calgary durham essex cornwall somerset
yorkshire westminster norfolk louisville myanmar bangladesh indonesian nigerian
ukrainian welsh portuguese czech bulgarian jamaica morocco iceland athens venice
munich florence perth brisbane wellington springfield lancaster chester albany
alexandria cardiff aberdeen belfast newman nepal uganda qatar bahrain""".split())


def годится_как_слово(w: str) -> bool:
    """Похоже ли вообще на английское слово: буквы, не цифры, не одна буква."""
    if not СЛОВО.match(w):
        return False
    if len(w) == 1 and w not in ОДИНОЧНЫЕ_СЛОВА:
        return False
    return True


def загрузить_имена() -> set:
    """Список имён-подсказок. Пустое множество, если файла нет."""
    путь = ДАННЫЕ / "names.txt"
    if not путь.exists():
        return set()
    return {l.strip().lower() for l in путь.read_text(encoding="utf-8").splitlines()
            if l.strip()}


СЛОВО_ЖЕ_И_ИМЯ = set("""grace rose mark will faith hope earl pearl angel destiny
amber berry carol dawn joy may june july august art bill jack frank max rich
sunny summer autumn crystal daisy ruby violet olive sage ginger hazel iris jade
lily jasmine melody harmony justice chance drew curry marina bailey blake
hunter parker tanner taylor tyler carter cooper mason wade reed""".split())


def разметить(w: str, имена: set) -> str:
    """Один из видов: слово / возможно имя / мат / сокращение / название."""
    if w in МАТ:
        return "мат"
    if w in СОКРАЩЕНИЯ:
        return "сокращение"
    if w in НАЗВАНИЯ:
        return "название"
    if not (set(w) & ГЛАСНЫЕ):
        return "сокращение"
    if len(w) <= 2 and w not in КОРОТКИЕ_СЛОВА:
        return "сокращение"
    if w in имена and w not in СЛОВО_ЖЕ_И_ИМЯ:
        return "возможно имя"
    return "слово"


ВИДЫ_НА_ПЕРЕВОД = ("слово", "возможно имя")
ВИДЫ_ОТСЕВА = ("мат", "сокращение", "название")


def собрать_имена_из_источников(первые: Path, детские: Path, порог=0.002) -> set:
    """Готовит компактный список имён из двух открытых источников.

    Полные источники в репозиторий не кладутся: детские имена это семь мегабайт
    за сто лет. Берём популярные (порог по доле) плюс весь короткий список имён.
    """
    out = set()
    if первые.exists():
        out |= {l.strip().lower() for l in
                первые.read_text(encoding="utf-8", errors="replace").splitlines()
                if l.strip()}
    if детские.exists():
        with детские.open(encoding="utf-8", errors="replace") as f:
            for r in csv.DictReader(f):
                try:
                    if float(r["percent"]) >= порог:
                        out.add(r["name"].strip().lower())
                except (ValueError, KeyError):
                    pass
    return out
