#!/usr/bin/env python
"""
Script to run tests for the Language Learning Bot project.
Allows running tests for frontend, backend, or both components.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Define project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_DIR = PROJECT_ROOT / "backend"


def setup_parser():
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(description="Run tests for Language Learning Bot")
    parser.add_argument(
        "--component",
        "-c",
        choices=["frontend", "backend", "all"],
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
    return parser


def run_frontend_tests(args):
    """Run frontend tests."""
    print("\n🔍 Running frontend tests...\n")
    os.chdir(FRONTEND_DIR)
    
    # Проверяем наличие директории с тестами
    tests_dir = Path("tests")
    if not tests_dir.exists() or not list(tests_dir.glob("test_*.py")):
        print("⚠️ No test files found in frontend/tests directory!")
        print("✅ Frontend tests: No tests to run!")
        return 0
    
    cmd = ["pytest"]
    
    if args.verbose:
        cmd.append("-v")
    
    if args.coverage:
        cmd.extend(["--cov=app", "--cov-report=term"])
        if args.html:
            cmd.append("--cov-report=html")
    
    if args.specific:
        cmd.append(args.specific)
    
    result = subprocess.run(cmd)
    
    # Проверяем код возврата
    if result.returncode != 0:
        # Проверяем, могла ли быть ошибка из-за отсутствия тестов
        try:
            # Запускаем pytest с минимальными параметрами для проверки сбора тестов
            check_cmd = ["pytest", "--collect-only", "-q"]
            output = subprocess.check_output(check_cmd, stderr=subprocess.STDOUT, text=True)
            
            # Если в выводе есть "no tests", значит тестов просто нет
            if "no tests" in output.lower():
                print("⚠️ Pytest found no tests in frontend directory")
                print("✅ Frontend tests: No tests to run!")
                return 0
        except subprocess.CalledProcessError:
            # Если сбор тестов тоже дал ошибку, вернем оригинальный код ошибки
            pass
    
    return result.returncode


def run_backend_tests(args):
    """Run backend tests."""
    print("\n🔍 Running backend tests...\n")
    os.chdir(BACKEND_DIR)
    
    # Проверяем наличие директории с тестами
    tests_dir = Path("tests")
    if not tests_dir.exists() or not list(tests_dir.glob("test_*.py")):
        print("⚠️ No test files found in backend/tests directory!")
        print("✅ Backend tests: No tests to run!")
        return 0
    
    cmd = ["pytest"]
    
    if args.verbose:
        cmd.append("-v")
    
    if args.coverage:
        cmd.extend(["--cov=app", "--cov-report=term"])
        if args.html:
            cmd.append("--cov-report=html")
    
    if args.specific:
        cmd.append(args.specific)
    
    result = subprocess.run(cmd)
    
    # Проверяем код возврата
    if result.returncode != 0:
        # Проверяем, могла ли быть ошибка из-за отсутствия тестов
        try:
            # Запускаем pytest с минимальными параметрами для проверки сбора тестов
            check_cmd = ["pytest", "--collect-only", "-q"]
            output = subprocess.check_output(check_cmd, stderr=subprocess.STDOUT, text=True)
            
            # Если в выводе есть "no tests", значит тестов просто нет
            if "no tests" in output.lower():
                print("⚠️ Pytest found no tests in backend directory")
                print("✅ Backend tests: No tests to run!")
                return 0
        except subprocess.CalledProcessError:
            # Если сбор тестов тоже дал ошибку, вернем оригинальный код ошибки
            pass
    
    return result.returncode


def main():
    """Main function to run tests."""
    parser = setup_parser()
    args = parser.parse_args()
    
    print(f"🚀 Starting test runner for Language Learning Bot")
    print(f"📂 Project root: {PROJECT_ROOT}")
    
    frontend_exit_code = 0
    backend_exit_code = 0
    
    if args.component in ["frontend", "all"]:
        frontend_exit_code = run_frontend_tests(args)
        if frontend_exit_code != 0:
            print("\n❌ Frontend tests failed!")
        else:
            print("\n✅ Frontend tests passed or no tests found!")
    
    if args.component in ["backend", "all"]:
        backend_exit_code = run_backend_tests(args)
        if backend_exit_code != 0:
            print("\n❌ Backend tests failed!")
        else:
            print("\n✅ Backend tests passed or no tests found!")
    
    # Return non-zero if any test suite failed
    if frontend_exit_code != 0 or backend_exit_code != 0:
        print("\n❌ Some tests failed!")
        return 1
    
    print("\n✅ All tests passed or no tests found!")
    return 0


if __name__ == "__main__":
    sys.exit(main())