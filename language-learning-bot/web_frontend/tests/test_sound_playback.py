"""
Проигрывание звука на карточке: одна дорожка на страницу.

Что проверяется и почему
------------------------
В пик-режиме варианты ответа — это наборы звуков, и каждый вариант играется
цепочкой с паузой между звуками. Учащийся слышит первый звук, понимает, что
слово не то, и жмёт следующий вариант. Если предыдущая цепочка не оборвана,
варианты звучат одновременно и сравнить их невозможно — то есть ломается ровно
то действие, ради которого режим и существует.

Тесты структурные: исполнять JS здесь нечем, поэтому проверяется разводка — что
все кнопки звука идут через общего владельца и что владелец умеет обрывать и
звук, и отложенный переход по цепочке. Кнопки живут в шаблоне карточки, а сам
владелец — в /static/js/word_card.js (из шаблона он вынесен: тот фрагмент
приезжает по hx-swap, и скрипт внутри него выполнялся заново на каждый ответ).
"""

import re
from pathlib import Path

import pytest

TEMPLATE = (Path(__file__).resolve().parents[1]
            / "app" / "templates" / "partials" / "word_card.html")
SCRIPT = (Path(__file__).resolve().parents[1]
          / "app" / "static" / "js" / "word_card.js")


@pytest.fixture(scope="module")
def html() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def js() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_every_sound_button_goes_through_the_shared_owner(html):
    """
    Ни одна кнопка не должна дёргать <audio> напрямую: такой вызов ничего не
    знает о том, что уже играет, и накладывается на предыдущее.
    """
    onclicks = re.findall(r'onclick="([^"]*)"', html)
    sound_clicks = [c for c in onclicks if "play" in c.lower() or "snd-" in c]
    assert sound_clicks, "кнопки звука не найдены — тест смотрит не туда"
    for click in sound_clicks:
        assert click.startswith("playSounds("), click

    # Прямой вызов .play() на элементе мимо владельца.
    assert not re.search(r"getElementById\([^)]*\)\.play\(\)", html)


def test_all_three_kinds_of_sound_button_are_wired(html):
    """Одиночный звук, «все звуки слова» и вариант пик-режима — все три места."""
    assert "onclick=\"playSounds(['snd-{{ loop.index }}'])\"" in html
    assert html.count("onclick=\"playSounds(") == 3


def test_starting_playback_stops_whatever_was_playing(js):
    """play() обязан начинаться с обрыва предыдущего, иначе цепочки складываются."""
    body = js[js.index("function play(ids)"):]
    body = body[:body.index("return { play")]
    assert re.match(r"\s*function play\(ids\)\s*\{\s*stop\(\);", body), body[:200]


def test_stop_cancels_the_pause_timer_and_the_pending_chain(js):
    """
    Паузу между звуками держит setTimeout, а не сам <audio>. Если оборвать
    только звук, следующий в цепочке всё равно зазвучит через 350 мс — поэтому
    нужен и clearTimeout, и счётчик поколений, отсекающий отложенный next().
    """
    body = js[js.index("function stop()"):]
    body = body[:body.index("function play(ids)")]
    assert "clearTimeout(timer)" in body
    assert "gen++" in body
    assert ".pause()" in body

    chain = js[js.index("function play(ids)"):js.index("return { play")]
    assert "mine !== gen" in chain, "отложенный next() не проверяет поколение"


def test_leaving_the_card_silences_it(js):
    """
    HTMX выбрасывает <audio> из DOM при переходе к следующему слову, но
    отсоединённый элемент продолжает играть — звук предыдущего слова наложился
    бы на следующее.
    """
    handler = js[js.index("function onBtnClick()"):]
    handler = handler[:handler.index("function onDone()")]
    assert "LBSounds.stop()" in handler
