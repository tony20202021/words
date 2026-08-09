#!/usr/bin/env python
"""
Script to run tests for the Language Learning Bot project.
Runs tests for all active components: BLS, telegram_bot, web_frontend,
backend, common, android.

Android-тесты идут через gradle, а не pytest, и раньше в этот скрипт не входили —
из-за чего «прогнал все тесты» не включало клиент, где половина офлайн-логики.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).absolute().parent
PROJECT_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "scripts" else SCRIPT_DIR

COMPONENT_DIRS = {
    "bls": PROJECT_ROOT / "business_logic_service",
    "android": PROJECT_ROOT / "android",
    "telegram": PROJECT_ROOT / "telegram_bot",
    "web": PROJECT_ROOT / "web_frontend",
    "backend": PROJECT_ROOT / "backend",
    "common": PROJECT_ROOT / "common",
}

def setup_parser():
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(description="Run tests for Language Learning Bot")
    parser.add_argument(
        "--component",
        "-c",
        choices=["bls", "telegram", "web", "backend", "common", "android", "all"],
        default="all",
        help="Component to test (default: all)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run tests with coverage",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML coverage report",
    )
    parser.add_argument(
        "--specific",
        "-s",
        type=str,
        help="Run a specific test module or function (e.g., test_main.py::TestMain::test_on_startup)",
    )
    parser.add_argument(
        "--pytest-args",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to pytest",
    )
    parser.add_argument(
        "--exitfirst",
        "--x",
        action="store_true",
        help="Exit pytest immediately on first error",
    )
    return parser


# Сколько тестов должно собраться в каждом компоненте. Это НЕ проверка качества,
# а защита от тихой пропажи: дважды за неделю тесты переставали запускаться, и оба
# раза раннер рапортовал успех. В 5093835 путь компонента указывал на удалённый
# сервис, и его тесты «проходили», не существуя, шесть недель. Число поднимать
# осознанно, вместе с новыми тестами.
EXPECTED_MIN = {
    "bls": 310, "telegram": 237, "web": 152, "backend": 140, "common": 18, "android": 72,
}


def collected_count(output: str) -> int | None:
    """Сколько тестов реально прошло, по хвосту вывода pytest."""
    m = re.findall(r"(\d+) passed", output)
    return int(m[-1]) if m else None


def check_count(name: str, got: int | None) -> int:
    """0 если собрано не меньше ожидаемого, иначе 1 и объяснение."""
    want = EXPECTED_MIN.get(name)
    if want is None:
        return 0
    if got is None:
        print(f"❌ {name}: не удалось определить число тестов — считаем это провалом, "
              f"молчаливый успех уже дважды скрывал неработающий прогон")
        return 1
    if got < want:
        print(f"❌ {name}: собрано {got}, ожидалось не меньше {want} — "
              f"тесты пропали или перестали собираться")
        return 1
    if got > want:
        print(f"ℹ️  {name}: тестов стало больше ({got} > {want}) — обновите EXPECTED_MIN")
    return 0


def run_component_tests(name: str, directory: Path, args, extra_pytest_args=None):
    """Run pytest in a component directory. Returns exit code."""
    label = name.replace("_", " ").title()
    print(f"\n🔍 Running {label} tests...\n")

    # Отсутствие каталога или тестов — это НЕ успех. Компонент перечислен в
    # COMPONENT_DIRS, значит его тесты обязаны существовать и запускаться;
    # если он удалён — удалите его и отсюда.
    if not directory.exists():
        print(f"❌ Directory not found: {directory}")
        return 1

    os.chdir(directory)
    tests_dir = Path("tests")
    if not tests_dir.exists() or not list(tests_dir.rglob("test_*.py")):
        print(f"❌ No test files found in {directory}/tests")
        return 1

    cmd = ["pytest"]
    # --coverage и --html объявлены в argparse с самого начала и никогда не
    # читались: запуск с ними молча шёл без покрытия и рапортовал успех.
    if args.coverage:
        cmd.extend(["--cov=app", "--cov-report=term-missing"])
        if args.html:
            cmd.append("--cov-report=html")
    elif args.html:
        print("⚠️  --html без --coverage ничего не даёт")
    if args.verbose:
        cmd.append("-v")
    if args.exitfirst:
        cmd.append("-x")
    if args.specific:
        cmd.append(args.specific)
    if extra_pytest_args:
        cmd.extend(extra_pytest_args)
    if args.pytest_args:
        cmd.extend(args.pytest_args)

    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    # Код 5 — ничего не собрано. Послабление держали ради модульных скипов в
    # writing_images_service; сервис удалён, скипов в проекте не осталось ни
    # одного, так что теперь это просто «тесты не нашлись».
    if result.returncode == 5:
        print(f"❌ {label}: ни один тест не собран")
        return 1
    if result.returncode != 0:
        return result.returncode
    if args.specific or args.pytest_args:
        return 0   # прогон подмножества — счётчик не про него
    return check_count(name, collected_count(result.stdout))


def run_backend_tests(args):
    return run_component_tests("backend", COMPONENT_DIRS["backend"], args)


def run_common_tests(args):
    return run_component_tests("common", COMPONENT_DIRS["common"], args)



def run_bls_tests(args):
    return run_component_tests("bls", COMPONENT_DIRS["bls"], args)


def run_telegram_tests(args):
    return run_component_tests("telegram", COMPONENT_DIRS["telegram"], args)


def run_web_tests(args):
    return run_component_tests("web", COMPONENT_DIRS["web"], args)


def android_test_count(directory: Path) -> int | None:
    """Сколько тестов отчитал gradle: -q ничего не печатает, читаем отчёты."""
    import xml.etree.ElementTree as ET
    results = directory / "app" / "build" / "test-results" / "testDebugUnitTest"
    if not results.exists():
        return None
    total = 0
    for xml in results.glob("*.xml"):
        try:
            total += int(ET.parse(xml).getroot().get("tests", 0))
        except Exception:
            return None
    return total


def run_android_tests(args):
    """JVM-тесты андроида (gradle testDebugUnitTest) — без эмулятора."""
    directory = COMPONENT_DIRS["android"]
    print("\n🔍 Running Android tests...\n")
    # Пропуск при отсутствии gradlew был бы ровно тем же «нет тестов = зелено»,
    # из-за которого шесть недель не запускались тесты удалённого сервиса.
    if not (directory / "gradlew").exists():
        print(f"❌ gradlew не найден в {directory}")
        return 1

    os.chdir(directory)
    cmd = ["./gradlew", "testDebugUnitTest"]
    if not args.verbose:
        cmd.append("-q")
    if args.specific:
        cmd.extend(["--tests", args.specific])
    print(f"Running command: {' '.join(cmd)}")
    code = subprocess.run(cmd).returncode
    if code != 0:
        return code
    if args.specific:
        return 0
    n = android_test_count(directory)
    print(f"  тестов в отчётах gradle: {n}")
    return check_count("android", n)


def main():
    """Main function to run tests."""
    parser = setup_parser()
    args = parser.parse_args()

    print("🚀 Starting test runner for Language Learning Bot")
    print(f"📂 Project root: {PROJECT_ROOT}")

    runners = {
        "bls": run_bls_tests,
        "telegram": run_telegram_tests,
        "web": run_web_tests,
        "backend": run_backend_tests,
        "common": run_common_tests,
        "android": run_android_tests,
    }

    if args.component == "all":
        components = ["bls", "telegram", "web", "backend", "common", "android"]
    else:
        components = [args.component]

    failed = []
    for comp in components:
        code = runners[comp](args)
        if code != 0:
            print(f"\n❌ {comp} tests failed!")
            failed.append(comp)
        else:
            print(f"\n✅ {comp} tests passed or no tests found!")

    if failed:
        print(f"\n❌ Failed components: {', '.join(failed)}")
        return 1

    print("\n✅ All tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
    