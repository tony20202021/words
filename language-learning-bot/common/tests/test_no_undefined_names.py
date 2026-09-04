"""Имя используется, но не импортировано — падение при первом же вызове.

Так едва не уехала отметка прослушанного варианта в Telegram: `suppress`
вызывался в обработчике и не был импортирован. Модуль импортировался
нормально, тесты были зелёные — NameError ждал первого нажатия кнопки.

Линтера в проекте нет, поэтому проверка своя и намеренно узкая: ищем имена,
которые модуль использует, но нигде не определяет и не импортирует. Ложные
срабатывания гасим списком встроенных имён.
"""
import ast
import builtins
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ["telegram_bot/app", "web_frontend/app", "business_logic_service/app",
            "backend/app", "common"]
BUILTINS = set(dir(builtins)) | {"__file__", "__name__", "__doc__", "__package__"}


def module_files():
    for pkg in PACKAGES:
        for path in sorted((ROOT / pkg).rglob("*.py")):
            if "__pycache__" in path.parts or "/tests/" in str(path):
                continue
            yield path


def defined_names(tree: ast.AST) -> set:
    """Всё, что модуль связывает сам: импорты, присваивания, def, class, аргументы."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names |= {(a.asname or a.name).split(".")[0] for a in node.names}
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            # У лямбды имени нет, зато есть аргументы — без них «lambda i: ...»
            # выглядит как использование неопределённого i.
            if not isinstance(node, ast.Lambda):
                names.add(node.name)
            args = getattr(node, "args", None)
            if args:
                for a in (args.posonlyargs + args.args + args.kwonlyargs):
                    names.add(a.arg)
                for a in (args.vararg, args.kwarg):
                    if a:
                        names.add(a.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            names.add(node.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            names |= set(node.names)
        elif isinstance(node, ast.comprehension):
            for sub in ast.walk(node.target):
                if isinstance(sub, ast.Name):
                    names.add(sub.id)
    return names


@pytest.mark.parametrize("path", list(module_files()), ids=lambda p: str(p.name))
def test_module_uses_only_names_it_has(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    known = defined_names(tree) | BUILTINS
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    missing = sorted(used - known)
    assert not missing, f"{path.relative_to(ROOT)}: имена без определения — {missing}"
