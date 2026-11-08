"""
Приём порции: повторы.

Состав предложения сторож проверяет давно, а вот повторы пропускал. Беда
безобидная на вид: «I know you» годится и для you, и для i, и для know —
ни одного чужого слова. Но файл набивается одной и той же фразой, и человек
видит её в третий раз, не получая ничего нового. Поэтому фраза живёт в файле
однажды, и проверяется это при приёме: сочиняющий своих прошлых порций не
помнит.

База здесь не нужна и вредна: проверка должна идти на любом месте и за
миллисекунды. Поэтому выход в Mongo и запись на диск подменяются.
"""
import argparse
import json
import sys
from pathlib import Path

import pytest

КОРЕНЬ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(КОРЕНЬ))

import batches                                        # noqa: E402

СЛОВА = [
    {"word_number": 1, "word_foreign": "i", "translation": "я"},
    {"word_number": 2, "word_foreign": "know", "translation": "знать"},
    {"word_number": 3, "word_foreign": "you", "translation": "ты"},
    # «me» нужно для второй фразы: без него она ушла бы в брак по составу, и
    # проверка про повторы доказывала бы совсем не то, что обещает названием.
    {"word_number": 4, "word_foreign": "me", "translation": "мне, меня"},
]


@pytest.fixture
def стенд(monkeypatch, tmp_path):
    """Подменяет базу и запись; отдаёт то, что осело бы в файле."""
    записанное = {}

    monkeypatch.setattr(batches, "слова_языка", lambda код: СЛОВА)
    monkeypatch.setattr(batches, "читать", lambda код: записанное.get(код, {}))
    monkeypatch.setattr(batches, "писать",
                        lambda код, данные: записанное.__setitem__(код, данные))

    def принять(порция, уже=None):
        if уже is not None:
            записанное["en"] = уже
        файл = tmp_path / "порция.json"
        файл.write_text(json.dumps(порция, ensure_ascii=False), encoding="utf-8")
        код = batches.команда_add(argparse.Namespace(
            file=str(файл), language="en", always=10))
        return код, записанное.get("en", {})

    return принять


def test_годная_порция_принимается(стенд):
    код, итог = стенд({"2": [{"text": "I know you", "ru": "Я знаю тебя"}]})
    assert код == 0
    assert итог["2"][0]["text"] == "I know you"


def test_повтор_внутри_порции_отвергается(стенд):
    """Одна фраза подана сразу двум словам — проходит только первая."""
    код, итог = стенд({
        "2": [{"text": "I know you", "ru": "Я знаю тебя"}],
        "3": [{"text": "I know you", "ru": "Я знаю тебя"}],
    })
    assert код == 1, "повтор обязан быть замечен"
    принято = sum(len(v) for v in итог.values())
    assert принято == 1, f"в файл село {принято} предложений вместо одного"


def test_повтор_уже_лежащего_в_файле_отвергается(стенд):
    код, итог = стенд(
        {"3": [{"text": "I know you", "ru": "Я знаю тебя"}]},
        уже={"2": [{"text": "I know you", "ru": "Я знаю тебя"}]})
    assert код == 1
    assert "3" not in итог, "фраза удвоилась под другим словом"
    assert len(итог["2"]) == 1


def test_повтор_узнаётся_без_оглядки_на_регистр_и_точку(стенд):
    """Иначе запрет обходится одной заглавной буквой."""
    код, итог = стенд(
        {"3": [{"text": "i know you.", "ru": "Я знаю тебя"}]},
        уже={"2": [{"text": "I know you", "ru": "Я знаю тебя"}]})
    assert код == 1
    assert "3" not in итог


def test_разные_фразы_повтором_не_считаются(стенд):
    код, итог = стенд({
        "2": [{"text": "I know you", "ru": "Я знаю тебя"}],
        "3": [{"text": "You know me", "ru": "Ты меня знаешь"}],
    })
    assert код == 0, "разные предложения забракованы как повтор"
    assert sum(len(v) for v in итог.values()) == 2


# ── сплошная перепроверка ───────────────────────────────────────────────────
#
# Правила меняются позже, чем сочиняются предложения: запрет повторов появился,
# когда их было уже сто десять, и шесть повторов лежали в файле. Значит нужна
# команда, которая перепроверяет всё с нуля.
#
# Главная опасность такой команды — что она всегда отвечает «всё хорошо».
# Поэтому проверка подкладывает ей заведомое нарушение и требует, чтобы она
# его назвала и вернула ненулевой код.


def test_перепроверка_молчит_на_чистом_файле(стенд, monkeypatch, capsys):
    стенд({"2": [{"text": "I know you", "ru": "Я знаю тебя"}],
           "3": [{"text": "You know me", "ru": "Ты меня знаешь"}]})
    код = batches.команда_audit(argparse.Namespace(language="en", always=10))
    assert код == 0
    assert "нарушений:               0" in capsys.readouterr().out


def test_перепроверка_находит_подложенный_повтор(стенд, monkeypatch, capsys):
    # Повтор кладётся в обход приёма: именно так он и попал в файл — приём
    # тогда повторов не запрещал.
    стенд({"2": [{"text": "I know you", "ru": "Я знаю тебя"}]})
    monkeypatch.setattr(batches, "читать", lambda код: {
        "2": [{"text": "I know you", "ru": "Я знаю тебя"}],
        "3": [{"text": "I know you", "ru": "Я знаю тебя"}]})
    код = batches.команда_audit(argparse.Namespace(language="en", always=10))
    вывод = capsys.readouterr().out
    assert код == 1, "перепроверка обязана падать на подложенном повторе"
    assert "повтор" in вывод and "№2" in вывод


def test_перепроверка_находит_чужое_слово(стенд, monkeypatch, capsys):
    стенд({"2": [{"text": "I know you", "ru": "Я знаю тебя"}]})
    monkeypatch.setattr(batches, "читать", lambda код: {
        "2": [{"text": "I know purple", "ru": "Я знаю лиловое"}]})
    код = batches.команда_audit(argparse.Namespace(language="en", always=10))
    вывод = capsys.readouterr().out
    assert код == 1
    assert "purple" in вывод
