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
import os
import re
import sys
from datetime import datetime, timedelta

LOGS = {
    "/var/log/nginx/langbot-bls.access.log": "bls",
    "/var/log/nginx/langbot-web.access.log": "web",
}
OLD, NEW = {8443, 8444}, {8543, 8544}

# Первые сегменты путей, которые службы действительно обслуживают. Собраны из
# роутеров: business_logic_service/app и web_frontend/app. Список нужен, чтобы
# отличить «наш клиент получил законный 404» от «сканер щупал чужую админку».
ROUTES = {
    "bls": {
        "admin", "auth", "batch", "confirm", "create", "deny", "get_or_create",
        "health", "help", "hints", "languages", "lookup", "mobile", "qr",
        "results", "session", "settings", "sounds", "statistics", "stats",
        "status", "timezones", "user", "users", "version", "words",
    },
    "web": {
        "", "admin", "auth", "autologin", "broadcast", "connect", "diagnostics",
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
    r"|securityscanner|stretchoid|CriminalIP", re.I)

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
    for rec, service in entries:
        kind = classify(rec, service)
        p = ports[rec["port"]]
        p[kind] += 1
        if kind == "клиент":
            p["addrs"].add(rec["addr"])
            u = user_of(rec["path"])
            if u:
                p["users"].add(u)
            if p["last"] is None or (rec["when"] and rec["when"] > p["last"]):
                p["last"] = rec["when"]
        elif kind in ("непонятное", "безличное") and len(p["strange"]) < 10:
            p["strange"].append(rec["line"])
        if rec["when"]:
            if window["first"] is None or rec["when"] < window["first"]:
                window["first"] = rec["when"]
            if window["last"] is None or rec["when"] > window["last"]:
                window["last"] = rec["when"]
    return ports, window


def verdict(ports, expect=()):
    """(код возврата, строки вывода). Код 0 — можно закрывать.

    expect — user_id, которых обязательно надо увидеть на новых портах.
    Без этого списка скрипт ручается только за тех, кого застал: человек,
    не заходивший за окно наблюдения, в журнале неотличим от перешедшего, а
    его приложение всё это время держит старый адрес.
    """
    out = []
    busy = sorted(p for p in OLD if ports.get(p, {}).get("клиент"))
    strange = sorted(p for p in OLD
                     if ports.get(p, {}).get("непонятное")
                     or ports.get(p, {}).get("безличное"))
    clients_new = sorted(p for p in NEW if ports.get(p, {}).get("клиент"))

    if busy:
        out.append(f"ЗАКРЫВАТЬ РАНО: на {', '.join(map(str, busy))} приходят живые клиенты.")
        for p in busy:
            users = ", ".join(sorted(ports[p]["users"])) or "id не видно в путях"
            out.append(f"  {p}: {ports[p]['клиент']} запросов, кто: {users}")
        return 1, out

    if strange:
        out.append(f"РАЗБИРАТЬСЯ: на {', '.join(map(str, strange))} есть запросы, "
                   f"про которые не видно, человек это или нет.")
        out.append("  Неизвестное — не то же самое, что безвредное. Строки:")
        for p in strange:
            for line in ports[p]["strange"]:
                out.append(f"    {line}")
        return 1, out

    if not clients_new:
        out.append("ДАННЫХ НЕ ХВАТАЕТ: за это окно клиентов не было вообще — ни на старых")
        out.append("  портах, ни на новых. Тишина на 8443 тут ничего не доказывает: она")
        out.append("  одинаково выглядит и когда все перешли, и когда никто не заходил.")
        out.append("  Подождать, пока люди позанимаются, и запустить снова.")
        return 1, out

    seen = set()
    for p in clients_new:
        seen |= ports[p]["users"]
    missing = sorted(set(expect) - seen)
    if missing:
        out.append("ЖДЁМ ЛЮДЕЙ: на старых портах чисто, но на новых видели не всех.")
        out.append(f"  не появлялись: {', '.join(missing)}")
        out.append("  Их приложения всё это время держат старый адрес, и перенос")
        out.append("  случится только при первом запуске новой версии. Пока они не")
        out.append("  зайдут, закрытие оборвёт их молча.")
        return 1, out

    out.append("МОЖНО ЗАКРЫВАТЬ: на старых портах только шум сканеров, а клиенты")
    out.append("подтверждены на новых:")
    for p in clients_new:
        users = ", ".join(sorted(ports[p]["users"])) or "id не видно в путях"
        out.append(f"  {p}: {ports[p]['клиент']} запросов, кто: {users}")
    if not expect:
        out.append("")
        out.append("  Важно: ручаюсь только за тех, кого застал в этом окне. Человек,")
        out.append("  который просто не заходил, выглядит в журнале так же, как")
        out.append("  перешедший. Журналы nginx ротируются раз в сутки, поэтому окно")
        out.append("  короче, чем --days. Кого ждать — задайте через --expect.")
    out.append("")
    out.append("  убрать listen 8443/8444 из deploy/langbot-tls.conf, поставить конфиг,")
    out.append("  sudo nginx -t && sudo systemctl reload nginx")
    out.append("  sudo ufw delete allow 8443/tcp && sudo ufw delete allow 8444/tcp")
    return 0, out


def read_logs(days: int):
    since = datetime.now() - timedelta(days=days)
    entries, read, no_port = [], [], 0
    for path, service in LOGS.items():
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                read.append(path)
                for line in fh:
                    rec = parse_line(line)
                    if rec is None:
                        no_port += 1          # строка старого формата, без порта
                        continue
                    if rec["when"] is None or rec["when"] < since:
                        continue
                    entries.append((rec, service))
        except PermissionError:
            return None, path, 0
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

    ports, window = analyse(entries)

    print(f"за последние {args.days} сут., журналы: {', '.join(read)}")
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

    code, lines = verdict(ports, expect)
    print()
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
