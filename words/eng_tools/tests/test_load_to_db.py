"""
Загрузка словаря в базу: прогресс людей остаётся, слова меняются.

Проверяется на настоящей MongoDB в отдельной временной базе. Подделкой тут
ничего не проверить: вся суть в поведении уникального индекса
(language_id, word_foreign), а подделка проверяла бы мою же выдумку о нём.

Главная опора — первый тест. Новый словарь переставляет слова по номерам:
«it» переезжает с 10-го номера на 12-й. Обновление «в лоб» падает на
уникальном индексе, потому что в этот миг «it» ещё занято прежним владельцем —
08.11.2026 на этом и спотыкалась штатная загрузка, причём молча.
"""
import json
import sys
import uuid
from pathlib import Path

import pytest

КОРЕНЬ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(КОРЕНЬ / "eng_tools"))
sys.path.insert(0, str(КОРЕНЬ / "tts"))

URL = "mongodb://localhost:8527"


@pytest.fixture
def база():
    """Своя база на прогон; боевая не задействована ни на чтение."""
    pymongo = pytest.importorskip("pymongo")
    try:
        cl = pymongo.MongoClient(URL, serverSelectionTimeoutMS=1500)
        cl.admin.command("ping")
    except Exception as e:                                  # pragma: no cover
        pytest.skip(f"MongoDB недоступна ({e})")

    имя = f"langbot_test_load_{uuid.uuid4().hex[:8]}"
    assert "language_learning_bot" not in имя
    db = cl[имя]
    # Тот самый индекс, из-за которого всё и затевалось.
    db.words.create_index([("language_id", 1), ("word_foreign", 1)], unique=True,
                          name="lang_word_foreign_idx")
    язык = db.languages.insert_one({"name_ru": "Английский"}).inserted_id
    try:
        yield db, язык
    finally:
        cl.drop_database(имя)
        cl.close()


def _загрузить(db, язык_id, словарь: dict, tmp_path: Path, monkeypatch):
    """Запускает загрузчик против подставной базы."""
    import load_to_db

    monkeypatch.setattr(load_to_db, "подключиться", lambda: (db, язык_id))
    # Озвучки в тесте нет: каталог пустой, значит пути должны очищаться.
    monkeypatch.setattr(load_to_db, "ОЗВУЧКА", tmp_path / "нет-такого")

    файл = tmp_path / "словарь.json"
    файл.write_text(json.dumps(словарь, ensure_ascii=False), encoding="utf-8")
    код = load_to_db.main(["--dictionary", str(файл)])
    assert код == 0, "загрузчик вернул ошибку"


def test_слова_меняются_местами_несмотря_на_уникальный_индекс(
        база, tmp_path, monkeypatch):
    """
    Опора всей затеи: два слова обмениваются номерами.

    Обмен выбран намеренно. Сперва здесь стоял случай попроще — «it» переезжал
    с 10-го номера на 12-й, а на 10-м появлялось третье слово, — и проверка
    проходила даже БЕЗ первого прохода: обновление идёт по возрастанию
    номеров, 10-й освобождал «it» раньше, чем 12-й его просил. Сторож без
    зубов хуже отсутствующего: он уверяет, что защита работает.

    Обмен не обойти никаким порядком. Кто бы ни обновлялся первым, нужное ему
    слово занято другим участником обмена.
    """
    db, язык = база
    db.words.insert_many([
        {"language_id": язык, "word_number": 10, "word_foreign": "it",
         "translation": "это"},
        {"language_id": язык, "word_number": 12, "word_foreign": "said",
         "translation": "сказал"},
    ])

    _загрузить(db, язык, {
        "10": {"word": "said", "description": ["сказал"],
               "transcription": "/sɛd/", "frequency": 10},
        "12": {"word": "it", "description": ["это"], "transcription": "/ɪt/",
               "frequency": 12},
    }, tmp_path, monkeypatch)

    по_номеру = {w["word_number"]: w["word_foreign"]
                 for w in db.words.find({"language_id": язык})}
    assert по_номеру == {10: "said", 12: "it"}, (
        f"слова не обменялись номерами: {по_номеру}")


def test_записи_сохраняют_свой_id_а_значит_и_прогресс(база, tmp_path, monkeypatch):
    """
    Прогресс в user_statistics ссылается на запись слова. Пересоздать запись
    значит оборвать эту ссылку — человек потерял бы всё изученное. Поэтому
    запись обязана остаться той же, сменив содержимое.
    """
    db, язык = база
    вставлено = db.words.insert_one({
        "language_id": язык, "word_number": 7, "word_foreign": "snow",
        "translation": "снег"}).inserted_id

    _загрузить(db, язык, {
        "7": {"word": "cat", "description": ["кот"], "transcription": "/kæt/",
              "frequency": 7},
    }, tmp_path, monkeypatch)

    слово = db.words.find_one({"language_id": язык, "word_number": 7})
    assert слово["_id"] == вставлено, "запись пересоздана — прогресс оборван"
    assert слово["word_foreign"] == "cat"


def test_чужая_озвучка_не_остаётся_у_нового_слова(база, tmp_path, monkeypatch):
    """
    Сторож против худшего из возможных исходов. Пути озвучки собраны по самому
    слову: у 12-го номера это sounds/en/gtts/said.mp3. Сменив слово и не
    тронув пути, получим «it», которое вслух говорит «said». Штатная загрузка
    так и поступает: пустое значение она отбрасывает, а не очищает.
    """
    db, язык = база
    db.words.insert_one({
        "language_id": язык, "word_number": 12, "word_foreign": "said",
        "translation": "сказал",
        "sounds": '{"sound_1": "sounds/en/gtts/said.mp3"}'})

    _загрузить(db, язык, {
        "12": {"word": "it", "description": ["это"], "transcription": "/ɪt/",
               "frequency": 12},
    }, tmp_path, monkeypatch)

    слово = db.words.find_one({"language_id": язык, "word_number": 12})
    assert слово["word_foreign"] == "it"
    assert not слово.get("sounds"), (
        f"у «it» осталась озвучка прежнего слова: {слово.get('sounds')}")


def test_слов_которых_не_было_добавляются(база, tmp_path, monkeypatch):
    db, язык = база
    db.words.insert_one({"language_id": язык, "word_number": 1,
                         "word_foreign": "the", "translation": "арт-ль"})

    _загрузить(db, язык, {
        "1": {"word": "the", "description": ["арт-ль"], "transcription": "/ðə/",
              "frequency": 1},
        "2": {"word": "to", "description": ["к"], "transcription": "/tu/",
              "frequency": 2},
    }, tmp_path, monkeypatch)

    assert db.words.count_documents({"language_id": язык}) == 2
    новое = db.words.find_one({"language_id": язык, "word_number": 2})
    assert новое["word_foreign"] == "to"
    assert новое["created_at"], "у новой записи нет времени создания"


def test_временных_имён_после_загрузки_не_остаётся(база, tmp_path, monkeypatch):
    """
    Опора против обрыва на середине. Первый проход даёт словам временные
    имена; если второй не доработает, в базе останется мусор вместо слов, и
    люди увидят его на занятии.
    """
    db, язык = база
    db.words.insert_many([
        {"language_id": язык, "word_number": n, "word_foreign": f"old{n}",
         "translation": "старое"} for n in range(1, 6)
    ])

    _загрузить(db, язык, {
        str(n): {"word": f"new{n}", "description": ["новое"],
                 "transcription": f"/n{n}/", "frequency": n}
        for n in range(1, 6)
    }, tmp_path, monkeypatch)

    слова = [w["word_foreign"] for w in db.words.find({"language_id": язык})]
    assert all(w.startswith("new") for w in слова), f"остался мусор: {слова}"


def test_прогресс_не_тронут(база, tmp_path, monkeypatch):
    """Загрузка не имеет права писать в user_statistics вовсе."""
    db, язык = база
    db.words.insert_one({"language_id": язык, "word_number": 1,
                         "word_foreign": "the", "translation": "арт-ль"})
    db.user_statistics.insert_many([
        {"user_id": "u1", "language_id": str(язык), "word_id": "w1", "score": 1},
        {"user_id": "u1", "language_id": str(язык), "word_id": "w2", "score": 0},
    ])

    _загрузить(db, язык, {
        "1": {"word": "cat", "description": ["кот"], "transcription": "/kæt/",
              "frequency": 1},
    }, tmp_path, monkeypatch)

    assert db.user_statistics.count_documents({"language_id": str(язык)}) == 2
    assert {s["score"] for s in db.user_statistics.find()} == {0, 1}
