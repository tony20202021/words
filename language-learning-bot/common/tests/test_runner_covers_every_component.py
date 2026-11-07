"""
Компонент, добавленный в каталоги и забытый в списке «все», молча не
запускается.

В самом run_tests.sh про эту беду написано дважды: в 5093835 путь компонента
указывал на удалённый сервис, и его тесты «проходили», не существуя, шесть
недель. Но список компонентов для «all» там всё равно перечислен отдельно от
COMPONENT_DIRS, и разъехаться им ничего не мешает — 07.11.2026 я сам добавил
компонент tts в каталоги, а в список забыл, и прогон «всех» его не видел.

Проверка читает ИСХОДНИК раннера: запускать его ради этого незачем, а
сравнивать надо именно те три места, которые обязаны совпадать.
"""
import ast
from pathlib import Path

RUNNER = Path(__file__).resolve().parents[2] / "run_tests.sh"


def _dict_keys(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if name in targets and isinstance(node.value, ast.Dict):
                return {k.value for k in node.value.keys if isinstance(k, ast.Constant)}
    raise AssertionError(f"в раннере не нашёлся словарь {name}")


def _all_list(tree):
    """Список компонентов, который перебирается при --component all."""
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign)
                and any(getattr(t, "id", "") == "components" for t in node.targets)
                and isinstance(node.value, ast.List)):
            return {e.value for e in node.value.elts if isinstance(e, ast.Constant)}
    raise AssertionError("в раннере не нашёлся список компонентов для «all»")


def test_every_known_component_is_actually_run():
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    известные = _dict_keys(tree, "COMPONENT_DIRS")
    запускаемые = _all_list(tree)

    забыты = известные - запускаемые
    assert not забыты, (
        f"компоненты есть в COMPONENT_DIRS, но «all» их не запускает: "
        f"{sorted(забыты)} — их тесты молча не выполняются")


def test_every_component_has_an_expected_count():
    """
    Без ожидаемого числа компонент может перестать собирать тесты, и раннер
    отрапортует успех: ровно та тихая пропажа, ради которой числа и заведены.
    """
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    известные = _dict_keys(tree, "COMPONENT_DIRS")
    с_числом = _dict_keys(tree, "EXPECTED_MIN")

    без_числа = известные - с_числом
    assert not без_числа, (
        f"у этих компонентов нет ожидаемого числа тестов: {sorted(без_числа)}")
