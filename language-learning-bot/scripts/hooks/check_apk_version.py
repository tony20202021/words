#!/usr/bin/env python
"""
Версия внутри собранного APK против common/version.py.

Отдельным файлом, а не строкой в хуке: разбор бинарного манифеста на shell
получается ненадёжным. Первая попытка была на iconv и молча отдавала пустую
строку — проверка «проходила» всегда, то есть повторяла ровно тот дефект
«нет данных = успех», ради которого чинился run_tests.sh.

Неопределимая версия здесь — ошибка. Если прочитать нечего, мы не знаем,
совпадает она или нет, и молчать об этом нельзя.
"""

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APK = ROOT / "android" / "LangBot.apk"


def source_version() -> str:
    src = (ROOT / "common" / "version.py").read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*["\'](.+?)["\']', src)
    if not m:
        sys.exit("pre-push: не нашёл __version__ в common/version.py")
    return m.group(1)


def apk_version() -> str:
    if not APK.exists():
        sys.exit(f"pre-push: нет собранного APK: {APK}")
    with zipfile.ZipFile(APK) as z:
        manifest = z.read("AndroidManifest.xml").decode("utf-16-le", errors="ignore")
    found = sorted(set(re.findall(r"\d+\.\d+\.\d+", manifest)))
    if len(found) != 1:
        sys.exit(f"pre-push: не смог определить версию внутри APK (нашёл {found}). "
                 f"Не зная её, пропускать проверку нельзя.")
    return found[0]


def main() -> int:
    want, got = source_version(), apk_version()
    if want != got:
        print("\npre-push: ВЕРСИЯ В APK НЕ СОВПАДАЕТ — push остановлен.", file=sys.stderr)
        print(f"  common/version.py:   {want}", file=sys.stderr)
        print(f"  android/LangBot.apk: {got}", file=sys.stderr)
        print("Пересоберите APK или верните версию. "
              "Осознанно пропустить: SKIP_TESTS=1", file=sys.stderr)
        return 1
    print(f"pre-push: версия в APK совпадает ({want})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
