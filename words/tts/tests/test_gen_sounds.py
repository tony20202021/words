"""
Озвучка слов: имена файлов и таблица языков.

Проверяется то, что ломается молча. Сама генерация ходит в сеть и длится
часы — её здесь нет; а вот имя файла и состав таблицы решают, найдёт ли
приложение звук, и ошибка в них выглядит как «у слова нет озвучки».
"""
import importlib.util
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "gen_sounds.py"
spec = importlib.util.spec_from_file_location("gen_sounds", TOOL)
mod = importlib.util.module_from_spec(spec)
sys.modules["gen_sounds"] = mod
spec.loader.exec_module(mod)


def test_an_ordinary_word_keeps_its_own_spelling():
    """
    Имя файла — само слово, а не номер: владелец ищет другой частотный список
    для английского, и при замене номера съедут. Имя по слову замену
    переживает, поэтому слаг не должен портить обычные слова.
    """
    assert mod.slug("many") == "many"
    assert mod.slug("snow") == "snow"
    assert mod.slug("up-to-date") == "up-to-date"
    # Апостроф уходит в подчёркивание намеренно: в имени файла он ломает
    # кавычки в оболочке и требует кодирования в URL, а различать слова ему
    # не помогает — «don't» в словаре одно. Путь в базе строится ТЕМ ЖЕ
    # слагом, поэтому расходиться им неоткуда.
    assert mod.slug("don't") == "don_t"


def test_an_unusual_character_cannot_escape_into_the_path():
    """
    В английском словаре такое слово ровно одно — «AT&T's». Но амперсанд,
    косая черта и точки в начале — это уже не имя файла, а путь: слаг обязан
    их обезвредить, иначе звук ляжет не туда или не ляжет вовсе.
    """
    assert "&" not in mod.slug("AT&T's")
    assert mod.slug("a/b") == "a_b"
    assert not mod.slug("../etc/passwd").startswith(".")
    assert "/" not in mod.slug("../etc/passwd")


def test_a_slug_is_never_empty():
    """Пустое имя дало бы файл «.mp3» — его потом не найти и не опознать."""
    assert mod.slug("") == "_"
    assert mod.slug("***") == "_"


def test_every_language_in_the_table_is_fully_described():
    """
    Недописанная строка таблицы роняет генерацию на середине — после часов
    работы и тысяч уже скачанных файлов.
    """
    for имя, spec_ in mod.LANGUAGES.items():
        assert spec_["code"], имя
        assert spec_["gtts"], имя
        assert len(spec_["edge"]) == 2, f"{имя}: нужно ровно два голоса Edge"
        assert all("Neural" in v for v in spec_["edge"]), имя


def test_hebrew_is_deliberately_absent():
    """
    Сторож против «добавим для единообразия». Озвучка иврита уже есть и
    устроена иначе: имена по номеру слова, каталоги hila и avri. Запуск этого
    инструмента для иврита сложил бы рядом второй набор из десяти тысяч
    файлов под другими именами — база указывала бы на старые, новые заняли бы
    место впустую.
    """
    assert "Иврит" not in mod.LANGUAGES


def test_voice_directories_match_what_the_database_will_point_at():
    """
    Имена каталогов голосов попадают в поле sounds как часть пути. Разъехались
    бы — приложение искало бы файлы там, где их нет.
    """
    assert mod.VOICE_DIRS == ["gtts", "voice1", "voice2"]


# ── выбор диапазона номеров ─────────────────────────────────────────────────

def test_a_range_of_word_numbers_can_be_asked_for():
    """
    Генерация идёт часами, а звук нужен там, где человек занимается сейчас.
    07.11.2026 второй пользователь шёл по номерам около 4000, и при счёте от
    самого частотного слова очередь дошла бы до него через пять часов —
    поэтому владелец попросил озвучить сначала 3000–4000.

    Проверяется построение запроса, а не поход в базу: именно здесь легко
    перепутать границу и молча пропустить край диапазона.
    """
    import inspect
    исходник = inspect.getsource(mod.load_words)
    assert '"$gte"' in исходник and '"$lte"' in исходник, (
        "границы диапазона должны быть включающими: «с 3000 по 4000» значит "
        "вместе с 3000 и 4000")


def test_the_range_arguments_exist_and_default_to_everything():
    """Без диапазона инструмент обязан брать весь словарь, как и раньше."""
    import inspect
    исходник = inspect.getsource(mod.main)
    assert '"--from"' in исходник and '"--to"' in исходник
    assert 'default=1' in исходник, "начало по умолчанию — первое слово"
