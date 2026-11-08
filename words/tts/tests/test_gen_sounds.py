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


# ── запись путей в базу ──────────────────────────────────────────────────────

class ПоддельнаяБаза:
    """Запоминает, что записали, и сколько записей изменилось."""
    def __init__(self):
        self.записи = {}
        self.words = self

    def update_one(self, фильтр, правка):
        было = self.записи.get(фильтр["_id"])
        стало = правка["$set"]["sounds"]
        self.записи[фильтр["_id"]] = стало
        return type("Res", (), {"modified_count": 0 if было == стало else 1})()


def _файлы(tmp_path, имена, голоса=("gtts", "voice1", "voice2")):
    for г in голоса:
        (tmp_path / г).mkdir(parents=True, exist_ok=True)
        for имя in имена:
            (tmp_path / г / f"{имя}.mp3").write_bytes(b"x" * 100)
    return tmp_path


def test_only_words_with_real_files_get_a_path(tmp_path):
    """
    Главное свойство записи. Путь ставится только тем словам, у которых файл
    ДЕЙСТВИТЕЛЬНО лежит на диске: иначе приложение покажет кнопку звука,
    нажатие на неё уйдёт в 404, и человек решит, что сломалось приложение.
    """
    база = _файлы(tmp_path, ["snow"])
    db = ПоддельнаяБаза()
    слова = [{"_id": 1, "word_foreign": "snow"}, {"_id": 2, "word_foreign": "rain"}]

    записано = mod.записать_пути(db, {"code": "en"}, база, слова)

    assert записано == 1
    assert 1 in db.записи and 2 not in db.записи, "слову без файлов проставили путь"


def test_the_path_matches_what_the_server_will_look_for(tmp_path):
    """Путь собирается из кода языка, каталога голоса и слага — как на диске."""
    база = _файлы(tmp_path, ["snow"])
    db = ПоддельнаяБаза()
    mod.записать_пути(db, {"code": "en"}, база, [{"_id": 1, "word_foreign": "snow"}])

    пути = db.записи[1]
    for голос in mod.VOICE_DIRS:
        assert f"sounds/en/{голос}/snow.mp3" in пути, пути


def test_a_word_with_only_some_voices_still_gets_those(tmp_path):
    """
    Недоделанное слово не теряется: что скачалось, то и регистрируется.
    Генерация идёт часами, и обрыв посередине слова не должен стоить ему
    всех голосов сразу.
    """
    база = _файлы(tmp_path, ["snow"], голоса=("gtts",))
    db = ПоддельнаяБаза()
    mod.записать_пути(db, {"code": "en"}, база, [{"_id": 1, "word_foreign": "snow"}])

    assert "sounds/en/gtts/snow.mp3" in db.записи[1]
    assert "voice1" not in db.записи[1]


def test_the_batch_size_and_only_db_switches_exist():
    """
    Порционная запись. Прежде пути писались ОДИН раз, в самом конце прохода:
    на 8466 словах это значило, что файлы на диске есть, а в приложении
    тишина — все пять часов, пока проход не кончится.

    --only-db нужен, чтобы подхватить уже готовое, не останавливая идущую
    генерацию: именно так 07.11.2026 зазвучали первые полторы тысячи слов.
    """
    import inspect
    исходник = inspect.getsource(mod.main)
    assert '"--db-batch"' in исходник and '"--only-db"' in исходник
    assert "default=200" in исходник, "порция по умолчанию должна быть задана"


# ── молчание сервера ────────────────────────────────────────────────────────

def test_молчащий_голос_не_подвешивает_работу(monkeypatch, tmp_path):
    """
    Сторож против зависания на одном слове.

    08.11.2026 работа встала на 7400-м слове из 8466: соединение к серверу
    Microsoft осталось открытым, ответа не пришло, и `except` не сработал —
    падать было нечему. Повторы без срока ожидания от этого не спасают: висит
    первая же попытка. Четыре часа работы замерли молча, в журнале ни строки.

    Здесь голос молчит нарочно. Проверка должна закончиться отказом за
    отведённый срок, а не ждать вечно.
    """
    import asyncio
    import sys
    import types

    молчун = types.ModuleType("edge_tts")

    class Communicate:
        def __init__(self, text, voice):
            pass

        async def save(self, path):
            await asyncio.sleep(3600)       # сервер молчит

    молчун.Communicate = Communicate
    monkeypatch.setitem(sys.modules, "edge_tts", молчун)

    from gen_sounds import edge_save

    async def прогнать():
        return await edge_save("слово", "голос", tmp_path / "x.mp3",
                               tries=2, срок=0.2)

    получилось = asyncio.run(asyncio.wait_for(прогнать(), timeout=15))
    assert получилось is False, "молчание сервера принято за успех"


def test_срок_ожидания_задан_и_разумен():
    """
    Опора: срок должен существовать и быть в здравых пределах. Слишком малый
    завалит работу на медленной сети, слишком большой вернёт зависание.
    """
    from gen_sounds import СРОК_ЗАПРОСА
    assert 10 <= СРОК_ЗАПРОСА <= 300, f"срок {СРОК_ЗАПРОСА} с не годится"


# ── слова из файла, минуя базу ──────────────────────────────────────────────

def test_слова_читаются_из_файла_словаря(tmp_path):
    """
    Озвучить надо уметь и то, что в базу ещё не загружено. Новый английский
    список — десять тысяч слов, и у 2768 из них озвучки нет: в базе этих слов
    никогда не было. Ждать загрузки нельзя — она меняет то, по чему люди уже
    занимаются, и решается отдельно; озвучка же ничего не меняет.
    """
    import json

    from gen_sounds import слова_из_файла

    файл = tmp_path / "словарь.json"
    файл.write_text(json.dumps({
        "1": {"word": "cat", "frequency": 1},
        "2": {"word": "dog", "frequency": 2},
        "3": {"word": "", "frequency": 3},          # пустое — пропустить
    }, ensure_ascii=False), encoding="utf-8")

    слова = слова_из_файла(файл, limit=0)
    assert [w["word_foreign"] for w in слова] == ["cat", "dog"]
    assert [w["word_number"] for w in слова] == [1, 2]


def test_из_файла_берётся_заданный_отрезок(tmp_path):
    """Отрезок номеров нужен и здесь: озвучка идёт часами."""
    import json

    from gen_sounds import слова_из_файла

    файл = tmp_path / "словарь.json"
    файл.write_text(json.dumps({
        str(n): {"word": f"w{n}", "frequency": n} for n in range(1, 11)
    }, ensure_ascii=False), encoding="utf-8")

    слова = слова_из_файла(файл, limit=0, first=4, last=6)
    assert [w["word_number"] for w in слова] == [4, 5, 6]


def test_читается_и_формат_прежнего_словаря(tmp_path):
    """
    Прежний eng.json зовёт поля иначе. Инструмент должен понимать оба, иначе
    озвучить старый словарь этим путём не выйдет вовсе.
    """
    import json

    from gen_sounds import слова_из_файла

    файл = tmp_path / "старый.json"
    файл.write_text(json.dumps({
        "7": {"word_foreign": "snow", "word_number": 7},
    }, ensure_ascii=False), encoding="utf-8")

    слова = слова_из_файла(файл, limit=0)
    assert слова == [{"word_number": 7, "word_foreign": "snow"}]


def test_слова_из_файла_и_запись_в_базу_несовместимы():
    """
    Сторож против тихой бессмыслицы. Слов из файла в базе нет, и записывать
    пути некуда: запрос вернул бы ноль обновлённых записей, инструмент
    отрапортовал бы успех, а в приложении осталась бы тишина. Такую
    несовместимость надо называть вслух, а не выяснять по пустому результату.
    """
    import subprocess
    import sys
    from pathlib import Path

    корень = Path(__file__).resolve().parents[3]
    р = subprocess.run(
        [sys.executable, "-I", str(корень / "words" / "tts" / "gen_sounds.py"),
         "--language", "Английский", "--words-from", "/нет/такого.json",
         "--write-db"],
        capture_output=True, text=True, timeout=60)
    assert р.returncode != 0, "несовместимые ключи приняты молча"
    assert "несовместимы" in (р.stderr + р.stdout)
