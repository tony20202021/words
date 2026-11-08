"""
Отправщик владельцу: чтобы токен не утёк и файл дошёл нужным видом.

Скрипт ходит в Telegram с токеном бота в URL. Исключения httpx показывают URL
целиком — то есть достаточно один раз напечатать текст исключения, чтобы
токен осел в журнале, в транскрипте сессии и в истории терминала. Отозвать
его потом можно, но узнать об утечке неоткуда.
"""
import importlib.machinery
import importlib.util
import sys
from pathlib import Path

import pytest

СКРИПТ = Path(__file__).resolve().parents[2] / "scripts" / "send_to_owner.py"
spec = importlib.util.spec_from_loader(
    "send_to_owner",
    importlib.machinery.SourceFileLoader("send_to_owner", str(СКРИПТ)))
mod = importlib.util.module_from_spec(spec)
sys.modules["send_to_owner"] = mod
spec.loader.exec_module(mod)

ТОКЕН = "123456:СЕКРЕТНЫЙ-ТОКЕН-БОТА"


def test_the_token_never_reaches_the_output(tmp_path, capsys, monkeypatch):
    """Падение запроса не должно стоить нам токена."""
    файл = tmp_path / "x.png"
    файл.write_bytes(b"x")

    class Взрывается:
        @staticmethod
        def post(*a, **k):
            raise RuntimeError(f"сбой при обращении к {a[0] if a else ''}")

    monkeypatch.setitem(sys.modules, "httpx", Взрывается)
    ok = mod.послать(ТОКЕН, 1, файл, "подпись")

    напечатано = capsys.readouterr().out
    assert ok is False
    assert ТОКЕН not in напечатано, "токен напечатан в выводе"
    assert "СЕКРЕТНЫЙ" not in напечатано
    assert "RuntimeError" in напечатано, "о сбое надо сказать хотя бы типом"


def test_pictures_go_as_photos_and_the_rest_as_documents(tmp_path, monkeypatch):
    """
    Картинку, посланную документом, человек видит строкой с именем файла и
    должен её скачать. А BotFather вообще принимает только фото — именно так
    ставится аватарка бота.
    """
    вызовы = []

    class Ловушка:
        @staticmethod
        def post(url, **k):
            вызовы.append(url)
            return type("R", (), {"status_code": 200, "json": lambda self: {"ok": True}})()

    monkeypatch.setitem(sys.modules, "httpx", Ловушка)
    for имя, метод in (("a.png", "sendPhoto"), ("b.jpg", "sendPhoto"),
                       ("c.pdf", "sendDocument"), ("d.mp3", "sendDocument")):
        п = tmp_path / имя
        п.write_bytes(b"x")
        mod.послать(ТОКЕН, 1, п, "")
        assert вызовы[-1].endswith(метод), f"{имя} ушёл как {вызовы[-1]}"


def test_the_owner_is_looked_up_and_not_written_into_the_code():
    """
    Личный номер в репозитории — и лишнее, и ломкое: при смене владельца его
    пришлось бы искать по коду. Берётся из базы, по признаку администратора.
    """
    исходник = СКРИПТ.read_text(encoding="utf-8")
    assert "is_admin" in исходник
    import re
    номера = re.findall(r"\b\d{8,}\b", исходник)
    assert not номера, f"в коде зашит чей-то номер: {номера}"
