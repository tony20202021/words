"""
Раннер обязан объяснить, почему упал android.

08.11.2026: прогон сказал «android tests failed» и больше ничего. Разбор занял
полчаса, и выяснилось, что не упала ни одна проверка — все 282 прошли, а
споткнулась сама сборка gradle. Вывод подавлен ключом -q, отчёты никто не
читал, и сообщение было одинаковым что для упавшего теста, что для сорванной
сборки. Эти два случая надо различать вслух.

Проверяется разбор отчётов gradle: раннер читает их сам, поэтому подделка
здесь — настоящий формат XML, который пишет gradle, а не выдумка.
"""
import ast
import sys
from pathlib import Path

КОРЕНЬ = Path(__file__).resolve().parents[2]
RUNNER = КОРЕНЬ / "run_tests.sh"


def _загрузить_раннер():
    """Раннер — это python-файл с расширением .sh; грузим его как модуль."""
    import importlib.util
    spec = importlib.util.spec_from_loader("runner_under_test", loader=None)
    модуль = importlib.util.module_from_spec(spec)
    модуль.__dict__["__name__"] = "runner_under_test"
    # Раннер вычисляет корень проекта от __file__; без него не загрузится.
    модуль.__dict__["__file__"] = str(RUNNER)
    код = RUNNER.read_text(encoding="utf-8")
    # Отрезаем запуск: нас интересуют только функции.
    дерево = ast.parse(код)
    дерево.body = [n for n in дерево.body
                   if not (isinstance(n, ast.If)
                           and getattr(getattr(n.test, "left", None), "id", "") == "__name__")]
    exec(compile(дерево, str(RUNNER), "exec"), модуль.__dict__)
    return модуль


ОТЧЁТ_С_ПАДЕНИЕМ = '''<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.langbot.app.SomeTest" tests="2" failures="1" errors="0">
  <testcase name="ok_one" classname="com.langbot.app.SomeTest"/>
  <testcase name="broken_one" classname="com.langbot.app.SomeTest">
    <failure message="java.lang.AssertionError: кнопки нет">стек</failure>
  </testcase>
</testsuite>
'''

ОТЧЁТ_С_ОШИБКОЙ = '''<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.langbot.app.SomeTest" tests="1" failures="0" errors="1">
  <testcase name="broken_one" classname="com.langbot.app.SomeTest">
    <error message="java.lang.IllegalStateException: сервер молчит">стек</error>
  </testcase>
</testsuite>
'''

ОТЧЁТ_ЧИСТЫЙ = '''<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.langbot.app.GoodTest" tests="1" failures="0" errors="0">
  <testcase name="all_fine" classname="com.langbot.app.GoodTest"/>
</testsuite>
'''


def _каталог_отчётов(tmp_path: Path) -> Path:
    d = tmp_path / "app" / "build" / "test-results" / "testDebugUnitTest"
    d.mkdir(parents=True)
    return d


def test_упавшая_проверка_названа_по_имени(tmp_path):
    d = _каталог_отчётов(tmp_path)
    (d / "TEST-SomeTest.xml").write_text(ОТЧЁТ_С_ПАДЕНИЕМ, encoding="utf-8")

    павшие = _загрузить_раннер().android_failed_tests(tmp_path)

    assert len(павшие) == 1
    имя, сообщение = павшие[0]
    assert имя == "SomeTest.broken_one"
    assert "кнопки нет" in сообщение


def test_когда_тесты_целы_список_пуст(tmp_path):
    """
    Главный случай. Пустой список значит «упало не в тестах», и раннер должен
    сказать именно это, а не делать вид, что проверка провалилась.
    """
    d = _каталог_отчётов(tmp_path)
    (d / "TEST-GoodTest.xml").write_text(ОТЧЁТ_ЧИСТЫЙ, encoding="utf-8")

    assert _загрузить_раннер().android_failed_tests(tmp_path) == []


def test_ошибки_тоже_считаются_падением(tmp_path):
    """<error> вместо <failure> — то же самое для человека."""
    d = _каталог_отчётов(tmp_path)
    # Отдельный отчёт, а не подмена слова в прежнем: замена «failure» на
    # «error» ломает и атрибуты, получается битый XML, и проверка мерила бы
    # устойчивость к мусору вместо разбора ошибок.
    (d / "TEST-E.xml").write_text(ОТЧЁТ_С_ОШИБКОЙ, encoding="utf-8")

    павшие = _загрузить_раннер().android_failed_tests(tmp_path)
    assert len(павшие) == 1 and павшие[0][0] == "SomeTest.broken_one"


def test_без_отчётов_не_падаем(tmp_path):
    """Сборка могла сорваться до того, как появился хоть один отчёт."""
    assert _загрузить_раннер().android_failed_tests(tmp_path) == []


def test_битый_отчёт_не_роняет_разбор(tmp_path):
    """Оборванный XML — обычное дело при убитой сборке."""
    d = _каталог_отчётов(tmp_path)
    (d / "TEST-Broken.xml").write_text("<testsuite><testcase", encoding="utf-8")
    (d / "TEST-SomeTest.xml").write_text(ОТЧЁТ_С_ПАДЕНИЕМ, encoding="utf-8")

    павшие = _загрузить_раннер().android_failed_tests(tmp_path)
    assert len(павшие) == 1, "битый файл помешал прочитать целый"
