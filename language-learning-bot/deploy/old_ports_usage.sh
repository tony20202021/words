#!/usr/bin/env python
"""
Ходит ли кто-нибудь ещё на старые TLS-порты.

Зачем
-----
31.10.2026 порты сведены к виду 85**: 8443 → 8543 (BLS), 8444 → 8544 (веб).
Старые оставлены слушать на время перехода, и закрыть их надо не наугад.

Причина осторожности: адрес сервера хранится в настройках установленного
приложения, обновление APK его не меняет — перенос делает само приложение при
первом запуске новой версии. Пока хоть один человек приходит на 8443, закрытие
оборвёт ему связь молча: с виду это «нет сети».

Читает журналы nginx, поэтому запускать под sudo:

    sudo python deploy/old_ports_usage.sh
    sudo python deploy/old_ports_usage.sh --days 3
"""

import argparse
import collections
import os
import re
import sys
from datetime import datetime, timedelta

LOGS = ("/var/log/nginx/langbot-bls.access.log",
        "/var/log/nginx/langbot-web.access.log")
OLD, NEW = {8443, 8444}, {8543, 8544}

# port=8443 ... [31/Oct/2026:10:05:01 +0100]
RE_PORT = re.compile(r"port=(\d+)")
RE_TIME = re.compile(r"\[([^\]]+)\]")
RE_ADDR = re.compile(r"^([0-9a-fA-F.:]+)")


def parse_time(line: str):
    m = RE_TIME.search(line)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1).split()[0], "%d/%b/%Y:%H:%M:%S")
    except ValueError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7, help="за сколько суток смотреть")
    args = ap.parse_args()

    since = datetime.now() - timedelta(days=args.days)
    hits = collections.defaultdict(lambda: {"n": 0, "addrs": set(), "last": None})
    no_port = 0
    read = []

    for path in LOGS:
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                read.append(path)
                for line in f:
                    m = RE_PORT.search(line)
                    if not m:
                        no_port += 1          # строка старого формата, без порта
                        continue
                    when = parse_time(line)
                    if when is None or when < since:
                        continue
                    port = int(m.group(1))
                    rec = hits[port]
                    rec["n"] += 1
                    a = RE_ADDR.match(line)
                    if a:
                        rec["addrs"].add(a.group(1))
                    if rec["last"] is None or when > rec["last"]:
                        rec["last"] = when
        except PermissionError:
            print(f"нет доступа к {path} — запустите под sudo")
            return 2

    if not read:
        print("журналов nginx не найдено")
        return 2

    print(f"за последние {args.days} сут., журналы: {', '.join(read)}")
    if no_port:
        print(f"строк старого формата (без порта, до правки): {no_port} — они не в счёт")
    print()
    for port in sorted(set(OLD) | set(NEW) | set(hits)):
        rec = hits.get(port)
        tag = "СТАРЫЙ" if port in OLD else ("новый " if port in NEW else "      ")
        if not rec or not rec["n"]:
            print(f"  {tag} {port}: тишина")
            continue
        print(f"  {tag} {port}: {rec['n']} запросов, адресов {len(rec['addrs'])}, "
              f"последний {rec['last']:%d.%m %H:%M}")
        for a in sorted(rec["addrs"]):
            print(f"        {a}")

    live_old = [p for p in OLD if hits.get(p, {}).get("n")]
    print()
    if live_old:
        print(f"ЗАКРЫВАТЬ РАНО: на {', '.join(map(str, sorted(live_old)))} ещё приходят.")
        return 1
    print("На старые порты никто не приходил — можно закрывать:")
    print("  убрать listen 8443/8444 из deploy/langbot-tls.conf, поставить конфиг,")
    print("  sudo nginx -t && sudo systemctl reload nginx")
    print("  sudo ufw delete allow 8443/tcp && sudo ufw delete allow 8444/tcp")
    return 0


if __name__ == "__main__":
    sys.exit(main())
