#!/usr/bin/env python
"""
Ходит ли на старые TLS-порты КТО-НИБУДЬ ЖИВОЙ.

Зачем
-----
31.10.2026 порты сведены к виду 85**: 8443 → 8543 (BLS), 8444 → 8544 (веб).
Старые оставлены слушать на время перехода, и закрыть их надо не наугад: адрес
сервера хранится в настройках установленного приложения, обновление APK его не
меняет — перенос делает само приложение при первом запуске. Пока хоть один
человек приходит на 8443, закрытие оборвёт ему связь молча: с виду «нет сети».

Две ошибки первой версии, обе показали себя на живых журналах
-------------------------------------------------------------
Первая: она считала ЗАПРОСЫ. За сутки на 8443 пришло девять штук — и все до
единого от сканеров: GET /, /webui/, /favicon.ico, сплошь 404, один прямо
представился zgrab/0.x. Скрипт честно сказал «закрывать рано». Сказал бы он
это и через год: сканеры не кончатся никогда, и порт остался бы открытым
навсегда.

Вторая, обратная и опаснее: тишину на старом порту она приняла бы за «все
перешли». Но отсутствие следов и отсутствие пользователя в журнале выглядят
одинаково. Человек мог просто не открывать приложение — а его настройки
никуда не делись и ждут первого запуска.

Поэтому здесь два правила. Считаются только КЛИЕНТЫ, а не обращения. И тишина
сама по себе разрешением не считается: нужно положительное доказательство —
тех же людей видели на НОВЫХ портах.

Как отличается клиент от сканера
--------------------------------
    клиент      опознан: либо User-Agent приложения (okhttp, stagefright),
                либо user_id прямо в пути. Это человек, которого оборвём
    шум         сканер назвал себя сам (их много, и они не прячутся), либо
                путь не наш и сервер ответил отказом — терять было некому
    безличное   путь наш, ответ есть, а кто пришёл — не видно. Закрывать
                запрещает, но показывается коротко: судить должен человек
    непонятное  всё остальное. Печатается целиком и закрывать запрещает:
                неизвестное — не то же самое, что безвредное

Про «безличное» стоит сказать отдельно, потому что на нём я уже ошибся.
Сначала клиентом считалось всё, что пришло к нашему маршруту. На живом
журнале таким «клиентом» оказался CensysInspect, запросивший /version: путь
наш, ответ 200. Сканер, попавший в настоящий маршрут, выглядит как человек —
и правило «похоже на наше, значит свой» вернуло бы ту же вечную блокировку,
только в новом костюме. Поэтому клиент теперь не «похож», а опознан.

Кто именно приходил, видно из самих путей: /session/<user_id>/<language_id>.
Сопоставить id с человеком — в Mongo, коллекция users.

Читает журналы nginx, поэтому запускать под sudo:

    sudo python3 deploy/old_ports_usage.sh
    sudo python3 deploy/old_ports_usage.sh --days 3

Именно python3, а не python: sudo сбрасывает PATH, и conda-питон пользователя
root не виден — выходит «sudo: python: command not found». Скрипту conda и не
нужна, он обходится стандартной библиотекой.
"""

import argparse
import collections
import glob
import gzip
import os
import re
import sys
from datetime import datetime, timedelta

# Журналы вместе с ротацией. logrotate режет их раз в сутки, и читать только
# текущий значило бы, что --days врёт: сколько ни проси, дальше сегодняшнего
# дня не заглянешь. Поймано 07.11.2026 на вопросе «ходит ли кто-то ещё на
# старые порты»: в каталоге лежало четырнадцать дней, скрипт смотрел один.
LOGS = {
    "/var/log/nginx/langbot-bls.access.log": "bls",
    "/var/log/nginx/langbot-web.access.log": "web",
}
OLD, NEW = {8443, 8444}, {8543, 8544}

# Первые сегменты путей, которые службы действительно обслуживают. Собраны из
# роутеров: business_logic_service/app и web_frontend/app. Список нужен, чтобы
# отличить «наш клиент получил законный 404» от «сканер щупал чужую админку».
ROUTES = {
    # «admin» в списке НЕТ намеренно: наружу nginx отдаёт по нему 404 сам
    # (location ^~ /admin { return 404; }), а приложение туда не ходит. Любой
    # запрос к /admin снаружи — чужой, и держать из-за него порт открытым
    # незачем. Поймано 07.11.2026: такие пробы висели в «безличных».
    "bls": {
        "auth", "batch", "confirm", "create", "deny", "get_or_create",
        "health", "help", "hints", "languages", "lookup", "mobile", "qr",
        "results", "session", "settings", "sounds", "statistics", "stats",
        "status", "timezones", "user", "users", "version", "words",
    },
    "web": {
        "", "auth", "autologin", "broadcast", "connect", "diagnostics",
        "download", "health", "help", "languages", "login", "logout", "qr",
        "settings", "sound", "static", "stats", "study", "users", "words",
    },
}

# Приложение: okhttp — его сетевой слой, stagefright — проигрыватель звука
# самого Android, он ходит за mp3 напрямую.
APP_UA = re.compile(r"okhttp|stagefright|dalvik|langbot", re.I)

# Сканеры, которые представляются честно. Список не про безопасность — он про
# то, чтобы их обращения не выдавались за людей. Подделать User-Agent можно,
# но подделывают его чтобы прикинуться браузером, а не чтобы прикинуться
# Censys, так что ложных срабатываний тут не бывает — бывают пропуски, и они
# уходят в «безличное», где их видит человек.
SCANNER_UA = re.compile(
    r"zgrab|censys|shodan|masscan|nmap|paloaltonetworks|expanse|internet-measurement"
    r"|netsystemsresearch|leakix|binaryedge|odin\.io|projectdiscovery|scanworld"
    r"|securityscanner|stretchoid|CriminalIP|infrawatch|infrawat\.ch", re.I)

# Ответы, которыми сервер говорит «я этого не обслуживаю». Если путь при этом
# не наш — терять было нечего.
REFUSALS = {400, 404, 405, 414, 421, 501}

RE_PORT = re.compile(r"port=(\d+)")
RE_TIME = re.compile(r"\[([^\]]+)\]")
RE_ADDR = re.compile(r"^(\S+)")
RE_QUOTED = re.compile(r'"([^"]*)"')
RE_STATUS = re.compile(r'"[^"]*"\s+(\d{3})\b')
RE_USER = re.compile(r"/(?:session|settings|statistics|results|user)/([0-9a-f]{24})\b")


def parse_line(line: str):
    """Строка журнала -> разобранная запись, или None если формат не тот."""
    m = RE_PORT.search(line)
    if not m:
        return None
    quoted = RE_QUOTED.findall(line)
    if not quoted:
        return None
    request = quoted[0]
    # Пробел между полями иногда теряется при переносе — User-Agent берём
    # последним закавыченным, а не по счёту.
    ua = quoted[-1] if len(quoted) > 1 else ""
    parts = request.split()
    path = parts[1] if len(parts) > 1 else ""
    status = RE_STATUS.search(line)
    when = RE_TIME.search(line)
    try:
        moment = datetime.strptime(when.group(1).split()[0], "%d/%b/%Y:%H:%M:%S") if when else None
    except ValueError:
        moment = None
    addr = RE_ADDR.match(line)
    return {
        "port": int(m.group(1)),
        "addr": addr.group(1) if addr else "?",
        "when": moment,
        "path": path.split("?")[0],
        "status": int(status.group(1)) if status else 0,
        "ua": ua,
        "line": line.rstrip("\n"),
    }


def first_segment(path: str) -> str:
    return path.lstrip("/").split("/")[0]


def classify(rec: dict, service: str) -> str:
    """клиент / шум / безличное / непонятное — см. заголовок модуля."""
    ua = rec["ua"] or ""
    if APP_UA.search(ua):
        return "клиент"
    if user_of(rec["path"]):
        return "клиент"
    if SCANNER_UA.search(ua):
        return "шум"
    # Пустой User-Agent — это не человек. Браузеры его шлют всегда, наше
    # приложение тоже; пустым приходит голый сокет. Без этого правила
    # «GET / HTTP/1.1» с «-» вместо агента попадал в безличные и держал
    # 8444 открытым: строка из живого журнала 01.11, адрес из сети Censys.
    if ua in ("", "-"):
        return "шум"
    if first_segment(rec["path"]) in ROUTES.get(service, set()):
        return "безличное"
    if rec["status"] in REFUSALS:
        return "шум"
    return "непонятное"


def user_of(path: str):
    m = RE_USER.search(path)
    return m.group(1) if m else None


def analyse(entries):
    """Записи -> что известно по каждому порту."""
    ports = collections.defaultdict(
        lambda: {"клиент": 0, "шум": 0, "безличное": 0, "непонятное": 0,
                 "addrs": set(), "users": set(), "last": None, "strange": []})
    window = {"first": None, "last": None}
    # Когда каждого человека в последний раз видели на старых портах и на
    # новых. Без времени вердикт слеп: «заходил на 8443 шесть дней назад» и
    # «ходит на 8443 сейчас» для него одно и то же, хотя между ними как раз и
    # лежит обновление приложения.
    people = collections.defaultdict(lambda: {"old": None, "new": None})
    # То же для обращений, опознанных как клиент, но без user_id в пути.
    anon = {"old": None, "new": None}

    def позже(куда, ключ, когда):
        if когда and (куда[ключ] is None or когда > куда[ключ]):
            куда[ключ] = когда

    for rec, service in entries:
        kind = classify(rec, service)
        p = ports[rec["port"]]
        p[kind] += 1
        if kind == "клиент":
            p["addrs"].add(rec["addr"])
            сторона = "old" if rec["port"] in OLD else "new"
            u = user_of(rec["path"])
            if u:
                p["users"].add(u)
                позже(people[u], сторона, rec["when"])
            else:
                позже(anon, сторона, rec["when"])
            if p["last"] is None or (rec["when"] and rec["when"] > p["last"]):
                p["last"] = rec["when"]
        elif kind in ("непонятное", "безличное") and len(p["strange"]) < 10:
            p["strange"].append(rec["line"])
        if rec["when"]:
            if window["first"] is None or rec["when"] < window["first"]:
                window["first"] = rec["when"]
            if window["last"] is None or rec["when"] > window["last"]:
                window["last"] = rec["when"]
    return ports, window, dict(people), anon


def verdict(ports, expect=(), people=None, anon=None):
    """(код возврата, строки вывода). Код 0 — можно закрывать.

    Решение принимается ПО ЛЮДЯМ И ПО ВРЕМЕНИ, а не по счёту запросов.

    Почему так. 07.11.2026 второй пользователь сказал, что обновился, и
    журналы это подтверждали: на новом 8543 он есть. Но за ту же неделю на
    старом 8443 лежали его же 96 запросов — от 01.11, ДО обновления. Прежний
    вердикт сложил окно целиком и ответил «закрывать рано», хотя шесть дней
    там никого не было. Он не различал «ходил тогда» и «ходит сейчас», а
    ровно между этими двумя моментами и происходит переезд.

    Признак переезда: последний раз человека видели на НОВОМ порту позже, чем
    на старом. Признак застревания: наоборот, либо на новом не видели вовсе.

    expect — user_id, которых обязательно надо увидеть. Без этого списка
    скрипт ручается только за тех, кого застал, и говорит об этом.
    """
    out = []
    people = people or {}
    anon = anon or {"old": None, "new": None}

    def когда(t):
        return f"{t:%d.%m %H:%M}" if t else "не видели"

    застряли = sorted(u for u, t in people.items()
                      if t["old"] and (t["new"] is None or t["old"] > t["new"]))
    переехали = sorted(u for u, t in people.items()
                       if t["old"] and t["new"] and t["new"] > t["old"])
    только_новые = sorted(u for u, t in people.items() if t["new"] and not t["old"])

    if застряли:
        out.append("ЗАКРЫВАТЬ РАНО: эти люди в последний раз приходили на СТАРЫЙ порт.")
        for u in застряли:
            t = people[u]
            out.append(f"  {u}: старый {когда(t['old'])}, новый {когда(t['new'])}")
        out.append("  Их приложения держат старый адрес, и перенос случится только")
        out.append("  при первом запуске новой версии. Закрытие оборвёт их молча.")
        return 1, out

    подтверждены = set(переехали) | set(только_новые)
    missing = sorted(set(expect) - подтверждены)
    if missing:
        out.append("ЖДЁМ ЛЮДЕЙ: на старых портах никто не застрял, но и на новых")
        out.append("видели не всех, кого вы назвали.")
        for u in missing:
            t = people.get(u, {"old": None, "new": None})
            out.append(f"  {u}: старый {когда(t['old'])}, новый {когда(t['new'])}")
        out.append("  «Не заходил» и «перешёл» в журнале выглядят одинаково.")
        return 1, out

    if not подтверждены:
        out.append("ДАННЫХ НЕ ХВАТАЕТ: за это окно опознанных людей не было вовсе —")
        out.append("  ни на старых портах, ни на новых. Тишина на 8443 тут ничего не")
        out.append("  доказывает: она одинаково выглядит и когда все перешли, и когда")
        out.append("  никто не заходил. Подождать и запустить снова.")
        return 1, out

    # Без списка ожидаемых нельзя утверждать, что мы знаем всех, — тогда
    # неопознанное на старых портах остаётся поводом не закрывать.
    strange = sorted(p for p in OLD
                     if ports.get(p, {}).get("непонятное")
                     or ports.get(p, {}).get("безличное"))
    if strange and not expect:
        out.append(f"РАЗБИРАТЬСЯ: на {', '.join(map(str, strange))} есть запросы, про")
        out.append("которые не видно, человек это или нет, а кого ждать — вы не сказали.")
        out.append("  Назовите людей через --expect либо разберите строки:")
        for p in strange:
            for line in ports[p]["strange"]:
                out.append(f"    {line}")
        return 1, out

    out.append("МОЖНО ЗАКРЫВАТЬ: все названные люди подтверждены на новых портах.")
    for u in sorted(подтверждены):
        t = people[u]
        out.append(f"  {u}: старый {когда(t['old'])} -> новый {когда(t['new'])}")

    if anon["old"]:
        out.append("")
        out.append(f"  Оговорка: на старых портах есть обращения, похожие на клиента, но")
        out.append(f"  без user_id в пути; последнее {когда(anon['old'])}. Чьи они — не")
        out.append("  видно. Решение принято по названным вами людям, не по ним.")
    if strange:
        out.append(f"  Там же неопознанного: "
                   f"{sum(ports[p]['безличное'] + ports[p]['непонятное'] for p in strange)} "
                   f"запросов. Примеры:")
        for p in strange:
            for line in ports[p]["strange"][:3]:
                out.append(f"    {line}")
    if not expect:
        out.append("")
        out.append("  Важно: ручаюсь только за тех, кого застал в этом окне. Кого")
        out.append("  ждать — задайте через --expect.")

    out.append("")
    out.append("  убрать listen 8443/8444 из deploy/langbot-tls.conf, поставить конфиг,")
    out.append("  sudo nginx -t && sudo systemctl reload nginx")
    out.append("  sudo ufw delete allow 8443/tcp && sudo ufw delete allow 8444/tcp")
    return 0, out


def rotated(path: str):
    """Сам журнал и все его ротации: file.log, file.log.1, file.log.2.gz…"""
    found = [path] if os.path.exists(path) else []
    found += sorted(glob.glob(path + ".*"))
    return found


def open_log(path: str):
    """Ротации старше первой лежат пожатыми."""
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, encoding="utf-8", errors="replace")


def read_logs(days: int):
    since = datetime.now() - timedelta(days=days)
    entries, read, no_port = [], [], 0
    for base, service in LOGS.items():
        for path in rotated(base):
            try:
                with open_log(path) as fh:
                    read.append(os.path.basename(path))
                    for line in fh:
                        rec = parse_line(line)
                        if rec is None:
                            no_port += 1      # строка старого формата, без порта
                            continue
                        if rec["when"] is None or rec["when"] < since:
                            continue
                        entries.append((rec, service))
            except PermissionError:
                return None, path, 0
            except OSError:
                continue
    return entries, read, no_port


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7, help="за сколько суток смотреть")
    ap.add_argument("--expect", default="",
                    help="user_id через запятую: кого обязательно надо увидеть "
                         "на новых портах, прежде чем закрывать старые")
    args = ap.parse_args()
    expect = [u.strip() for u in args.expect.split(",") if u.strip()]

    entries, read, no_port = read_logs(args.days)
    if entries is None:
        print(f"нет доступа к {read} — запустите под sudo")
        return 2
    if not read:
        print("журналов nginx не найдено")
        return 2

    ports, window, people, anon = analyse(entries)

    print(f"за последние {args.days} сут., прочитано журналов: {len(read)} "
          f"(с ротациями)")
    if window["first"]:
        print(f"окно с портом в журнале: {window['first']:%d.%m %H:%M} — "
              f"{window['last']:%d.%m %H:%M}")
    if no_port:
        print(f"строк старого формата (без порта, до правки): {no_port} — "
              f"по ним порт не определить, они не в счёт")
    print()

    for port in sorted(set(OLD) | set(NEW) | set(ports)):
        tag = "СТАРЫЙ" if port in OLD else ("новый " if port in NEW else "      ")
        p = ports.get(port)
        kinds = ("клиент", "шум", "безличное", "непонятное")
        if not p or not any(p[k] for k in kinds):
            print(f"  {tag} {port}: тишина")
            continue
        print(f"  {tag} {port}: клиентов {p['клиент']}, шума {p['шум']}, "
              f"безличных {p['безличное']}, непонятного {p['непонятное']}")
        if p["клиент"]:
            last = f"{p['last']:%d.%m %H:%M}" if p["last"] else "?"
            print(f"        последний клиент {last}, адресов {len(p['addrs'])}")
            for u in sorted(p["users"]):
                print(f"        user_id {u}")

    code, lines = verdict(ports, expect, people, anon)
    print()
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
