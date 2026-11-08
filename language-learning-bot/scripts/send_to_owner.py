#!/usr/bin/env python3
"""
Послать владельцу сообщение или файл — от имени бота, в личный чат.

Зачем. Картинку, отчёт или собранный файл надо как-то отдать человеку, а он
сидит не за этим сервером. Телеграм для этого уже есть: бот знает владельца,
владелец знает бота. Через этот путь, например, уезжали варианты аватарки.

Про токен. Он читается из .env внутри Python и никуда не печатается.
Исключения httpx показывают URL целиком, а в нём токен, — поэтому при ошибке
печатается только ТИП исключения, без текста.

Про получателя. Номер в коде не зашит: берётся telegram_id администратора из
базы. Зашитый номер пришлось бы менять при каждой смене владельца, а в
репозитории ему и вовсе не место.

Запуск:
    python scripts/send_to_owner.py --text "готово"
    python scripts/send_to_owner.py --file отчёт.png --text "вот отчёт"
    python scripts/send_to_owner.py --file a.png --file b.png --text "два"
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
API = "https://api.telegram.org"

# Картинки Telegram показывает прямо в переписке, остальное — вложением.
КАРТИНКИ = {".png", ".jpg", ".jpeg", ".webp"}


def env(key: str) -> str:
    try:
        for line in ENV.read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def chat_id_владельца() -> int:
    """telegram_id администратора — чтобы номер не лежал в коде."""
    from pymongo import MongoClient
    db = MongoClient(env("MONGODB_URL"), serverSelectionTimeoutMS=5000)[
        env("MONGODB_DB_NAME") or "language_learning_bot"]
    u = db.users.find_one({"is_admin": True, "telegram_id": {"$ne": None}})
    if not u:
        raise SystemExit("в базе нет администратора с telegram_id")
    return int(u["telegram_id"])


def послать(token: str, chat: int, путь: Path | None, текст: str) -> bool:
    import httpx
    try:
        if путь is None:
            r = httpx.post(f"{API}/bot{token}/sendMessage",
                           data={"chat_id": chat, "text": текст}, timeout=60)
        else:
            поле = "photo" if путь.suffix.lower() in КАРТИНКИ else "document"
            метод = "sendPhoto" if поле == "photo" else "sendDocument"
            with open(путь, "rb") as fh:
                r = httpx.post(f"{API}/bot{token}/{метод}",
                               data={"chat_id": chat, "caption": текст},
                               files={поле: (путь.name, fh)}, timeout=120)
        ok = r.status_code == 200 and r.json().get("ok")
        print(f"  {путь.name if путь else 'текст'}: "
              f"{'отправлено' if ok else r.json().get('description', r.status_code)}")
        return bool(ok)
    except Exception as e:
        # Только тип: в тексте исключения httpx лежит URL, а в нём токен.
        print(f"  {путь.name if путь else 'текст'}: не вышло, {type(e).__name__}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text", default="", help="текст или подпись к файлу")
    ap.add_argument("--file", action="append", default=[], help="файл (можно несколько)")
    ap.add_argument("--chat-id", type=int, default=0, help="кому, если не владельцу")
    args = ap.parse_args()

    if not args.text and not args.file:
        raise SystemExit("нечего посылать: нужен --text или --file")

    token = env("BOT_TOKEN")
    if not token:
        raise SystemExit("в .env нет BOT_TOKEN")
    chat = args.chat_id or chat_id_владельца()

    пути = [Path(f) for f in args.file]
    нет = [p for p in пути if not p.exists()]
    if нет:
        raise SystemExit("нет таких файлов: " + ", ".join(str(p) for p in нет))

    плохо = 0
    if not пути:
        плохо += not послать(token, chat, None, args.text)
    for i, p in enumerate(пути):
        # Подпись только у первого: иначе она повторится под каждым файлом.
        плохо += not послать(token, chat, p, args.text if i == 0 else "")
    return 1 if плохо else 0


if __name__ == "__main__":
    sys.exit(main())
