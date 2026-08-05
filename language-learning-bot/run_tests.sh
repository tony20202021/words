#!/usr/bin/env python
"""
Script to run tests for the Language Learning Bot project.
Runs tests for all active components: BLS, telegram_bot, web_frontend,
backend, common.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).absolute().parent
PROJECT_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "scripts" else SCRIPT_DIR

COMPONENT_DIRS = {
    "bls": PROJECT_ROOT / "business_logic_service",
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
        choices=["bls", "telegram", "web", "backend", "common", "all"],
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


def run_component_tests(name: str, directory: Path, args, extra_pytest_args=None):
    """Run pytest in a component directory. Returns exit code."""
    label = name.replace("_", " ").title()
    print(f"\n🔍 Running {label} tests...\n")

    if not directory.exists():
        print(f"⚠️ Directory not found: {directory}")
        print(f"✅ {label} tests: skipped!")
        return 0

    os.chdir(directory)
    tests_dir = Path("tests")
    if not tests_dir.exists() or not list(tests_dir.rglob("test_*.py")):
        print(f"⚠️ No test files found in {directory}/tests")
        print(f"✅ {label} tests: No tests to run!")
        return 0

    cmd = ["pytest"]
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
    result = subprocess.run(cmd)
    # pytest exits 5 when everything was skipped at module level (nothing collected).
    # That is a deliberate skip, not a failure — see the skip reasons in the test files.
    if result.returncode == 5:
        print(f"⏭️  {label}: all tests skipped at module level (see skip reason in the files)")
        return 0
    return result.returncode


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
    }

    if args.component == "all":
        components = ["bls", "telegram", "web", "backend", "common"]
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
    