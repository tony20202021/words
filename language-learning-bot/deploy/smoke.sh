#!/usr/bin/env python
"""
Смоук после выкладки: подхватили ли сервисы то, что мы им положили.

Зачем
-----
В правилах проекта записано «проверяй, что сервисы перезапустились и подхватили
изменения», но проверялось это только прозой в теле коммита. Дважды за неделю
проза расходилась с реальностью:

  70de9f3  версию подняли, APK не пересобрали — приложение предлагало обновиться
           до сборки, которой нет;
  e7af675  поля посчитали и записали в Mongo, а API продолжал отдавать None,
           потому что бэкенд не перезапускали (у его юнита нет --reload).

Обе ошибки видны за секунду, если спросить у работающей системы, а не у себя.

Что проверяется
---------------
  версии          /version у BLS совпадает с common/version.py
  APK             versionCode внутри отдаваемого файла совпадает с версией,
                  и файл совпадает с собранным локально
  поля            слово через публичный API содержит ожидаемые поля
  доступность     веб отвечает на /login
  безопасность    прокси звука отбивает обход каталога

Использование
-------------
    python deploy/smoke.sh                  # против боевого хоста
    python deploy/smoke.sh --host localhost --bls-port 8531 --web-port 8548
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
APK = os.path.join(ROOT, "android", "LangBot.apk")

# Сертификат выписан на IP и живёт шесть дней; проверка цепочки здесь не цель.
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

_results: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    _results.append((ok, name, detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f" — {detail}" if detail else ""))
    return ok


def get(url: str, timeout: int = 20) -> bytes | None:
    try:
        return urllib.request.urlopen(url, timeout=timeout, context=_CTX).read()
    except urllib.error.HTTPError as e:
        return None if e.code >= 400 else e.read()
    except Exception:
        return None


def status(url: str, timeout: int = 20) -> int:
    try:
        return urllib.request.urlopen(url, timeout=timeout, context=_CTX).status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def local_version() -> str:
    src = open(os.path.join(ROOT, "common", "version.py"), encoding="utf-8").read()
    return re.search(r'__version__\s*=\s*["\'](.+?)["\']', src).group(1)


def version_code(version: str) -> int:
    major, minor, patch = (int(x) for x in version.split("."))
    return major * 10000 + minor * 100 + patch


def apk_version_code(blob: bytes, tmp: str) -> int | None:
    """versionCode из манифеста APK. Читаем из самого файла, не из имени."""
    with open(tmp, "wb") as fh:
        fh.write(blob)
    try:
        out = subprocess.run(["aapt", "dump", "badging", tmp],
                             capture_output=True, text=True, timeout=60).stdout
        m = re.search(r"versionCode='(\d+)'", out)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    # aapt может быть не в PATH — тогда достаём строку версии из манифеста.
    try:
        with zipfile.ZipFile(tmp) as z:
            manifest = z.read("AndroidManifest.xml").decode("utf-16-le", errors="ignore")
        found = sorted(set(re.findall(r"\d+\.\d+\.\d+", manifest)))
        if len(found) == 1:
            return version_code(found[0])
    except Exception:
        pass
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="77.81.226.56")
    ap.add_argument("--bls-port", type=int, default=8443, help="порт BLS (через nginx)")
    ap.add_argument("--web-port", type=int, default=8444, help="порт веба (через nginx)")
    ap.add_argument("--scheme", default="https")
    ap.add_argument("--word-id", default="", help="id слова для проверки полей API")
    ap.add_argument("--backend", default="http://localhost:8573")
    args = ap.parse_args()

    bls = f"{args.scheme}://{args.host}:{args.bls_port}"
    web = f"{args.scheme}://{args.host}:{args.web_port}"
    want = local_version()
    print(f"версия в common/version.py: {want}\n")

    # ── версии ──────────────────────────────────────────────────────────────
    raw = get(f"{bls}/version")
    if check("BLS отвечает на /version", raw is not None):
        data = json.loads(raw)
        check("версия BLS совпадает с исходником", data.get("version") == want,
              f"отдаёт {data.get('version')}, ожидалось {want}")
        check("version_code согласован с версией",
              data.get("version_code") == version_code(want),
              f"отдаёт {data.get('version_code')}, ожидалось {version_code(want)}")

    # ── APK ─────────────────────────────────────────────────────────────────
    blob = get(f"{web}/download/android", timeout=120)
    if check("APK отдаётся", blob is not None and len(blob) > 1_000_000,
             f"{len(blob) if blob else 0} байт"):
        tmp = os.path.join(HERE, ".smoke.apk")
        try:
            code = apk_version_code(blob, tmp)
            check("versionCode внутри APK совпадает с версией",
                  code == version_code(want),
                  f"в бинарнике {code}, ожидалось {version_code(want)}")
            if os.path.exists(APK):
                same = hashlib.sha256(blob).hexdigest() == \
                       hashlib.sha256(open(APK, "rb").read()).hexdigest()
                check("отдаётся тот же файл, что собран локально", same,
                      "" if same else "сервер отдаёт другую сборку")
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    # ── поля слова через API ────────────────────────────────────────────────
    if args.word_id:
        raw = get(f"{args.backend}/api/words/{args.word_id}")
        if check("слово читается через API бэкенда", raw is not None):
            w = json.loads(raw)
            for field in ("word_foreign", "translation", "part_of_speech", "lemma"):
                check(f"поле {field} доезжает", w.get(field) not in (None, ""),
                      f"{field}={w.get(field)!r}")

    # ── доступность и безопасность ──────────────────────────────────────────
    check("веб отвечает на /login", status(f"{web}/login") == 200)
    code = status(f"{web}/sound/%2e%2e%2f%2e%2e%2fetc%2fx.mp3")
    check("прокси звука отбивает обход каталога", code == 400, f"HTTP {code}")

    failed = [r for r in _results if not r[0]]
    print(f"\nпроверок: {len(_results)}, провалено: {len(failed)}")
    if failed:
        print("\nсмоук НЕ пройден:")
        for _, name, detail in failed:
            print(f"  {name}" + (f" — {detail}" if detail else ""))
        return 1
    print("смоук пройден")
    return 0


if __name__ == "__main__":
    sys.exit(main())
